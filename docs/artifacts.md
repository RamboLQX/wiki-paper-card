# 工作产物与工作流说明

本文档解释 `wiki-paper-card` 框架在运行过程中产生的所有文件。每一份产物代表什么、由谁生成、哪些需要你关注、哪些不需要。本文同时解释论文处理、研究空白挖掘和旧版 Vault 升级三个主要工作流，以及过程中需要你做决策的环节。

## 目录分层的职责

框架把三类内容放在三个目录里，先分清这三个目录就不会混淆产物：

| 目录 | 职责 | 你是否需要关注 |
|---|---|---|
| `raw/` | 你的原始论文资料。框架只读，从不修改 | 由你维护，框架不会动它 |
| `work/` | 处理过程中的草稿、审计报告和计划文件 | 大部分不需要看，只有面向你的报告例外 |
| `wiki/` | 通过审计后正式发布的知识页面 | 这是框架的核心产出，日常阅读都在这里 |

判断方法很简单。你在 Obsidian 里打开的是 `wiki/` 下的页面。`work/` 里的文件是处理过程的中间记录，除非 Agent 在收尾说明中让你看某一篇，否则不需要打开。

## 工作流一：处理论文（wiki-paper-card）

开始前先固定一次处理范围：

| 模式 | 结果 | 不会执行 |
|---|---|---|
| `card-only` | `work/` 中经过整理和审计的 Paper Card | digest、连接、发布和全部 `wiki/` 写入 |
| `wiki-topic` | 发布 Paper Card，并维护 Topic、索引、日志和聚合视图 | 新增、推进、回答、标注或删除研究空白；既有空白保持不变 |
| `wiki-full` | 完整入库与研究空白维护 | 仅受常规证据与审计边界限制 |

用户已经说明范围时直接开始；只说“处理/分析论文”时，Agent 在开始前询问一次，
同一批论文不逐篇询问。完整 Wiki 流程分五步：

```text
1. 准备   提取论文文本和已有知识库上下文
2. 分析   每篇论文独立生成 Paper Card 与分析摘要
3. 检查   确定性脚本审计卡片结构、证据和公式
4. 连接   批量比较论文，决定创建或更新哪些 Topic
5. 发布   确定性脚本写入 wiki/，并更新索引、日志和仪表盘
```

每一步的产物如下：

| 阶段 | 产物 | 类型 | 说明 |
|---|---|---|---|
| 准备 | `work/<名称>/source_bundle.json` | 机器 | 提取出的论文文本，供分析使用 |
| 准备 | `work/<批次>/batch-manifest.json` | 机器 | 仅两个 Wiki 模式生成；从 source bundle 复算并固定本批论文的原始路径、SHA、目标页面和 work_dir |
| 准备 | `work/<名称>/kb-context.md` | 机器 | 已有知识库的相关上下文摘要 |
| 分析 | `work/<名称>/paper-card.md` | 中间 | 论文分析的完整草稿，发布前会经过审计和整理 |
| 分析 | `work/<名称>/paper-digest.json` | 机器 | 仅两个 Wiki 模式生成；论文的结构化摘要，连接阶段使用 |
| 检查 | `work/<名称>/paper-digest-finalize-report.json` | 机器 | 记录 digest 中 SHA、来源页路径和单篇 seed 成员等系统字段的整理前后值；不修改语义内容 |
| 检查 | `work/<名称>/audit-report.json` 等 | 机器 | 结构与证据审计报告，失败会阻止继续 |
| 连接 | `work/<名称>/link-plan.json` | 机器 | schema 3.0 跨论文计划，包含完整叙事、证据台账、稳定开放项 ID 和 Topic 基线哈希 |
| 发布 | `work/<名称>/publish-report.json` | 机器 | 实际写入 wiki/ 的结果记录 |

发布后进入 `wiki/` 的正式页面：

