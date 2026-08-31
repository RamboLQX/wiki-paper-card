# 研究空白挖掘 v2 与知识排布优化方案（草案 v2，待审）

> 历史设计说明：本文已实施的 gap v2 字段仍有效，但 Topic 写回和文本片段去重方案已被 schema 3.0 取代。当前契约以 `skills/wiki-paper-card/references/link-plan-schema.md` 和 `skills/wiki-gap-mining/references/mining-brief.md` 为准：mining 按稳定 ID 维护开放项，不改写 Topic 叙事。
>
> 状态：已实施（2026-08-29，见 CHANGELOG 0.8.0）。已确认的决策：6 字段全保留、priority 用 高/中/低、Top 速览只在挖掘报告、category 单值、分类视图放知识树内。第 7 节遗留问题 1–4 中：`[待验证]` 标签已采用；候选 topic 用现有 `status: stub`；意图分流在 wiki 已有对应页面时询问；research.md 只排序不显示标记。第 8 节 merge_topic 扩展未实施（留待页面级整合需求出现）。
> 输入：上一版 v2 方案 + 同事的《wiki-gap-mining 调用方式问题记录》+ 项目负责人的理念要求。
> 语言：通俗中文，不用"证伪"这类术语。

## 0. 已确认的决策

1. gap 条目的 6 个新字段全部保留。
2. `priority` 用标签 **高 / 中 / 低**，不用数字。
3. 「Top 空白速览」只放在挖掘报告里，不放进 `research.md`。

## 1. 设计原则（对齐项目理念）

这几条是本次所有改动的前提，也是判断"要不要加机制"的尺子：

- **重点是信息的排布与整理，不是防"水字数"。** 一条信息只要放在正确的区块、让研究者看得明白、讲清了该讲的细节，就是有价值的；放错区块或无实质内容的信息才需要被挡下。价值纪律的表述从"禁止凑字数"改为"这条信息回答研究者需要知道的什么，该放在哪个区块"。
- **保持精简，不越做越大。** 不新增 wiki 目录、不新增状态机、不新增候选库文件类型。候选分级全部落在现有 `work/` 报告里；"候选 topic"复用现有 `status: stub`（发布器新建 topic 页本来就默认 stub）；"待验证方向 vs 正式空白"用 v2 字段的齐备度表达，不加新状态。
- **维护导向。** 文献会不断更新，topic 页是长期维护对象。每次更新都是**编辑式合并**：先读目标小节现状 → 语义去重 → 改写合并或新增，而不是无脑追加。

## 2. Gap 条目 v2（6 字段）

沿用上一版方案，仅把 `priority` 改为标签：

| 字段 | 通俗含义 | 证据从库里哪来 | 必填 |
|---|---|---|---|
| `gap` | 空白是什么、从哪来 | 已有 | 必填 |
| `source_refs` | 追溯到哪些论文 | 已有 | 必填 |
| `direction` | 一句话：往哪个方向走能推进 | 已有 | 必填 |
| `continuity` | 后续论文怎么承接 | 已有 | 必填 |
| `significance` | 为什么值得做：解决了会改变什么判断或共识 | topic「关键发现」共识/分歧 | 可选 |
| `evidence_boundary` | 现有方法卡在哪 | topic 对照表「边界」列 +「争议与不确定」 | 可选 |
| `experiment` | 怎么检验：先讲猜想，再讲用什么数据/基准/指标/对照 | source Section 16「候选假设」「验证方式」 | 可选 |
| `success_criterion` | 做到什么算成 | 从现有证据提炼 | 可选 |
| `risk` | 可能行不通的地方：哪些论文已暗示这条路难走 | Section 16「可能失败」+「争议与不确定」 | 可选 |
| `priority` | 高 / 中 / 低 + 一句理由 | 横向比较后提炼 | 可选 |

**新字段的第二重用途——成熟度信号（对应同事问题 P4）：**

- 只有 `gap` + `direction`、缺 `evidence_boundary`/`experiment` → **待验证方向**（研究构想，证据不足）。
- `evidence_boundary` + `experiment` 齐备 → **正式研究空白**（有边界有做法，可以拿去开题）。

字段齐备度就是知识状态的判据，不需要另加状态字段。渲染时"待验证方向"在主行前加 `[待验证]` 标签。

