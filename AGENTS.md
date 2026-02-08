# Repo Agent Instructions

## Language and Communication

- The user communicates in Chinese; by default, write documentation, logs, and explanations in Chinese.
- Communicate from a business-outcome perspective: clarify value, benefits, risks, and impact scope.

## Core Engineering Rules

- Priority order: business outcomes > long-term architecture > concise style.
- Review existing code first to avoid redundant implementation.
- Keep changes minimal; do not add unauthorized scope or feature planning.
- Follow modular design; experimental work must stay within a single sub-module and avoid cross-module pollution.
- New business code must be placed in leaf directories, never in the repository root or other high-level module directories.

## Mandatory Skill Workflow

For every development task, follow `local-dev-workflow` by default and apply the following Skills based on triggers:

- `build-check`: Run quality gates after any code change (build/type/lint checks).
- `dev-logs`: Record each development cycle under `docs/dev_logs/`.
- `repo-structure-sync`: Run when files/directories are added, deleted, moved, or when npm dependencies/scripts change.
- `knowledge-tree-update`: Use only when editing `web/src/data/knowledge-tree.ts`.
- `git-management`: Use when a milestone is reached or before large modifications, to enforce Git checkpoints and commit cadence.

If the user explicitly names a Skill (for example, `$build-check`), it must be prioritized.

## Human Intent Alignment

- Before any code change, align implementation intent with the user and explicitly confirm:
  - Which files will be modified or added
  - The core implementation approach
  - Impact scope and risks
- Start implementation only after the user gives clear confirmation.

## Required Pre-Change Checks

- Read `AGENTS.md` before each change.
- Architecture context strategy:
  - Prefer MCP tools to read the target module directly down to leaf nodes (minimal, on-demand context).
  - Use `docs/architecture/repository-structure.md` as fallback when scope is unclear, MCP is unavailable, or cross-module impact must be evaluated.
- Create a backup before any deletion or rollback operation.

## Quality and Verification

- After frontend code changes, run at minimum:
  - `cd web && npm run lint`
  - `cd web && npm run dev` (verify there are no runtime errors in output)
- Run additionally as needed:
  - `bash scripts/check_errors.sh`
  - `cd web && npm run test`
- Delivery without verification is prohibited.

## Documentation and Traceability

- Keep `docs/architecture/repository-structure.md` synchronized with actual repository structure.
- For each development cycle, add a log under `docs/dev_logs/{YYYY-MM-DD}/` with incrementing sequence filename.
- Each log must include: original user prompt, second-level timestamp, file list, change details, and verification results.

## Automation and Version Policy

- Automate every step that can be automated; do not push executable work back to the user manually.
- When installing SDKs or Python packages, use the latest verifiable stable versions to avoid compatibility issues from outdated releases.

## Prohibited Behaviors

- Committing code without checks/tests.
- Finishing development without updating `dev_logs`.
- Not updating `repository-structure.md` after structural changes.
- Asking the user to manually do work that can be scripted.
- Installing outdated SDKs/dependencies when newer stable versions are available.
