# OpsPilot commit-readiness review

At the end of work that changes this repository, inspect Git status/diff and all
changed/new files for secrets, sensitive or real customer data, unnecessary generated
artifacts and absolute local paths. Check ignore coverage and whether ignored
artifacts are already tracked; ignore rules do not protect tracked files.

Include **GITHUB COMMIT READINESS** in the final report, with exact repository-relative
paths and brief reasons in three groups:

- **A. Safe to commit** — reviewed source, tests, documentation and clearly synthetic
  data without secrets or private machine/customer information.
- **B. Do not commit** — credentials, environment files, databases/backups, dependency
  environments, caches, sensitive raw logs and unnecessary generated output.
- **C. Manual review needed** — files with publication/privacy uncertainty.

Explicitly say **None** for empty groups and provide a recommended commit message.
Do not stage, commit or push as part of this review. Do not delete user files.