**渲染（topic 页「研究空白与候选方向」）**：主行摘要 + 缩进子条目，只有写了的字段才渲染；「已解决的研究空白」归档格式不变。

**报告**：加「Top 空白速览」区块（按 高/中/低 排，每条一行：gap 一句话 + 为什么值钱 + 怎么做）。

## 3. 同事 9 个问题的采纳判断与映射

| # | 同事的问题 | 我的判断 | 改在哪 |
|---|---|---|---|
| P1 | 论文处理与 gap mining 调用边界混淆 | 采纳，轻改 | `wiki-gap-mining/SKILL.md` 加"输入意图分流" |
| P2 | scope 在无领域子目录时退化为"未分类/全库" | 采纳，一半是用户侧组织问题 | SKILL.md 写明退化规则与提示；建议按领域建子目录 |
| P3 | create_topic 门槛过低（两篇提相似想法即建页） | 采纳，重点改 | mining-brief 收紧 + linker-brief 初始生成规则收紧 |
| P4 | 探索性候选与正式知识不分层 | 采纳，用排布规则解决，不加新区块 | 三个 brief 补"内容类型→区块"映射表 |
| P5 | open_questions 与 research_gaps 语义重复 | 采纳，加排他规则，不合并区块 | linker-brief / mining-brief 补第三条分类规则 |
| P6 | 确认只确认"写不写"，不确认"写到哪、什么身份" | 采纳，轻改 | mining-brief 报告加「待确认清单」结构化格式 |
| P7 | 报告与 link-plan 缺稳定中间层 | 采纳，轻改 | 报告候选字段与 link-plan 字段同名同构 |
| P8 | DSH 下 Phase B 执行者不清 | 采纳，轻改 | dsh-mode.md + SKILL.md 写死执行方式 |
| P9 | 追加式合并不适合探索性 mining | 采纳，改在 miner 纪律与 plan 最小化，不大改 publisher | mining-brief 写回限制 + 语义去重纪律 |

**明确不采纳的重机制方案**（与"不要越做越大"冲突）：独立候选库文件、新的知识状态机、多轮确认表单 UI。候选分级落在 `work/` 报告里，知识状态用现有字段表达。

## 4. 各问题的具体改法

### 4.1 输入意图分流（P1）与 scope 退化（P2）→ `wiki-gap-mining/SKILL.md`

- 用户提到 `raw/` 路径或"处理"字眼时，先查 wiki 是否已有对应 source 页：**没有 → 路由到 `wiki-paper-card`**；**有 → 明确问一句**"补处理新论文 / 只挖掘已有内容的空白 / 两者"。
- scope 是"第一级领域目录"。当 `wiki/sources/papers/` 下没有领域子目录时，scope 按"用户点名的页面集合"或整库处理，并在报告「范围与日期」里注明"当前按整库/未分类处理，建议按领域分子目录以启用按域挖掘"。

### 4.2 create_topic 收紧（P3）→ `mining-brief.md` + `linker-brief.md`

- **gap-mining 默认不新建正式 topic**：只允许 `update_topic` 已有页面；确有跨组新主题时，先在报告中列为「候选新 topic」，用户显式确认后才 `create_topic`，且新页保持 `status: stub`（发布器默认行为），语义定义为"候选主题，等待更多论文支撑"。
- **linker（初始生成环节）同步收紧**：`create_topic` 必须满足 knowledge-model 已有的"至少两篇论文共享同一问题/机制/证据空间"，并明确反例——"两篇各自提出相似的未来研究想法"不构成共享证据空间，不建页。同事记录的 ESG 候选 A（网络对象、结果变量、数据来源都不同，只共享"可能存在网络溢出"这一抽象层次）就是典型反例。
- **"想法相似"的处理决策树（整合优先，不轻易建页）**：
  1. 两篇共享同一问题/机制/证据空间 → **整合到一个 topic 页**，在页内用对照表比较，不各建一页；
  2. 只共享抽象层次的相似（对象/变量/数据不同）→ **不建页**，作为「待验证方向」写进最贴切的已有 topic 的空白小节，或只留在报告；
  3. 多个候选空白收敛到同一个缺失设定 → 在报告里**合并成一条**，带多个 `source_refs`，写回也只写一条；
  4. 两个已存在的 topic 页边界交叉、内容重叠 → 属于页面级整合，需要「全库整理」能力（见第 8 节可选扩展）。
