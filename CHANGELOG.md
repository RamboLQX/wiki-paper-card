# Changelog

本项目的版本变更记录。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循语义化版本。

## [Unreleased]

### 新增与改进

- **Knowledge Tree 单树检索**：`wiki/meta/knowledge-tree.md` 统一为人与 Agent 共用的树入口。检索先匹配领域、Topic、论文叶子或开放项，再只展开候选分支；具体论文未命中时回退 `wiki/index.md` 与 `wiki/sources/`。publisher 不再创建或更新 `agent-tree.md`；升级前遗留的该文件保持不变，可由用户安全删除。
- **Topic 空开放问题可读性**：没有独立开放问题时保留 `## 开放问题` 标题并显示说明性占位；具有明确推进方向的条目仍只进入研究空白区，不为填满栏目重复写入。新增真实问题时占位自动消失，问题全部归档或移除后自动恢复。
- **研究空白生命周期记录**：研究空白继续用 open/answered 表达是否关闭，部分推进通过稳定 ID 的 `progress_updates` 保存论文、方法、结果、证据和剩余边界，并在 Topic 及聚合视图标记“已有进展”。完全解决时归档页就地展示解决论文、方法、结果、范围和证据；旧 sidecar 可按已有字段继续读取，无需全库迁移。
- **Codex 正式适配**：新增 `.agents/skills/` 安装布局、Vault 级 `AGENTS.md`、`.agents/WIKI_PAPER_CARD_ROOT` 指针与 Codex 编排映射。`install.sh` 新增 `--host codex` 和 `--host all`，并保持默认值及 `both=claude+dsh` 的旧语义。Codex 每篇论文使用一个 fresh processor，同时最多三个且受当前会话可用子 Agent 槽位限制；全批次审计通过后只创建一个 linker。
- **多宿主入口一致性**：`template/CLAUDE.md` 与新增的 `template/AGENTS.md` 使用字节一致的宿主无关 Vault 规则；安装器对已有入口文件继续 no-clobber，`all` 模式下两份最终内容不一致时明确警告。
- **Paper Card 与 Topic 统一可读性契约**：共享 writing guide 改为“先完整、后精练”。Paper Card 的研究问题、背景、核心思想、方法、结论、公式解释和研究想法采用可连续阅读的段落；必要的模块、实验、局限和批判分析表格继续保留，并由本地审计阻断明显碎片化输出。
- **Topic schema 3.0 与无标记正文**：Topic 从追加式关键发现条目升级为受控的概述、综合认识和真实争议段落。link plan 保留 finding/contradiction 证据台账，publisher 使用标准 Markdown 脚注，不再重复输出 finding bullets。稳定开放项与重放状态进入 `wiki/meta/topic-state/` sidecar，正文不再出现 `wiki-paper-card:*` 协议。
- **paper-card / gap-mining 双入口协调**：ingest 独占 Topic 叙事、证据台账与论文对照；mining 经用户确认后只按稳定 ID/origin 维护开放项。两者共用 `publish_wiki.py`，通过 `base_topic_sha256` 乐观锁阻断过期计划；mining 归档答案时返回 `narrative_refresh_recommended`。
- **兼容与迁移边界**：schema 2.0 继续兼容旧计划和页面。已有 schema 3.0 marker 页面在下一次有效更新时单页迁移为 clean Markdown + sidecar；无 marker 且无 sidecar 的历史页面返回 `narrative_migration_required` 并保持零写入，不提供隐式全库迁移。

### 修复方法

- **仓库根目录解析确定性化**：`<REPO_ROOT>` 不再依赖 Agent 从 skill 软链推断。`install.sh` 向每个宿主目录写入 `WIKI_PAPER_CARD_ROOT` 指针文件（DSH：`$VAULT/.dsh/`；Claude Code：`$VAULT/.claude/`，内容为仓库绝对路径），自检校验指针指向的 `vendor/nature-paper-card/SKILL.md` 可读。`dsh-mode.md`、`wiki-paper-card/SKILL.md`、`workflow-contract.md` 与 `template/CLAUDE.md` 的解析规则统一为：环境变量 → 指针文件 →（DSH）`readlink -f` 软链，解析后必须验证再继续，禁止猜测路径；skill 内 `../../` 相对引用明确以 skill 目录（`skill` 工具返回的 resourceBase）为基准换算。修复 DSH 会话未设置 `WIKI_PAPER_CARD_ROOT` 时模型推断仓库根偏差一级、首次读取报 `cannot read ".../skills/vendor/nature-paper-card/SKILL.md": not found` 的问题（与既有 `../../adapters/dsh/dsh-mode.md` 修复同属一类，根因是路径解析依赖模型推断）。

