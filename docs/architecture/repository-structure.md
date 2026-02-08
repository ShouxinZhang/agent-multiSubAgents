# AI Journey - 仓库架构文档

## 目录结构

<!-- REPO-TREE-START -->
```
AIJourney/
├── .agents/                                 # 本地 Agent Skills 与执行规范目录
├── demos/                                   # 示例与实验性功能目录
│   └── gomoku-10x10-kernel/                 # 10x10 五子棋多 Agent 实时演示子模块
├── docs/                                    # 项目文档目录
│   ├── architecture/                        # 仓库结构与架构说明文档目录
│   └── dev_logs/                            # 开发过程日志目录
├── scripts/                                 # 工程自动化脚本目录
│   ├── repo-metadata/                       # 仓库结构元数据扫描与文档生成脚本
│   ├── review/                              # AI 评审流水线脚本与产物目录
│   └── restart.sh                           # 仓库级 GUI 重启入口脚本（转发到 demo）
├── .gitattributes                           # Git 属性配置
├── .gitignore                               # 仓库级忽略规则
├── AGENTS.md                                # 仓库级 Agent 行为与交付约束说明
└── LICENSE                                  # 项目开源许可证
```
<!-- REPO-TREE-END -->
