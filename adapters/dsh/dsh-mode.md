# DSH Mode

DeepSeek Harness (DSH) 宿主下的编排映射。DSH 会话在 Vault 目录中启动时，
`workflow-contract.md` 的各阶段按下表映射到 DSH 原生能力。所有确定性阶段
（prepare、finalize、audit、publish、workflow_status）仍然通过 bash 工具调用
`python3 <REPO_ROOT>/scripts/...`，不变。

## 环境确认

- DSH 自动发现 `<VAULT_ROOT>/.dsh/skills/` 与 `<VAULT_ROOT>/.agents/skills/` 下的
  skill 目录（`<name>/SKILL.md`），以及 Vault 根目录的 `CLAUDE.md` / `AGENTS.md`。
  安装由 `scripts/install.sh --host dsh` 完成，无需其他配置。
- `<REPO_ROOT>` 按以下确定性顺序解析，禁止靠模型推断路径：
  1. `WIKI_PAPER_CARD_ROOT` 环境变量；
  2. `<VAULT_ROOT>/.dsh/WIKI_PAPER_CARD_ROOT` 指针文件（`install.sh` 写入，内容为
     仓库绝对路径，直接读取即可）；
  3. `bash` 执行 `readlink -f "<VAULT_ROOT>/.dsh/skills/wiki-paper-card"`，对结果
     连续取两次 `dirname` 得到仓库根目录（软链真实路径的 `skills/wiki-paper-card`
     之上两级）。
  解析后必须验证 `<REPO_ROOT>/vendor/nature-paper-card/SKILL.md` 可读；验证失败
  就停止并请用户设置 `WIKI_PAPER_CARD_ROOT` 或重新运行 install.sh，不得继续猜测
  其他路径。
- skill 文档内的 `../../` 相对引用一律以 skill 目录为基准换算成绝对路径后再读取：
  skill 目录即 `skill` 工具返回的 `resourceBase`（DSH 安装布局下形如
  `<VAULT_ROOT>/.dsh/skills/<name>/`）。例如 `../../vendor/nature-paper-card/SKILL.md`
  换算为 `<REPO_ROOT>/vendor/nature-paper-card/SKILL.md`。不要以会话工作目录为基准
  解析这些引用，也不要只上溯一级。
- 运行 Python 脚本统一加 `PYTHONDONTWRITEBYTECODE=1`，避免写入系统缓存。

## 阶段映射

| 契约阶段 | DSH 执行方式 |
|---|---|
| Phase 0 确定性准备 | bash 工具直接运行 prepare_paper.py、batch_manifest.py、build_processor_pack.py、build_kb_context.py |
| Phase 1 Paper Cards | `subagent` 工具：每篇论文一个后台子代理，prompt 携带 processor-brief、输入路径与输出约束 |
| Phase 1 完成检查 | bash 运行 `workflow_status.py`；子代理返回/唤醒后只看文件系统状态与退出码，通知信息不是完成证明 |
| Phase 1 修正循环 | `send_message` 向同一子代理发送精确错误项（最多 3 次尝试，之后该篇转串行） |
| Phase 2 确定性 finalize | bash 工具运行 finalize_paper_card.py、finalize_paper_digest.py 与 manifest-aware audit_paper_digest.py |
| Phase 3 批量 link | `subagent` 工具：每批一个 linker 子代理 |
| Phase 4 链接计划审计 | bash 工具使用同一 batch manifest 运行 audit_link_plan.py |
| Phase 5 发布 | bash 工具使用同一 batch manifest 运行 publish_wiki.py；禁止用子代理执行 wiki 写入 |

## 并发与批次

- 每篇论文一个独立子代理，**默认同时活跃 6 个，上限 8 个**。DSH 对子代理数量
  无硬性上限，此值用于控制 provider 限流风险与成本，与质量无关（质量由
  确定性审计门与"全部通过后才 link"的顺序门保证）。
- 单批建议 ≤ 15 篇（约束来自 linker 一次读取全部 digest 的上下文预算）。
- 超大批次（>15 篇）可用 DSH 的 `workflow` 工具做分阶段 fan-out（可到 12-16
  并发），但每个分组的审计与发布仍需走完整确定性门。

### 等待式恢复（不要轮询）

- 派发完所有 processor 后直接结束回合，等待子代理完成通知。DSH 会在每个
  后台子代理结束时自动通知主会话；**只在收到新通知时**运行一次
  `workflow_status.py` 对账，其余时间不做任何检查。
- 不为单批处理创建 goal 循环，不做定时重查，不按轮次"自动续跑"——那会产生
  反复的空检查。goal 只适合多小时无人值守任务；即使使用，每轮也只做一次
  对账，且以子代理通知为触发，而非按轮次间隔轮询。
- 不计算、不输出耗时预估或轮次预估。只报告 `workflow_status.py` 的确定性
  事实（complete / INCOMPLETE 与缺失文件），完成时间由系统自然呈现。

## 空白挖掘（wiki-gap-mining）

- Phase A（读 + 挖掘）：`subagent` 工具跑一个后台 miner 子代理，prompt 携带
  `references/mining-brief.md`、范围（域列表或 all）与输出路径。全库范围时
  miner 可在内部按域拆读并自行汇总，不返回论文正文。
- Phase B（写回，仅在用户确认后）：用户对报告「待确认清单」逐项答复后，
  主会话用 `send_message` 唤醒**同一个 miner**，把确认结果发回，由 miner
  生成 link-plan（miner 保留 Phase A 的全部上下文，不重读库；报告候选与
  link-plan 字段同名同构，翻译是机械映射）。若子代理已不可用，主 agent
  按同名同构规则生成 link-plan。
- 主会话运行 audit_link_plan.py 与 publish_wiki.py 两个确定性脚本；miner
  只写 link-plan 与 work/ 文件，禁止子代理执行 wiki 写入。
- mining publish 的 `narrative_refresh.required` 为 true 时，主会话启动一个
  fresh linker subagent，批量处理报告列出的全部 Topic 并生成
  `purpose: "refresh"` 的 `work/topic-refresh-plan.json`。不要按 Topic 分别
  启动 linker，也不要重跑 processor；refresh 的 audit/publish 仍由主会话执行。

## 与 Claude Code 宿主的差异

- DSH 不使用 `adapters/claude-code/agents/*.md` 子代理定义文件；processor 与
  linker 的职责描述直接取 `references/processor-brief.md` 与
  `references/linker-brief.md`，原样拼入子代理 prompt。
- DSH 子代理默认后台运行并通知主会话；`interrupt_agent` 可中断进行中的子代理，
  `list_agents` 可枚举存活子代理。
- 子代理可用 `subagent_fork` 继承主会话上下文（如复用已读契约），但论文全文
  仍不得进入主会话。
- 若 DSH 会话未提供子代理能力，回退到串行执行并明确告知用户上下文消耗会上升。

## 验证清单

安装完成后在 DSH 会话中依次确认：

1. skill 目录里出现 `wiki-paper-card`、`wiki-shared` 与 `wiki-gap-mining`；
2. `python3 <REPO_ROOT>/scripts/smoke_test.py` 通过；
3. 调用 `Use wiki-paper-card to process raw/papers/example.pdf.` 能进入 Phase 0
   并生成 source bundle 与 kb-context。
