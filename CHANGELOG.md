# Changelog

本项目的版本变更记录。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循语义化版本。

## [0.2.0] - 2026-08-22

### 新增

- DeepSeek Harness（DSH）运行宿主适配：
  - `adapters/dsh/dsh-mode.md`：工作流契约到 DSH 原生能力的编排映射（后台 subagent、workflow_status 完成检查、send_message 修正循环）。
  - `scripts/install.sh`：幂等多宿主安装（`--host claude|dsh|both`），冲突检测、no-clobber 复制、符号链接校验。
- Processor 上下文 pack：
  - `scripts/build_processor_pack.py`：把每篇 processor 需读的 18 个规范文件确定性合并为单个 `processor-pack.md` + SHA 清单，`--verify` 断言 pinned 源未漂移。
- 知识树检索（PageIndex 式树索引 + LLM 树搜索）：
  - `skills/wiki-shared/references/retrieval-protocol.md`：lookup（预算剪枝）与 survey（领域整树展开）双模式检索协议。
  - `wiki/meta/knowledge-tree.md`：publisher 确定性重建的按领域导航树（论文/主题/概念实体 + 别名 + 领域聚合开放问题与研究空白）。
- 研究仪表盘 `wiki/meta/research.md`：按领域（`raw/papers/` 一级目录）聚合开放问题、研究空白与 L1 候选；旧 `wiki/meta/candidates.md` 首次发布自动迁移后不再写入。

### 变更

- 并发策略：DSH 宿主默认 6、上限 8 个并发 processor（Claude Code 保持 3）；"全部审计通过后才 link"顺序门不变。
- `processor-brief.md`：Required Reads 改为读取 processor pack（无 pack 时回退逐个读取）。
- `linker-brief.md` / `link-plan-schema.md`：新增关键发现 vs 研究空白的"两问归类决策程序"，共识信号稳定写入 `## 关键发现`。
- `build_kb_context.py`：alias 参与检索匹配（英文查询可命中中文页面）；零关键词重合时显式标注索引顺序回退。

### 修复

- `publish_wiki.py` 的 `parse_frontmatter` 把 `sources:`/`aliases:` 空值行误判为标量字段，导致枢纽页更新丢失已有 sources 列表（新增回归测试）。
- 完成检查改为事件驱动：处理器派发后不轮询、不按轮次定时重查、不输出耗时/轮次预估，仅在子代理完成通知到达时对账一次（workflow-contract / dsh-mode / batch-mode 同步修订）。

## [0.1.0] - 2026-08-15

### 新增

- 初始公开发布：Sections 01-16 Paper Card 工作流（上游 `nature-paper-card` v1.2.0 快照 + 本项目知识结晶层）。
- L0/L1/L2 三级知识门槛、确定性 prepare/finalize/audit/publish 脚本、批量并发编排（Claude Code 宿主）。
- L1 候选账本 `wiki/meta/candidates.md`、幂等 Wiki 发布与 index/log 维护。