### 改动文件

- `scripts/install.sh`：新增 `write_repo_root_pointer`；`verify_host_resources` 增加指针文件与目标仓库校验；安装完成提示同步。
- `adapters/dsh/dsh-mode.md`：环境确认段新增确定性解析顺序、验证门与 `../../` 基准规则。
- `skills/wiki-paper-card/SKILL.md` / `references/workflow-contract.md` / `template/CLAUDE.md`：去除"从环境或 skill 所在仓库解析"的推断式措辞。
- `docs/agent-quick-setup.md` / `docs/installation.md` / `adapters/{dsh,claude-code}/README.md` / `README.md` / `README.en.md`：指针文件机制与验证命令同步。
- `scripts/audit_wiki_paper_card.py` / `scripts/publish_wiki.py`：新增 Paper Card 结构化可读性门禁、Topic sidecar、无标记叙事、标准脚注、段落化研究空白、过期计划预检、mining stub 和叙事刷新警告。
- `skills/wiki-paper-card/references/`、`skills/wiki-gap-mining/`、`skills/wiki-shared/`：同步 Topic 叙事、证据台账、双入口权限与迁移边界。
- 测试：`tests/test_install.py` 新增 Codex 安装与指针用例；`tests/test_audit_link_plan.py`、`tests/test_audit_wiki_paper_card.py` 与 `tests/test_publish_wiki.py` 覆盖 schema 3.0、可读性合同、二篇到五篇多批次、双入口冲突、迁移阻断、研究空白生命周期和幂等回归；全量 166 个测试通过。

## [0.9.1] - 2026-08-30

### 新增与改进

- **产物与工作流说明**：新增 `docs/artifacts.md`，按"面向用户 / 面向机器 / 中间过程"三层解释全部产物，讲清处理论文与挖掘研究空白两个工作流的完整过程，重点说明 gap-mining 的决策闭环（报告待确认清单 → 用户逐项确认 → 写回 Topic 页与仪表盘；不确认则 wiki 无变化）。README 中英文新增 4.4 小节作入口，四个 skill README 的产物小节同步指向该文档。
- **收尾说明要求**：`workflow-contract.md` 与 `wiki-gap-mining/SKILL.md` 新增 User-Facing Closing Summary 契约，要求 Agent 收尾时向用户列出本次产物、各文件含义、是否需要用户决策。
- **Topic 页写作规范**：新增 `skills/wiki-shared/references/writing-guide.md`，确立"动机优先于细节"原则。概述写 3-5 句并覆盖研究问题、动机、进展与分歧；关键发现必须说明对读者意味着什么；正文散文禁止用分号连接两个命题、禁止破折号插入从句，压缩条目（对照表、gap 主行、仪表盘行）一行一意，术语内连字符与公式代码不受影响。
- **研究空白动机字段必填**：open 状态的研究空白必须携带非空 `significance`（为什么值得做：改变什么判断或选择），`audit_link_plan.py` 缺失即报错；`evidence_boundary` 缺失降级为 `[待验证]` 方向并给出 warning；answered 归档条目豁免。`linker-brief.md`、`mining-brief.md`、`link-plan-schema.md`、`wiki-schema.md` 同步，linker 与 miner 的 Required Reads 加入 writing-guide。

### 改动文件

- 新增：`docs/artifacts.md`、`skills/wiki-shared/references/writing-guide.md`。
- `audit_link_plan.py`：open gap 缺 significance 报 `research_gap_significance` 错误；缺 evidence_boundary 报 warning。
- `README.md` / `README.en.md`、`skills/wiki-paper-card/README{,.en}.md`、`skills/wiki-gap-mining/README{,.en}.md`、`skills/wiki-paper-card/references/{workflow-contract,linker-brief,link-plan-schema}.md`、`skills/wiki-gap-mining/{SKILL,references/mining-brief}.md`、`skills/wiki-shared/references/wiki-schema.md`：上述契约与入口同步。
- 测试：更新 `test_audit_link_plan.py`（significance 必填、answered 豁免、v2 可选字段降级为 experiment 等）与 `test_publish_wiki.py` 两处 mining plan 构造；全量 119 个测试通过。