| 页面 | 说明 |
|---|---|
| `wiki/sources/papers/…` | Paper Card，以连续段落解释单篇论文，同时保留公式、实验表和证据位置 |
| `wiki/topics/…` | Topic，用完整段落综合多篇论文的领域认识、边界与争议，并保留对照表、开放问题和段落化研究空白 |
| `wiki/meta/topic-state/…` | Topic 的机器 sidecar，保存稳定 ID、来源、annotation 和重放状态；不在正文暴露维护协议 |
| `wiki/meta/research.md` | 研究仪表盘，汇总当前所有开放问题与研究空白 |
| `wiki/meta/knowledge-tree.md` | 人与 Agent 共用的知识树；先匹配节点，再局部展开分支 |
| `wiki/index.md` / `wiki/log.md` | 页面索引与每次处理的日志 |

除开始时选择一次处理范围外，处理论文的过程不需要逐篇决策。Topic 的创建或更新由连接阶段根据准入规则自动判断。`wiki-topic` 的链接计划受到确定性门禁约束，不能携带任何研究空白内容或变更指令，发布时保留已有空白。更新时，linker 输出基于全部当前证据的完整叙事，发布器按固定标题整块替换概述、综合认识和真实争议，不按批次追加摘要。精确证据使用标准 Markdown 脚注，维护状态进入 sidecar，因此 Obsidian 正文中不会出现内部 marker。Agent 收尾时会汇报本次创建和更新了哪些页面。

## 工作流二：挖掘研究空白（wiki-gap-mining）

基于已有知识库挖掘开放问题、研究空白和候选研究方向。这个流程分两阶段，第二阶段需要你决策：

```text
第一阶段（只读）  挖掘 Agent 阅读 Topic 页与仪表盘
                  产出笔记和报告
                  报告末尾给出待确认清单
                      │
                      ▼
第二阶段（写回）  你逐项确认报告中的候选条目
                  挖掘 Agent 根据你的确认生成写回计划
                  确定性脚本把结果写入 Topic 页和仪表盘
```

两份关键产物：

| 产物 | 类型 | 说明 |
|---|---|---|
| `work/gap-mining-notes.md` | 中间 | 挖掘 Agent 的工作笔记，用于整理线索。你不需要读 |
| `work/gap-mining-report.md` | 面向用户 | 研究空白报告，带来源依据、可检验方向和建议落点。这是你需要读的文件 |

**报告是决策文件。** 报告的「待确认清单」逐条列出候选空白，每条需要你决定四件事：

- 是否采用这条候选；
- 写到哪里（现有 Topic、新建候选 Topic，还是只留在报告里）；
- 知识状态（正式空白还是待验证方向）；
- 写入哪个区块。

你逐项确认后，Agent 才会生成写回计划并更新 Topic 页的「开放问题」和「研究空白与候选方向」区块，同时同步研究仪表盘。**只读报告不确认，知识库不会有任何变化。** 没有值得记录的空白也是有效结果，报告会直接说明，不会为了数量填充条目。

gap-mining 不能改写 Topic 的概述、综合认识、争议或论文对照表。它与 paper-card 通过稳定条目 ID 共享开放项，并共用同一个确定性发布器。如果两份计划基于同一个旧 Topic，先发布的一份会使另一份过期；过期计划在任何 Wiki 写入前被阻断。

## 工作流三：升级已有 Vault 与迁移旧 Topic

升级先把运行入口更新和 Topic 内容迁移分开处理。`inspect` 只读取 Vault 并把分类报告写入 `work/upgrade/<run-id>/`；`install.sh --runtime-only` 只更新宿主运行文件和版本标记，不改动 `raw/` 或 `wiki/`。只有旧 Topic 确实需要迁移时，Agent 才生成显式 `purpose: migration` 计划并等待你确认。

确认迁移后，升级器先在完整 `wiki/` 副本中发布、审计并检查写入白名单；全部通过后才备份真实目标并按计划提交。基线哈希过期、越界写入或审计失败都会在真实 Wiki 写入前阻断。需要回滚时，升级器先核对迁移后的哈希；页面已被后续编辑则拒绝覆盖。

主要升级产物如下：