- 候选 topic 页的初始内容从简：概述（summary）+ 研究空白与候选方向，不硬凑对照表与关键发现；后续 ingest 批次再充实并升级状态。

### 4.3 内容分层用"排布规则"解决（P4）→ 三个 brief 共用一张映射表

不新增区块，只规定每类内容进哪个已有区块：

| 内容类型 | 落点 |
|---|---|
| 论文直接支持的发现 | topic「关键发现」（共识/单篇） |
| 论文承认的局限 | topic 对照表「边界」列 /「争议与不确定」 |
| 跨论文综合判断 | topic「关键发现」（共识） |
| 候选研究空白（字段齐） | topic「研究空白与候选方向」 |
| 待验证方向（缺字段） | topic「研究空白与候选方向」，带 `[待验证]` 标签 |
| 研究设计备忘录（具体数据/识别策略/失败条件） | 只进 source 页 Section 16 或挖掘报告，**不进 topic 页、不进 research.md** |

这张表放进 `knowledge-model.md` 作为单一事实来源，linker-brief 与 mining-brief 引用它。

### 4.4 open_questions 与 research_gaps 排他（P5）→ `linker-brief.md` + `mining-brief.md`

在现有"两问分类法"（key_findings vs research_gaps）后补第三条规则：

- 带 `source_refs` + `direction` 的候选 → 只写 `research_gaps`。
- 面向读者的一句话问题、没有方向 → 才写 `open_questions`。
- **同一候选不双写**；两处都合适时写 `research_gaps`，`open_questions` 不重复。
- 区块不合并（合并要动 publisher 和存量页面，收益低于排他规则）。

### 4.5 结构化确认（P6）→ `mining-brief.md` 报告契约

报告末尾加「待确认清单」，每个候选一行，用户只需在行上答复：

```text
- 候选 A：采用？[是/否] 落点：[现有 topic X / 新建候选 topic / 仅留在报告]
  知识状态：[正式空白 / 待验证方向] 写入：[research_gaps]
```

用户逐项回复后，Phase B 严格按回复生成 link-plan；"仅留在报告"的候选不产生任何页面变更。

### 4.6 报告与 link-plan 同名同构（P7）→ `mining-brief.md`

报告「候选研究空白」条目的字段名与 link-plan 的 `research_gaps` 字段**完全一致**（v2 的 10 个字段），翻译是机械映射，不做二次扩写。miner 产出 link-plan 时禁止改写候选文本。

### 4.7 DSH 下 Phase B 执行者（P8）→ `dsh-mode.md` + `SKILL.md`

- Phase A：后台 miner 子代理只读挖掘，产出报告，结束。
- 用户逐项确认后：主 agent 用 `send_message` 唤醒**同一个 miner**，把「待确认清单」的答复发给它，由 miner 生成 link-plan（DSH 子代理支持续聊；Claude Code 下用 Task 续跑）。
- 主 agent 运行 `audit_link_plan.py` + `publish_wiki.py`；禁止子代理执行 wiki 写入。
- 若子代理不可用，主 agent 按同名同构规则机械生成 link-plan（P7 保证了这个退路可靠）。

### 4.8 写回最小化 + 语义去重（P9）→ `mining-brief.md`

- **mining 写回只允许三种动作**：向已有 topic 的 `research_gaps`/`open_questions` 增条目；把跨组已解决条目标记 `answered` 归档；经确认的候选 topic 建页（stub）。
- **禁止 mining 写回触碰** 概述、关键发现、争议与不确定、论文与方法对照（这些只由论文处理的 linker 维护）。
- **语义去重纪律**：miner 生成 link-plan 前必须读目标 topic 页的相关小节；发现语义近似的已有条目时，**改写合并已有条目**（更新 `update_topic` 携带合并后的条目）或标注"无新增"，而不是追加一条近重复。

## 5. 逐文件改动清单

