#!/bin/bash

# =============================================================================
# Project File Usage Analyzer
# =============================================================================
# Analyzes which files in a project are actually being used/referenced
# Usage:
# chmod +x analyze_usage.sh
# ./analyze_usage.sh
# =============================================================================

set -e

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

echo "============================================================"
echo "Project File Usage Analysis"
echo "Directory: $(pwd)"
echo "============================================================"

# -----------------------------------------------------------------------------
# 1. GENERATED/CACHE DIRECTORIES (safe to delete)
# -----------------------------------------------------------------------------
echo ""
echo "1. GENERATED/CACHE DIRECTORIES (safe to ignore/delete)"
echo "------------------------------------------------------------"

generated_dirs=(".pytest_cache" "__pycache__" "htmlcov" ".coverage" "*.egg-info" ".venv" "venv" "node_modules" ".mypy_cache" "logs" ".ruff_cache")

for pattern in "${generated_dirs[@]}"; do
    found=$(find . -name "$pattern" -type d 2>/dev/null | grep -v ".git" | head -20)
    if [ -n "$found" ]; then
        echo "$found"
    fi
done

# -----------------------------------------------------------------------------
# 2. FILES TRACKED BY GIT
# -----------------------------------------------------------------------------
echo ""
echo "2. FILES TRACKED BY GIT"
echo "------------------------------------------------------------"
git ls-files 2>/dev/null | head -50
git_count=$(git ls-files 2>/dev/null | wc -l)
echo "... Total: $git_count files tracked by Git"

# -----------------------------------------------------------------------------
# 3. PYTHON IMPORTS ANALYSIS
# -----------------------------------------------------------------------------
echo ""
echo "3. PYTHON IMPORTS (what modules are used)"
echo "------------------------------------------------------------"
grep -rh "^import \|^from " --include="*.py" . 2>/dev/null \
    | grep -v ".venv" \
    | grep -v "__pycache__" \
    | sed 's/^import //' \
    | sed 's/^from //' \
    | sed 's/ import.*//' \
    | sort -u \
    | head -30

# -----------------------------------------------------------------------------
# 4. FILES REFERENCED IN PYTHON CODE
# -----------------------------------------------------------------------------
echo ""
echo "4. FILES/PATHS REFERENCED IN PYTHON CODE"
echo "------------------------------------------------------------"
grep -rohE "['\"][^'\"]*\.(py|yaml|yml|json|sql|txt|csv|env|sh|toml|ini)['\"]" --include="*.py" . 2>/dev/null \
    | grep -v ".venv" \
    | grep -v "__pycache__" \
    | tr -d "\"'" \
    | sort -u \
    | head -30

# -----------------------------------------------------------------------------
# 5. DOCKERFILE ANALYSIS
# -----------------------------------------------------------------------------
echo ""
echo "5. FILES USED BY DOCKER"
echo "------------------------------------------------------------"

for dockerfile in Dockerfile Dockerfile.dev Dockerfile.prod; do
    if [ -f "$dockerfile" ]; then
        echo ""
        echo "[$dockerfile]"
        grep -E "^COPY|^ADD|^RUN.*pip|^RUN.*uv" "$dockerfile" 2>/dev/null | head -20
    fi
done

# -----------------------------------------------------------------------------
# 6. DOCKER-COMPOSE ANALYSIS
# -----------------------------------------------------------------------------
echo ""
echo "6. FILES USED BY DOCKER-COMPOSE"
echo "------------------------------------------------------------"

for composefile in docker-compose*.yml docker-compose*.yaml; do
    if [ -f "$composefile" ]; then
        echo ""
        echo "[$composefile]"
        grep -E "env_file|volumes:|build:|\.env|\.yaml|\.yml" "$composefile" 2>/dev/null | head -20
    fi
done

# -----------------------------------------------------------------------------
# 7. PYPROJECT.TOML / SETUP.PY ANALYSIS
# -----------------------------------------------------------------------------
echo ""
echo "7. PACKAGE CONFIGURATION"
echo "------------------------------------------------------------"

