# Repository Structure

## 目录结构

<!-- REPO-TREE-START -->
```
REPO/
├── .agents/                                 # AI agent configuration root
│   └── skills/                              # agent skill definitions
├── apps/                                    # application modules
│   ├── gomoku_codex_cli/                    # dual Codex CLI Gomoku app
│   └── human_thinking_forum_codex_cli/      # human-thinking forum module directory
├── docs/                                    # project documentation root
│   ├── architecture/                        # generated repository metadata and tree
│   └── dev_logs/                            # development cycle logs
├── scripts/                                 # build, review, and tooling scripts
│   ├── repo-metadata/                       # repo metadata management toolset
│   ├── review/                              # automated code review pipeline
│   ├── tools/                               # Python quality check tool modules
│   └── check_errors.sh                      # multi-language quality gate shell script
├── .gitattributes                           # git attributes configuration
├── .gitignore                               # git ignore rules
├── AGENTS.md                                # root agent instructions for the repo
├── LICENSE                                  # project license file
├── package-lock.json                        # npm dependency lockfile
├── restart_forum.sh                         # one-click launcher for forum web app
└── restart.sh                               # one-click restart launcher for Gomoku app
```
<!-- REPO-TREE-END -->