| 文件 | 改动 |
|---|---|
| `skills/wiki-gap-mining/SKILL.md` | 输入意图分流；scope 退化规则；Phase B 执行者明确 |
| `skills/wiki-gap-mining/references/mining-brief.md` | 6 字段填写要求与成熟度定义；create_topic 收紧；候选分级 + 待确认清单；Top 速览；写回最小化三动作；open_questions/research_gaps 排他；语义去重纪律；报告与 link-plan 同名同构 |
| `skills/wiki-paper-card/references/linker-brief.md` | create_topic 成熟度规则（共享问题/机制/证据空间，含反例）；第三条分类规则（open_questions vs research_gaps 排他）；价值纪律改写为"排布导向"表述 |
| `skills/wiki-paper-card/references/link-plan-schema.md` | `research_gaps` 补 6 可选字段；`priority` 值域 高/中/低；说明"新字段可选、由 gap-miner 填写、linker 不强制" |
| `skills/wiki-shared/references/knowledge-model.md` | 「内容类型→区块」映射表（单一事实来源）；"待验证方向 vs 正式空白"的字段齐备度定义；编辑式合并纪律；stub=候选主题的语义说明 |
| `skills/wiki-shared/references/wiki-schema.md` | topic 页「研究空白与候选方向」的新渲染格式（主行 + 子条目 + `[待验证]` 标签） |
| `scripts/audit_link_plan.py` | 新字段轻校验（给了就查非空字符串，没给不报错）；`priority` 值域校验 高/中/低 |
| `scripts/publish_wiki.py` | `normalize_gaps` 携带新字段（现在直接丢弃）；`gap_bullet` 渲染子条目与 `[待验证]` 标签；`render_research_page` 按 高/中/低 排序 |
| `tests/test_audit_link_plan.py` | 新字段缺失不报错、空串 warning、priority 值域等用例 |
| `tests/test_publish_wiki.py` | 子条目渲染、无新字段时与现在逐字节一致、priority 排序、`[待验证]` 标签 |
| `adapters/dsh/dsh-mode.md` | 空白挖掘 Phase B：send_message 唤醒同一 miner 产出 link-plan |

改动不涉及 `vendor/`、`raw/`，不新增依赖，不新增 wiki 目录或文件类型。

## 6. 验证方式

