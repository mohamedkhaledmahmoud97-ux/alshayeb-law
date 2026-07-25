# ARCHITECTURE

## 1. System Overview

ALSHAYEB-LAW is organized as a documentation-heavy, benchmark-driven legal RAG project. The repository architecture separates specification, instructions, benchmarks, source material, outputs, and support files.

## 2. Repository Architecture

### Root Files
- README.md
- PROJECT_SPEC.md
- AI_CONTEXT.md
- DEVELOPMENT_PLAN.md
- ARCHITECTURE.md
- REQUIREMENTS.md
- ROADMAP.md
- TODO.md
- DECISIONS.md
- CHANGELOG.md
- CONTRIBUTING.md
- LICENSE
- SECURITY.md
- CODE_OF_CONDUCT.md

### Documentation Folder
Contains:
- report drafts,
- appendix material,
- master plans,
- methodology notes,
- and related documentation.

### Prompts Folder
Contains:
- Claude instructions,
- system prompts,
- and any reusable prompt templates.

### Benchmarks Folder
Contains:
- query sets,
- evaluation tasks,
- hard negatives,
- and benchmark definitions.

### Datasets Folder
Contains:
- source documents,
- labeled samples,
- annotations,
- and versioned dataset assets.

### Src Folder
Contains:
- scripts,
- pipeline code,
- retrieval logic,
- evaluation code,
- and utility functions.

### Tests Folder
Contains:
- unit tests,
- consistency tests,
- evaluation tests,
- and validation scripts.

### Config Folder
Contains:
- configuration files,
- environment settings,
- and system parameters.

### References Folder
Contains:
- bibliographic entries,
- legal references,
- and supporting citations.

### Outputs Folder
Contains:
- generated tables,
- figures,
- logs,
- and final artifacts.

### .github Folder
Contains:
- repository workflows,
- issue templates,
- pull request templates,
- and contribution automation.

## 3. Design Principles

- Keep documents separated by function.
- Keep reproducible artifacts in versioned folders.
- Keep source and output files distinct.
- Prefer clarity over compression.
- Preserve traceability across all files.

## 4. Future Expansion

The architecture can expand later to include:
- automated evaluation pipelines,
- CI checks,
- notebook experiments,
- and release packaging.