## [0.9.0] - 2026-08-30

### 新增与改进

- **知识树改为主题优先结构**：`wiki/meta/knowledge-tree.md` 从"领域 → 论文/主题/开放问题/研究空白四个扁平列表"重构为"领域 → 主题节点（带 index 一句话摘要作 signpost）→ 该主题的论文/开放问题/研究空白嵌套其下"；未归入任何主题的论文在领域级「未归入主题的论文」分组。多归属论文在每个所属主题下各列一次；空领域分组不再渲染。分类视图（按主题分类）保持原样。主题归属关系完全来自 topic frontmatter `sources`，零新增 LLM 索引成本、不新增页面或 meta 文件；索引与 research.md 不变。这使大模型产出的 topic 归纳成为树的中层导航节点，读者视图与 PageIndex 式逐层剪枝检索同时受益。
- **分类集合起始草案文档化**：`wiki-schema.md` 的 category 说明补充推荐起始集合（评测基准与数据集 / 消解与干预方法 / 行为规律 / 机制解释 / 多模态冲突 / 跨域迁移与统一度量 / 综述与元评估 / 领域应用），标注为按 Vault 用户持有、发布器不强制；发布器只按 frontmatter 实际存在的分类分组。
- **Agent 检索渐进式披露**：新增 `wiki/meta/agent-tree.md`——Agent 检索第一跳的 signpost 索引（领域 + 主题一句话摘要 + 未归属论文，不含叶子明细），发布器每次发布时与知识树一同确定性重建。`knowledge-tree.md` 定位为人读导航视图（主题优先嵌套全貌，结构不变），两个文件共用同一份确定性收集。`retrieval-protocol.md` 第一跳改为：只读 agent-tree 选分支（≤3 个主题），再逐层打开候选页面（topic 页 → source 页小节），实现 PageIndex 式逐层下降；agent-tree 不存在时回退读知识树再退 index。同步 CLAUDE/template 检索路由、gap-mining 读图入口、wiki-schema、knowledge-model、workflow-contract、README 中英文视图表。
- **检索协议同步**：树中嵌套条目不再重复「来源」后缀、research.md 的领域平铺条目保留来源链接；定向问答第一跳不再首选人读导航树。

### 修复方法

