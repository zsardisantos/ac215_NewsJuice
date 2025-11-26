# Explanation of the main files in the repository.

**.github/**
Contains the workflow file for the CI/CD GitHub Actions workflow (ci_full.yaml)

**docs/** Contains folder with documentation for submission of MS_4  
- Application_Design_Document
- Data_Versioning_documentation
- CI_Evidence
- Finetuning documentation  

(Note regarding testing: in services we have a script **combined_unit_test.sh** which generated the unitn test with a combined coverage for all three main services: scraper, loader and chatter.)  


The **services/** folder contains folders each of which is a self-contained containerized  micro-service:  

- **scraper_deployed/**
scraper version - currently deployed on Cloud Run and running on Scheduler every 24 h

- **loader_deployed/**
loader version - currently deployed on Cloud Run and running on Scheduler every 24 h

- **loader_testing/**
A version of the loader service with a full test suit added (incl. CI/CD workflow)

- **chatter_deployed/**
Contains the version of the chatter service 

- **frontend/**
Contains the frontend

- **finetuning/**
Contains the 2 finetuning exercise for the LLM
    1. Finetuning for podcast generation.
    2. Finetuning for article Classification

- **data_versioner/**
Contains the files for the Data Versioning module (hybrid SQL snapshot + DVC)

**Archive/**
Older files and versions (not relevant for submission)
