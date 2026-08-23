# Changelog

本项目的版本变更记录。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循语义化版本。

## [0.4.0] - 2026-08-24

### 移除

- **concepts 层与升级门**：不再有 concept 页面，不再有 L0/L1/L2 候选分层与升级门；论文私有术语、组件与一次性命名保留在 Paper Card 的 Section 14/15，不建独立页面。已有 vault 中的旧 concept 页面不再被写入或更新，knowledge-tree 不再列出，可标记 `archived` 或保留为只读参考。

### 变更

- **实体页确定性生成**：`publish_wiki.py` 从每批论文 digest 的 `analysis.datasets`、`analysis.models`、`analysis.metrics` 提取公共数据集/基准/模型族/指标，归一化名称、合并变体（最短原始名做页面标题，其余拼写进 aliases），新建 stub 或向已有页面追加"引用来源"wikilinks；实体页只含 frontmatter、标题、固定说明、别名与引用来源，零 LLM 参与，重跑幂等。
- **link-plan.json 与 paper-digest.json 的 schema_version 升至 2.0**：移除 `hub_actions` 与 `candidates` 字段，audit 对残留字段报错。
- **linker 只做 topic 决策**：wiki-linker 子代理只产出 topic actions（`create_topic`/`update_topic`），不再做 hub 决策。
- **研究仪表盘去 L1 台账**：`wiki/meta/research.md` 只聚合开放问题与研究空白；knowledge-tree 按领域分组，包含论文、主题、实体、开放问题与研究空白。
- topic 页"相关实体与概念"节改名为"相关实体"。

## [0.3.0] - 2026-08-23

### 新增

- `scripts/audit_wiki_state.py`：wiki 结构不变量检查（孤儿表格行、裸内联 HTML 标记、未解析 wikilink、log 重复条目），把"肉眼发现的污染"变成脚本化发现。
- `scripts/smoke_obsidian.py`：发布后 Obsidian 渲染冒烟检查（官方 Obsidian CLI，软门默认；`--strict` 变严格门）。顶部+底部双采样，断言标题装饰存在、`[[链接]]` 与 `**加粗**` 已编译。
- `finalize_paper_card.py`：新增 `html-lint-report.json`——卡片正文禁止代码标记与公式之外的裸内联 HTML 标记（Obsidian Live Preview 会把未闭合的 `<image>` 当 HTML 区域吞掉后续渲染）。
- `audit_link_plan.py`：关系方向一致性检查——`A extends B` 与 `B is_instance_of A` 反向矛盾对报错，自环报错。

### 变更

- `publish_wiki.py`：hub 页"证据/关系"新行改为直接并入现有表格（与 topic 对比表同逻辑），修复空行隔断导致的孤儿表格行；`update_hub` 携带新 `definition` 时替换页首定义段落。
- **概念/实体页瘦身（方向 A）**：hub 页不再渲染"证据"表与"开放问题"（证据留在论文卡与主题页，开放问题只归主题页并被知识树聚合）；link plan 的 evidence 仍作为准入证明被审计校验，但不落页。`hub_actions` 携带 open_questions 时审计给出警告。
- **移除 hub 页"关系"表**：类型化关系字段删除（模板、发布器、link-plan schema、审计、知识模型全部同步）；跨页连接改由定义行文中的 wikilink 表达（Obsidian 反向链接/图谱可见）。旧 plan 携带 `relations` 时审计给 `relations_deprecated` 警告并忽略。
- **实体页准入放宽（策略 C）**：公开数据集/基准/模型族/指标单篇即可建实体页（身份由发布方保证）；概念仍维持跨论文门槛。审计放行单来源 `create_hub`（kind=entity）；linker-brief 增加实体晋升指引与示例。
- **实体漏检提醒**：发布器扫描批次 digest 的 L1 entity 候选，无对应实体页/plan 动作时输出 `missed_entity_promotion` 警告（记入 publish-report，不阻断）。
- **名称变体防重（同名模型/数据集不建重复页）**：批次内审计对归一化同名的 hub 动作给 `hub_name_variant` 警告；发布器对 create_hub 撞上已有页名称/别名（归一化相等或前缀）的动作**拒绝执行**并要求改用 update_hub。被拒绝的动作不再参与 backlinks 与相关枢纽列表（修复泄漏回归测试）。linker-brief 明确模型族粒度与变体走 update_hub。
- `knowledge-model.md`：补齐 10 种关系的主语/宾语方向语义（`extends` 与 `is_instance_of` 同向、反向矛盾）；新增实体页建页标准（数据集/基准/模型族/指标/可复用方法）；更新 Hub Page Content 清单。
- `processor-brief.md`：字面量标签（如 `<image>`、`<CPLINK>`）必须用反引号包裹，禁止裸内联 HTML。
- `workflow-contract.md`：Phase 2 输出新增 `html-lint-report.json`；Phase 5 发布后新增 wiki 状态审计与 Obsidian 渲染冒烟检查。

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