- `audit_wiki_state.py`：`WIKILINK_RE` 的目标捕获组排除反斜杠并接受可选转义管道，表格单元格里 `[[A\|B]]` 形式的 wikilink 不再把目标解析成 `A\` 而误报 unresolved_link。实测一个 34 页 Vault 从 82 条误报降为 0（该库无真实未解析链接）。新增回归测试 `test_table_escaped_pipe_wikilink_resolves`（存在页转义链接通过、真实缺失目标仍报）。

### 改动文件

- `publish_wiki.py`：新增 `collect_topic_tree`（topic→论文归属收集）与 `gap_priority` 辅助函数；`render_knowledge_tree` 重写为主题优先渲染；新增 `render_agent_tree` / `build_agent_tree` 并随发布写回 `wiki/meta/agent-tree.md`；CLI 调用点同步。
- `audit_wiki_state.py`：`WIKILINK_RE` 兼容表格转义管道 `\|`。
- `wiki-schema.md` / `knowledge-model.md` / `workflow-contract.md`：同步主题优先树结构、agent-tree 与 topic 兼任 signpost 节点的职责。
- 测试：改造 `test_cli_writes_knowledge_tree` 与 `test_knowledge_tree_groups_by_domain`，新增 `test_knowledge_tree_lists_paper_under_each_assigning_topic`、`test_agent_tree_signposts_only` 与 `test_table_escaped_pipe_wikilink_resolves`；稳定性测试同时覆盖知识树与 agent-tree；全量 117 个测试通过。

## [0.8.2] - 2026-08-30

### 文档与视觉

- **README 产品化重构**：中英文 README 按“项目价值 → 快速开始 → 安装 → 框架结构 → 技术设计”重新组织。开头直接说明知识与经验数字化累积的价值，补充知识库问答能力，并精简重复的使用与技术说明。
- **Skill 索引与详情页**：新增 `wiki-paper-card`、`wiki-gap-mining` 的中英文详情页，标明 Stable / Beta 状态、触发方式、主要产物和运行边界；明确 `wiki-shared` 是共享内容目录，不作为独立 Skill。
- **统一产品视觉**：使用替代内容重新设计封面和产品效果图，展示 Paper Card、跨论文关系、知识库问答和研究空白；同步保留中英文工作流程图，并移除旧版横幅。

### 验证

- 中英文 README 章节结构、编号与本地链接检查通过。
- Markdown 差异与尾随空白检查通过。
- 本版本只调整文档与视觉资产，未改变运行代码和流程契约。

## [0.8.1] - 2026-08-30

### 新增与改进

- **语义去重与跨页互链的确定性写回**：topic 动作新增三个字段——`remove_open_questions` / `remove_research_gaps`（非空字符串列表，发布器按空白归一化的子串匹配删除对应条目）与 `annotate_research_gaps`（`{match, note}` 对象列表，把互链注释插入匹配 gap 的承接句尾；无承接句尾时降级为「相关空白」子条目）。审计校验三者形状，畸形即阻断。该能力源自 5.0 测试会话的实战扩展，经代码审查、补测试与契约同步后收编。

### 修复方法

- `audit_link_plan.py`：校验三个字段的形状（字符串列表 / match+note 对象），错误阻断。
- `publish_wiki.py`：`merge_topic_page` 支持按片段删除开放问题与研究空白、按 `match` 给 gap 块加互链注释；新增 `annotate_gap_block` 辅助函数。
- 契约文档：`link-plan-schema.md` 补三字段定义与规则；`mining-brief.md` 的语义去重纪律写明用这三个字段表达编辑。

### 修复结果

- 挖掘确认项里的"删除重复条目 / 加跨页互链注释"现在通过 link-plan 确定性落地，不再依赖手工编辑 wiki 页。
- 审计能在发布前拦截畸形的去重/注释指令；未命中的片段是无害的空操作。

### 验证

- 新增 3 个回归测试：三字段审计校验、按片段删除问题与空白、注释插入承接句尾与降级子条目。
- 项目 114 个测试、smoke test 全部通过。

## [0.8.0] - 2026-08-29

### 新增与改进

- **研究空白 v2 条目**：`research_gaps` 新增 6 个可选字段 `significance` / `evidence_boundary` / `experiment` / `success_criterion` / `risk` / `priority`（高/中/低）。发布器把它们渲染成主行 + 缩进子条目（只渲染已填字段）；带 v2 字段但缺 `evidence_boundary` 与 `experiment` 的条目标 `[待验证]`（待验证方向）；不带任何 v2 字段的条目保持旧的单行渲染，逐字节兼容。研究仪表盘与知识树的空白聚合只取主行，按优先级排序。
- **topic 分类轴**：topic 动作支持可选单值 `category`（如 模型优化 / 评估框架），发布器写入 frontmatter；知识树在领域视图之后新增「按主题分类」视图，未分类 topic 落在「未分类」分组。分类集合小而稳定、由用户持有。
- **信息排布纪律**：`knowledge-model.md` 新增「内容类型→区块」映射表与编辑式合并纪律；`linker-brief.md` 补第三条分类规则（`open_questions` 与 `research_gaps` 排他，禁止同候选双写）；`create_topic` 收紧为"至少两篇共享同一问题/机制/证据空间"，两篇仅抽象相似的未来想法不建页，新 topic 默认 `stub`（候选主题）。
- **gap-mining 流程收紧**：SKILL.md 增加输入意图分流（raw 路径 → 先查是否已入库）与 scope 退化说明；miner 报告新增 Top 空白速览、候选分级、结构化待确认清单，候选字段与 link-plan 字段同名同构；mining 写回只允许三种动作（增空白/开放问题、标记 answered 归档、经确认的候选 topic 建页），并要求写回前语义去重；DSH 下 Phase B 用 `send_message` 唤醒同一 miner 生成 link-plan。

### 修复方法

- `publish_wiki.py`：`normalize_gaps` 携带新字段；`gap_bullet` 渲染子条目与 `[待验证]` 标签；新增 `gap_key` / `section_bullet_blocks` / `block_root_text`，gap 合并改为块级（保留已有条目的子条目）；`priority_sort_key` 用于仪表盘与知识树排序；`collect_topic_categories` + `render_knowledge_tree` 分类视图；`topic_page_text` / `merge_topic_page` / `rebuild_page` 支持 category。
- `audit_link_plan.py`：新字段轻校验（给了但为空 → warning 不阻断）；`priority` 值域 高/中/低（违例报 error）；topic 动作 `category` 轻校验。
- 契约文档：`link-plan-schema.md`、`knowledge-model.md`、`wiki-schema.md`、`linker-brief.md`、`mining-brief.md`、`wiki-gap-mining/SKILL.md`、`adapters/dsh/dsh-mode.md` 同步以上语义。

### 修复结果

- 单条研究空白从一行摘要升级为"摘要 + 可检验细节"，学者可快速判断值不值得做、卡在哪、怎么做、做到什么算成。
- 知识库多出一个与来源领域正交的主题分类轴，检索与全库整理都能按分类定位。
- 探索性候选不再直接污染正式知识：待验证方向带标签、候选 topic 保持 stub、mining 写回不再触碰概述/对照/发现。

### 验证

- 新增 12 个回归测试：v2 字段渲染与 `[待验证]` 标签、旧格式逐字节兼容、合并保留已有子条目、category 创建/更新/保留、priority 排序、知识树分类视图、审计新字段与 priority 值域。
- 项目 111 个测试、smoke test 全部通过；旧格式 gap 渲染与既有页面更新行为不变。

## [0.7.3] - 2026-08-28

### 问题与影响

- **研究空白的"可追溯"校验仍有漏洞**：0.7.2 只预检 topic action 的 `papers` 引用，研究空白的 `source_refs` 与回答证据 `answered_by` 指向的页面未做存在性校验，一个 gap 仍可指向不存在的来源页通过审计并发布，形成不可核验的研究空白。
- **ingest 计划仍有部分发布风险**：预检只对 mining 计划生效；ingest 批次某来源页缺少 `paper-card.md` 时，来源页写不出去，但 Topic、index、log 仍会写入，产生指向不存在来源页的 Topic。
- **旧字符串 gap 的报错指引不足**：审计拒绝旧字符串 gap 时只提示"必须用结构化对象"，未说明必需字段与契约文档位置，迁移成本高。

### 修复方法

- `publish_wiki.py`：将原 `mining_source_errors` 扩展为统一的 `preflight_errors`。在任何写入前校验全部来源引用（topic `papers`、gap `source_refs`、answered 的 `answered_by`）：属于当前批次（本趟会写）的页面跳过存在性检查，其余引用必须存在于 `wiki/sources/` 下，缺页、越界路径或非来源页引用即以退出码 1 阻断；同时新增批次来源页 `paper-card.md` 存在性预检，ingest 与 mining 统一生效。
- `audit_link_plan.py`：旧字符串 gap 的报错信息明确列出必需字段（`gap`/`source_refs`/`direction`/`continuity`）并指向 `link-plan-schema.md`；`research_gap_shape` 报错同步列出字段要求。
- 契约文档（`workflow-contract.md`、`link-plan-schema.md`、`mining-brief.md`）同步统一预检语义。

### 修复结果

- 研究空白或回答证据引用不存在的来源页时，整次发布在任何 Wiki 写入前被阻断。
- ingest 批次缺少最终卡片时同样在写入前阻断，不再产生"Topic 已写、来源缺失"的部分发布。
- 被拒绝的旧格式 gap 报错可直接指引如何迁移。

### 验证

- 新增 3 个回归测试：gap `source_refs` 指向缺页时阻断、ingest 缺卡片时阻断、gap 引用本批之外已存在页面时放行；更新 mining 缺页与审计旧字符串断言的报错文案。
- 项目测试、smoke test 与两个固定上游测试集全部通过。

## [0.7.2] - 2026-08-28

### 问题与影响

- **研究空白的来源可追溯契约未被审计完整执行**：`link-plan` 文档要求研究空白携带 `source_refs`、`direction` 与 `continuity`，但审计器此前允许字符串 gap，也允许只有 `gap/status` 的对象通过；`answered` 条目只检查 `answered_by`，缺少 `answered_pointer` 仍可发布。结果是 Topic、研究仪表盘和知识树可能出现无法回到来源、缺少可检验方向或没有解决证据的研究空白。
- **Mining 缺失来源页时产生部分发布**：mining plan 引用不存在的 `papers` 页面时，发布器仍先写入 Topic，backlink 更新遇到缺页后静默跳过，最终退出码和发布报告仍显示成功。结果是 Topic 到来源页的图关系不完整，且成功状态掩盖了数据一致性问题。
- **KB Context 与新版 Topic 标题不一致**：上下文提取器仍匹配旧标题 `## 争议与矛盾`，而当前模板使用 `## 争议与不确定`，导致已有 Topic 的争议内容没有提供给 processor。
- **`max_pages` 上下文预算被重复使用**：来源页与 Topic 页分别截取 `max_pages`，默认 5 实际最多选入 10 页，突破调用方理解的全局页面预算。