1. 单元测试：`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`（重点看 audit 与 publish 两个文件的新用例）。
2. 回归验证：一条不带新字段的 gap 渲染结果与现在逐字节一致。
3. smoke：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/smoke_test.py`。
4. 真实最小例子：用现有 3 个 topic 页跑一次只读 Phase A，检查报告是否出现候选分级、待确认清单、Top 速览；不写回。
5. 同事记录中的反例回归：ESG 候选 A（网络溢出）按新规则不应成为正式 topic，最多列为「候选新 topic」。

## 7. 待你确认的点

1. `[待验证]` 标签用什么词更顺眼？（备选：`[待验证方向]` / `[构想]` / `[初步]`）
2. 候选 topic 用现有 `status: stub` 表示，还是用 `draft`？（发布器默认 stub，用 stub 改动最小；draft 需要给 create_topic 增加状态参数）
3. 意图分流里，用户给出 raw 路径且 wiki 已有对应页面时，是每次都问，还是默认"只挖掘已有内容"并在开场说明？
4. `research.md` 是否需要在每条 gap 后显示 高/中/低 标记（当前方案只做排序，不显示标记）？
5. 主题分类轴（第 9 节）是否纳入本次改动？若纳入：分类视图放 `knowledge-tree.md` 内（推荐，单入口）还是独立 meta 页面？
6. `category` 用单值（一个主分类）还是允许多值？推荐单值 + 留空兜底，保持集合小而稳定。

## 8. 全库整理的覆盖范围与缺口（可选扩展，待定）

用户要求"全库整理"时，要区分两个层次：

**已覆盖**：全库 scope（`scope=all`）已支持；link-plan 天然支持一次运行带多个 topic 动作；空白/开放问题层面的全库整理（补充条目、跨组 answered 归档、priority 排序、语义去重、逐项结构化确认）在本方案内。

**结构缺口（当前不覆盖）**：topic 页之间的**合并、拆分、归档、状态变更**无法通过 link-plan 表达——schema 只有 `create_topic` / `update_topic`（`audit_link_plan.py` 的 `ALLOWED_TOPIC_ACTIONS`），publisher 对 status 用 `setdefault`（永不覆盖），没有页面级 merge/archive 能力。今天要做"两个 topic 合并成一个"，只能手工编辑，违反"所有 wiki 写入由确定性 publisher 执行"的原则。

**最小扩展建议（仅当确有页面级整合需求时再做）**：

- link-plan 增加一个动作 `merge_topic`：把来源页的 sources、对照行、关键发现、争议、开放条目**去重后合并**进目标页；来源页不删除，标记 `status: archived` 并留一句指向新页的说明（符合"不自动删除页面"的退休纪律）。合并语义由 publisher 确定性实现 + 测试。
- `update_topic` 增加可选 `page_status` 字段：仅在显式给出时覆盖页面 status（现 `setdefault` 做不到），支撑 stub→evergreen 等状态演进。
- 整理流程复用两阶段模式：读 → 产出「整理清单」（合并/更新/归档/状态变更逐项列出）→ 用户逐项确认 → link-plan → audit → publish。这本质是 CLAUDE.md 路由规则 4 的可执行化（目前它只有一句话、没有对应 skill）。

不新增独立整理 skill、不新增候选库文件。是否纳入本次改动，由是否有"合并 topic"的实际需求决定。

## 9. 主题分类轴：topic 的分类维度（对应"模型优化 vs 评估框架"问题）

### 9.1 现状与缺口

当前框架只有一个分组轴：**论文来源领域**（`wiki/sources/papers/` 第一级目录）。`knowledge-tree.md` 按领域分（## 领域 → 论文/主题/开放问题/研究空白），topic 页在 `wiki/topics/` 下平铺，frontmatter 只有 `tags/sources/aliases/status`。**"这个 topic 属于模型优化还是评估框架"这类按研究主题的分类维度，目前没有任何承载位置**——只能体现在 topic 标题里，无法被确定性生成、无法检索、无法在整理时作为轴使用。

### 9.2 两个轴的关系（先讲清楚，避免混淆）

- **领域（domain）**：论文从哪来（raw 目录结构，机械、固定）。回答"涉及哪些来源论文"。
- **分类（category）**：topic 回答哪一类研究问题（如 模型优化 / 评估框架，语义、可整理）。回答"这个主题在研究图谱里属于哪一块"。

两轴正交：一个领域可以贡献多个分类的 topic；一个 topic 可以综合多个领域的论文（跨域 topic 已存在）；一个 topic 也可以暂时无分类（category 留空）。

### 9.3 最小机制（不新增文件、不新增目录、不迁移页面）

1. **schema**：topic frontmatter 增加可选 `category: ""`（字符串，默认空）。分类集合**小而稳定**，由用户持有；linker/miner 只从已有分类中选，提出新分类必须先经用户确认（防止分类爆炸）。
2. **动作**：`create_topic` / `update_topic` 增加可选 `category` 字段；publisher 仅在显式给出时写入 frontmatter（与编辑式合并纪律一致，不给不动）。
3. **确定性视图**：`knowledge-tree.md` 在现有"领域优先"部分之后，增加一个"按主题分类"部分（## 分类：模型优化 → 该分类下 topic 列表 + wikilink + 一句话摘要）。与领域部分共用同一份确定性收集，不引入新 meta 页面。分类为空或跨类的 topic 落在"未分类"分组。
4. **分类作为整理的轴**：全库整理时，整理清单每个 topic 增加一列"分类归属"（保持/改到 X/留空）；**两个 topic 内容相似但分类不同时，不合并**，各自保留并注明边界与交叉引用——分类是防止错误合并的护栏。

### 9.4 全库整理工作流（含分类维度，用户例子）

用户说"把全库按主题分类整理"时：

```text
Phase A（只读）：读全部 topic 页
  → 识别自然分类（如 模型优化 / 评估框架）与每个 topic 的归属
  → 识别分类内重叠（合并候选）与分类交叉的 topic
  → 产出「整理清单」：每个 topic 一行：
     分类归属（保持/改到 X/留空）+ 合并建议 + 状态变更 + 逐项待确认
Phase B（用户逐项确认后）：
  → link-plan（update_topic 带 category；页面级合并若采纳则用第 8 节的 merge_topic）
  → audit_link_plan.py → publish_wiki.py
  → knowledge-tree 自动重建，出现"按主题分类"视图
```

其中"识别自然分类"由 miner/整理代理提出、**用户确认后**才生效；分类集合一经确定保持稳定，后续论文处理（linker 建新 topic）沿用既有分类。
