# 📁 Structure of the Repository

This README describes the folder organization of the NewsJuice project.

---

## 🗂️ Project Root

| Folder/File | Description |
|-------------|-------------|
| `services/` | Containerized microservices |
| `docs/` | Documentation for project submissions |
| `.github/` | CI/CD workflow configurations |
| `Finetuning/` | Model fine-tuning resources |
| `.gitignore` | Git ignore rules |
| `README*.md` | Various README files (see README_general for descriptions) |

---

## 📂 Folder Descriptions

### `.github/`

Contains the workflow file for the CI/CD GitHub Actions workflow (`ci_combined_trigger_pulumi.yaml`)

### `docs/`

Contains documentation folders for MS4 submission:

- `Application_Design_Document/`
- `CI_CD_set-up_and_evidence/`
- `Data_Versioning_documentation/`
- `Finetuning_documentation/`
- `File: MEDIUM_BLOG_POST.md`
- `images (various images for *.md files)`

### `services/`

Contains self-contained containerized microservices:

| Service | Description |
|---------|-------------|
| `scraper_deployed/` | Scraper - deployed version |
| `loader_deployed/` | Loader - deployed version |
| `chatter_deployed/` | Chatter - deployed version |
| `frontend/` | Frontend - deployed version |
| `deployment/` | Deployment setup for Pulumi/Kubernetes |
| `data_versioner/` | Data Versioning module (hybrid SQL snapshot + DVC) |
| `finetuning/` | Fine-tuning exercises for the LLM |

#### Fine-tuning Modules

1. Fine-tuning for podcast generation
2. Fine-tuning for article classification

---

## 🌳 Detailed Services Structure

> Secondary files (e.g., for local testing, dotfiles and others like __*__ files etc.) are omitted.
```
services/
├── loader_deployed/
│   ├── loader.py
│   ├── main.py
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── docker-compose.test.yml
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── setup/
│       │   └── init_test_db.sql
│       ├── unit/
│       │   ├── __init__.py
│       │   └── test_chunking.py
│       ├── integration/
│       │   ├── __init__.py
│       │   └── test_database.py
│       └── system/
│           ├── __init__.py
│           └── test_loader_api.py
│
├── scraper_deployed/
│   ├── scraper.py
│   ├── main.py
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── docker-compose.test.yml
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── setup/
│       │   └── init_test_db.sql
│       ├── unit/
│       │   ├── __init__.py
│       │   └── test_scraping.py
│       ├── integration/
│       │   ├── __init__.py
│       │   └── test_database.py
│       └── system/
│           ├── __init__.py
│           └── test_scraper_api.py
│
├── chatter_deployed/
│   ├── chatter.py
│   ├── main.py
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── docker-compose.test.yml
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── unit/
│       │   ├── __init__.py
│       │   └── test_chat.py
│       ├── integration/
│       │   ├── __init__.py
│       │   └── test_database.py
│       └── system/
│           ├── __init__.py
│           └── test_chatter_api.py
│
├── frontend/
│   └── podcast-app/
│       ├── src/
│       ├── package.json
│       ├── Dockerfile
│       └── ... (React app files)
│
└── deployment/
    ├── __main__.py
    ├── Pulumi.yaml
    ├── Pulumi.prod.yaml
    ├── Dockerfile
    ├── docker-shell.sh
    └── docker-entrypoint.sh
```