### 修复方法

- `audit_link_plan.py`：新 plan 的 `research_gaps` 只接受结构化对象；每项强制非空 `source_refs`、`direction`、`continuity`，并校验列表元素类型。`answered` 的开放问题和研究空白同时强制非空 `answered_by` 与 `answered_pointer`。发布器保留旧字符串 gap 的渲染兼容，但审计门禁止它进入新的写入计划。
- `publish_wiki.py`：在任何目录、Topic、索引或日志写入前，对 mining plan 的全部 `papers` 引用执行来源页预检；缺页、越界路径或非 `wiki/sources/` 引用立即以退出码 1 阻断。backlink 写入函数不再吞掉缺页或读取异常，预检后的竞态/读取错误也会进入发布错误列表。
- `build_kb_context.py`：同时识别新版 `## 争议与不确定` 与历史 `## 争议与矛盾`；先合并来源页和 Topic 页评分，再全局截取一次 `max_pages`。
- 契约文档同步明确必填字段、历史兼容边界、Mining 发布前置校验和全局页面预算语义。

### 修复结果

- 不可追溯、不可检验或缺少回答证据的 link-plan 在 Wiki 写入前失败。
- Mining 引用缺页时不会创建 Topic 或产生成功假象，来源与 Topic 的双向图关系保持完整。
- Processor 能重新获得新版 Topic 中的争议与不确定内容。
- `max_pages=5` 在来源页与 Topic 页合计范围内最多选入 5 页。

