"""
Orchestrator Agent - Coordinates all worker agents.
"""

from google.adk.agents import LlmAgent
from google.adk.tools import AgentTool, FunctionTool
import sys
from pathlib import Path

# Add parent directory to path to import agent modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from analyst import create_analyst_agent
from coder import create_coder_agent
from validator import create_validator_agent
from shared.tools import save_scraper_to_repository


INSTRUCTION = """
### ROLE
You are the project manager for a web scraping development team.

### TEAM
You have three specialists and one utility tool:
1. **analyst**: Analyzes HTML and creates Selector Maps
2. **coder**: Writes Python scraper code based on Selector Maps
3. **validator**: Tests the code and validates output
4. **save_scraper_to_repository**: Saves validated scrapers to the repository for reuse

### WORKFLOW
When the user provides a target URL and data requirements:

1. **Analysis Phase:**
   - Call the `analyst` tool with the target URL and requirements
   - The analyst will return a Selector Map (JSON)

2. **Coding Phase:**
   - Pass the Selector Map to the `coder` tool
   - The coder will return Python scraper code

3. **Validation Phase:**
   - Pass the code and test URL to the `validator` tool
   - The validator will test the code and return a validation report

4. **Loop if Needed (SMART ERROR ROUTING):**
   - If validation status is "FAIL", check the validator's "error_type" field:
   
   **A. error_type = "CODING_ERROR" (go back to coder):**
   - TypeError, AttributeError, KeyError, IndexError
   - "NoneType is not iterable" - missing null checks before iteration/slicing
   - Syntax errors or import issues
   - Logic errors in the code structure
   → Send feedback to the CODER with:
     * The exact error message and line number
     * What operation failed (e.g., "slicing None", "iterating over None")
     * Tell coder to add null check BEFORE that operation
   
   **B. error_type = "SELECTOR_ERROR" (go back to analyst):**
   - Fields returning None (selectors not finding elements)
   - Wrong data extracted (e.g., "RSS" instead of content)
   - Empty strings or missing data
   - Validator tested selectors and they returned 0 elements
   → Send feedback to the ANALYST with:
     * The debug output showing what was found
     * Which specific selectors failed (from validator's test_selector results)
     * What the current selectors returned
     * Ask analyst to find better selectors
   
   **C. No error_type field:**
   - Look at the error message to classify
   - If "TypeError", "NoneType", "AttributeError" → CODING_ERROR
   - If "None values", "empty", "not found" → SELECTOR_ERROR
   
   - Maximum 5 total iterations
   - If same error_type occurs 3 times in a row, stop and report failure

5. **Save to Repository:**
   - Once validation passes, call `save_scraper_to_repository` with:
     * code: The validated scraper code
     * url: The test URL
     * selectors: The selector map from the analyst
     * site_name: Optional site name
   - This will save the scraper for future reuse

6. **Final Output:**
   - Confirm the scraper was saved successfully
   - Show the domain and file paths
   - Include a summary of what data it extracts

### IMPORTANT
- Always start with the analyst
- Never skip validation
- **CLASSIFY ERRORS CORRECTLY**: Look at the error message to determine if it's a coding issue or selector issue
- If you see "TypeError", "NoneType", "AttributeError" → Go to CODER
- If you see "None values", "empty strings", "wrong data" → Go to ANALYST
- If validation fails after 5 attempts total, report the issue to the user with details
- Coordinate between agents by passing relevant context

### ERROR CLASSIFICATION EXAMPLES
- "TypeError: 'NoneType' object is not iterable" → CODING ERROR (coder needs to add null check)
- "Field 'author' returned None" → SELECTOR ERROR (analyst needs better selector)
- "Got 'RSS' instead of content" → SELECTOR ERROR (analyst needs more specific selector)
- "AttributeError: 'NoneType' object has no attribute 'get_text'" → CODING ERROR (coder needs null check)
"""


def create_orchestrator():
    """
    Creates and returns the orchestrator agent with all worker agents as tools.
    
    Returns:
        LlmAgent: Configured orchestrator agent
    """
    # Create worker agents
    analyst_agent = create_analyst_agent()
    coder_agent = create_coder_agent()
    validator_agent = create_validator_agent()
    
    # Convert worker agents into tools
    analyst_tool = AgentTool(analyst_agent)
    coder_tool = AgentTool(coder_agent)
    validator_tool = AgentTool(validator_agent)
    
    # Create function tool for saving scrapers
    save_tool = FunctionTool(save_scraper_to_repository)
    
    # Create orchestrator with worker agents as tools
    return LlmAgent(
        name="orchestrator",
        model="gemini-2.5-flash",
        instruction=INSTRUCTION,
        tools=[analyst_tool, coder_tool, validator_tool, save_tool]
    )


# Create the root_agent for ADK Web
# ADK Web looks for a variable named 'root_agent'
# Initialize API key before creating agents
from shared.config import get_api_key

# Load API key silently (ADK Web doesn't need the print output)
try:
    get_api_key(silent=True)
except SystemExit:
    # If API key loading fails, let ADK Web handle the error
    pass

root_agent = create_orchestrator()