if [ -f "pyproject.toml" ]; then
    echo "[pyproject.toml - dependencies]"
    grep -A 50 "dependencies" pyproject.toml 2>/dev/null | grep -E "^\s+\"" | head -20
fi

if [ -f "setup.py" ]; then
    echo "[setup.py - packages]"
    grep -E "packages=|install_requires" setup.py 2>/dev/null | head -10
fi

# -----------------------------------------------------------------------------
# 8. SHELL SCRIPTS ANALYSIS
# -----------------------------------------------------------------------------
echo ""
echo "8. SHELL SCRIPTS AND WHAT THEY REFERENCE"
echo "------------------------------------------------------------"

for script in *.sh; do
    if [ -f "$script" ]; then
        echo ""
        echo "[$script]"
        grep -E "python|docker|source|export|\.\/" "$script" 2>/dev/null | head -10
    fi
done

# -----------------------------------------------------------------------------
# 9. ENVIRONMENT FILES
# -----------------------------------------------------------------------------
echo ""
echo "9. ENVIRONMENT FILES"
echo "------------------------------------------------------------"
ls -la .env* env.yaml env.yml 2>/dev/null || echo "No env files found"

# -----------------------------------------------------------------------------
# 10. POTENTIALLY UNUSED FILES
# -----------------------------------------------------------------------------
echo ""
echo "10. POTENTIALLY UNUSED FILES (not referenced elsewhere)"
echo "------------------------------------------------------------"

# Get all non-hidden, non-generated files
all_files=$(find . -type f \
    -not -path "./.git/*" \
    -not -path "./.venv/*" \
    -not -path "./__pycache__/*" \
    -not -path "./.pytest_cache/*" \
    -not -path "./htmlcov/*" \
    -not -path "./.dvc/*" \
    -not -name "*.pyc" \
    -not -name ".DS_Store" \
    2>/dev/null)

echo ""
echo "Checking each file for references..."
echo ""

for file in $all_files; do
    basename=$(basename "$file")
    
    # Skip common essential files
    case "$basename" in
        __init__.py|.gitignore|.dockerignore|.dvcignore|uv.lock|.flake8|pytest.ini|.coverage)
            continue
            ;;
    esac
    
    # Search for references to this file (by basename)
    references=$(grep -rl "$basename" --include="*.py" --include="*.yml" --include="*.yaml" --include="*.sh" --include="*.toml" --include="Dockerfile*" . 2>/dev/null \
        | grep -v ".venv" \
        | grep -v "$file" \
        | head -1)
    
    if [ -z "$references" ]; then
        # Check if it's a Python file that might be imported by module name
        if [[ "$basename" == *.py ]]; then
            module_name="${basename%.py}"
            module_ref=$(grep -rl "import $module_name\|from.*$module_name" --include="*.py" . 2>/dev/null | grep -v ".venv" | head -1)
            if [ -n "$module_ref" ]; then
                continue
            fi
        fi
        
        echo "  ? $file"
    fi
done

# -----------------------------------------------------------------------------
# 11. SUMMARY
# -----------------------------------------------------------------------------
echo ""
echo "============================================================"
echo "SUMMARY"
echo "============================================================"
echo ""
echo "Essential file types:"
echo "  - src/, tests/        → Your actual code"
echo "  - Dockerfile*         → Container definitions"
echo "  - docker-compose*.yml → Service orchestration"
echo "  - pyproject.toml      → Package configuration"
echo "  - *.sh                → Deployment/utility scripts"
echo "  - .env*, env.yaml     → Environment configuration"
echo ""
echo "Safe to delete:"
echo "  - htmlcov/            → Generated coverage reports"
echo "  - .pytest_cache/      → Test cache"
echo "  - __pycache__/        → Python bytecode cache"
echo "  - logs/               → Log files (if not needed)"
echo "  - *.pyc               → Compiled Python files"
echo ""
echo "Review the '?' items above - they may be unused."
echo "============================================================"