### 验证

- 新增 4 个回归测试，覆盖 gap 必填字段与旧字符串拒绝、`answered_pointer`、Mining 缺页写入门、当前争议标题和全局 `max_pages`。
- 项目测试、smoke test 与两个固定上游测试集全部通过。

## [0.7.1] - 2026-08-24

### 修复

- **install.sh 宿主资源链接**：安装时除 skill 目录外，同时把 `adapters/`、`vendor/`、`scripts/` 软链到宿主层的 `../../` 位置（Claude Code：`$VAULT_ROOT/.claude/`；DSH：`$VAULT_ROOT/.dsh/`），并新增安装自检：按 DSH 词法解析规则校验 `../../adapters/dsh/dsh-mode.md`、`../../vendor/nature-paper-card/SKILL.md`、`../../scripts/build_processor_pack.py` 可读，断链以退出码 1 报错。修复技能内 `../../` 引用在 Vault 安装布局下解析到不存在路径、DSH 会话每次报 `cannot read ".../adapters/dsh/dsh-mode.md": not found` 的问题。
- `wiki-paper-card` 与 `wiki-gap-mining` 的 `SKILL.md`：反引号形式的 `adapters/dsh/dsh-mode.md` 引用统一改为 `../../adapters/dsh/dsh-mode.md`，与 markdown 链接写法一致（DSH 按技能 base 目录解析相对路径，两种写法此前解析结果不同）。
- 测试：新增 `tests/test_install.py`（安装布局回归测试：技能与 `adapters/vendor/scripts` 兄弟软链、`../../` 词法解析可读、幂等重跑、资源路径冲突退出码 1）。

## [0.7.0] - 2026-08-24

### 新增

- **`wiki-gap-mining` skill**：跨组/全库研究空白挖掘入口。范围 = 用户指定的域集合（`raw/papers/` 一级目录）或全库；Phase A 只读挖掘并产出 `work/gap-mining-report.md`（候选空白、跨组已解决关系、已解决轨迹），Phase B 在用户确认后生成 link-plan 并走确定性审计与发布写回。读侧复用 retrieval-protocol 的 survey 纪律（含 topic 页归档小节），写侧仍由 `publish_wiki.py` 执行。
- **link-plan `purpose` 字段**（`ingest` 默认 / `mining`）：mining plan 的 `batch.source_pages` 为空、`batch.label` 命名本次挖掘，topic 动作引用已有 source 页；审计按模式应用不同规则（mining 下 `create_topic` 要求至少两篇已有论文支撑、允许批外引用）。
- **发布器 mining 支持**：为 mining plan 引用的已有 source 页追加 topic backlinks（新增 `source-backlinks` 写入类型，去重、幂等）；日志批次标题使用 `batch.label`。