| 产物 | 类型 | 说明 |
|---|---|---|
| `work/upgrade/<run-id>/inspection.json` | 机器 | 旧 Topic 分类、运行入口版本和需要人工复核的问题 |
| `work/upgrade/<run-id>/migration-plan.json` | 机器 | 仅包含用户确认目标的 schema 3.0 迁移计划 |
| `work/upgrade/<run-id>/migration-plan-report.json` | 机器 | 迁移计划的确定性审计结果 |
| `work/upgrade/<run-id>/staged-*-report.json` | 机器 | 副本发布和完整 Wiki 审计结果 |
| `work/upgrade/<run-id>/backup-manifest.json` 与 `backup/` | 恢复 | 提交前备份、迁移前后哈希和允许回滚的文件清单 |
| `work/upgrade/<run-id>/wiki-audit-report.json` | 机器 | 真实 Wiki 提交后的最终审计结果 |

完整命令、授权边界和失败处理见 [`agent-upgrade.md`](agent-upgrade.md)。

## 产物速查表

| 文件 | 类别 | 一句话说明 |
|---|---|---|
| `wiki/sources/` 下的 Paper Card | 面向用户 | 可连续阅读的单篇论文完整分析 |
| `wiki/topics/` 下的 Topic | 面向用户 | 多篇论文的综合认识、分歧、开放问题和段落化研究空白；新页含自动流程不会改写的「研究者备注」区 |
| `wiki/meta/topic-state/` | 机器 | Topic 的稳定 ID、来源、annotation、叙述待刷新标记与重放状态，不需要手动编辑 |
| `wiki/meta/research.md` | 面向用户 | 当前开放问题与空白的仪表盘 |
| `wiki/meta/knowledge-tree.md` | 面向用户 | 人与 Agent 共用的导航树和渐进检索入口 |
| `wiki/index.md`、`wiki/log.md` | 面向用户 | 页面索引与处理日志 |
| `work/gap-mining-report.md` | 面向用户 | 研究空白报告，含待确认清单 |
| `work/gap-mining-notes.md` | 中间 | 挖掘 Agent 的笔记，不需要读 |
| `work/topic-refresh-plan.json` 及对应 report | 机器 | mining 归档答案后，批量刷新受影响 Topic 综合叙述的计划、审计与发布结果 |
| `work/<批次>/batch-manifest.json` | 机器 | 当前论文批次的系统身份清单，是 digest、link-plan 和发布阶段共同核对的唯一来源 |
| `work/<名称>/paper-card.md` | 中间或交付 | Wiki 模式下是待发布草稿；`card-only` 下是经过审计的最终交付 |
| `work/<名称>/paper-digest-finalize-report.json` | 机器 | 系统字段整理差异，便于检查脚本改了什么 |
| `work/<名称>/link-plan.json` | 机器 | 写回计划，由确定性脚本执行 |
| `work/` 下的各种 `*-report.json` | 机器 | 审计与发布结果记录，Agent 用它判断流程状态 |
| `work/upgrade/<run-id>/` | 检查与恢复 | Vault 检查、迁移演练、备份、提交与回滚报告 |

## 决策点总览

框架设计上把需要你判断的环节收敛在最小范围：

| 环节 | 需要你做什么 |
|---|---|
| 处理论文 | 开始前选择一次 `card-only` / `wiki-topic` / `wiki-full`；明确说出模式时无需再确认 |
| 挖掘研究空白 | 阅读报告并逐项确认待确认清单。确认后才会写回 Topic |
| 候选新 Topic | 挖掘出的跨组方向要建新 Topic 时，必须经你显式确认 |
| 迁移旧 Topic | 先检查并预览迁移目标；只有你确认后才在副本演练并提交，回滚也需显式确认 |
| 重新处理论文 | 内容未变化的论文默认跳过，由你主动要求时才重新生成 |

每次工作结束时，Agent 都会列出本次产生的文件、它们各自的含义，以及是否有需要你决策的事项。看到不认识的产物文件名时，回到这张速查表对照即可。