### 变更

- `template/CLAUDE.md` 与仓库 `CLAUDE.md` 路由新增空白挖掘入口（第 3 条），并同步 retrieval-protocol 的 research.md 读取条件（选题类查询才读）；`retrieval-protocol.md` 明确 survey 只读、挖掘归 `wiki-gap-mining`。
- `install.sh` 挂载第三个 skill；`dsh-mode.md` 增加 miner 子代理编排映射与验证清单；`wiki-shared` SKILL.md 引用方补充。
- 测试：mining plan 审计（空 source_pages 放行、批外引用、双论文门槛、purpose 校验）与端到端发布（update/create topic、已有页 backlinks、日志标题、幂等）。

## [0.6.0] - 2026-08-24

### 新增

- **开放问题/研究空白的解决归档机制**：`link-plan.json` 的 `open_questions` 支持对象 `{question, status, answered_by, answered_pointer}`（字符串兼容视为 `open`），`research_gaps` 支持 `status`（`open`/`answered`）、`answered_by`、`answered_pointer`。当后续批次论文回答既有开放问题或填补研究空白时，linker 将条目标记 `answered`，发布器把它从 topic 页的 `## 开放问题` / `## 研究空白与候选方向` 移除并移入归档小节 `## 已解决的问题` / `## 已解决的研究空白`（有内容才渲染）。
- **聚合只显示当前开放项**：`wiki/meta/research.md` 与 `wiki/meta/knowledge-tree.md` 只聚合仍开放的条目，已解决条目不再出现在树与仪表盘中；全部解决时 research.md 渲染占位提示而非残留旧内容。

### 变更

- **research.md 与 knowledge-tree 分工明确**：knowledge-tree 为领域优先导航树（lookup 剪枝入口），research.md 为问题类型优先的全局开放问题/研究空白清单（选题扫描入口）；同一批 topic 页条目的两种透视，文本一致是设计使然，单一事实来源在 topic 页。`retrieval-protocol.md` 第一跳改为：定向问答只读 knowledge-tree，仅"按问题/空白选题"类查询才读 research.md。
- `audit_link_plan.py`：新增 `open_question_shape/status/answer_source` 与 `research_gap_status/answer_source` 校验（answered 必须带 `answered_by`，status 仅限 `open`/`answered`）。
- `publish_wiki.py`：`merge_topic_page` 的开放问题/研究空白合并从纯追加升级为"open 追加 + answered 迁移归档"；`topic_page_text` 支持对象格式并渲染归档小节；`render_research_page` 在无内容时返回占位仪表盘。
- topic 页模板、wiki-schema、knowledge-model、link-plan-schema、linker-brief、wiki-integration、workflow-contract 同步归档语义与分工说明。

## [0.5.0] - 2026-08-24

### 移除

- **实体页层**：不再生成 `wiki/entities/` 实体 stub。公开数据集/基准/模型族/指标保留在各篇 Paper Card 的 Section 14/15 中作为纯文本，不建独立页面。已有 vault 中的旧实体页不再被写入或更新，knowledge-tree 与 index 不再列出，可标记 `archived` 或保留为只读参考。
- **digest 的 `analysis.datasets/models/metrics` 列表**：`paper-digest.json` schema 升至 3.0，analysis 只保留 `one_sentence_summary`、`problem`、`method`、`key_results`、`limitations`、`critical_observations`、`open_questions`。
- **主题页「相关实体」节**、source 页 `## 关联页面` 中的实体反向链接、检索协议与 KB context 中的实体分支、index 的「实体」节一并移除。

### 变更

- `publish_wiki.py` 只写 source 页与 topic 页：移除实体归一化/变体合并/实体 stub 生成与合并逻辑约 200 行，publish-report 不再统计 entity。
- `audit_paper_digest.py` 只接受 schema 3.0；`audit_link_plan.py` 的 `hub_actions_removed` 提示不再提及实体生成。
- `audit_wiki_paper_card.py` 与 `smoke_test.py` 不再要求 `wiki/entities/` 目录；`install.sh` 不再创建该目录。
- 删除 `skills/wiki-shared/templates/entity-page.md`；wiki-schema、knowledge-model、retrieval-protocol、processor/linker brief、workflow-contract、batch-mode、wiki-integration 与 README 同步改写。

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
