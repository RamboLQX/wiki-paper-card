# DSH Mode

DeepSeek Harness (DSH) 宿主下的编排映射。DSH 会话在 Vault 目录中启动时，
`workflow-contract.md` 的各阶段按下表映射到 DSH 原生能力。所有确定性阶段
（prepare、finalize、audit、publish、workflow_status）仍然通过 bash 工具调用
`python3 <REPO_ROOT>/scripts/...`，不变。

## 环境确认

- DSH 自动发现 `<VAULT_ROOT>/.dsh/skills/` 与 `<VAULT_ROOT>/.agents/skills/` 下的
  skill 目录（`<name>/SKILL.md`），以及 Vault 根目录的 `CLAUDE.md` / `AGENTS.md`。
  安装由 `scripts/install.sh --host dsh` 完成，无需其他配置。
- `<REPO_ROOT>` 优先取 `WIKI_PAPER_CARD_ROOT` 环境变量，其次取 skill 所在仓库。
- 运行 Python 脚本统一加 `PYTHONDONTWRITEBYTECODE=1`，避免写入系统缓存。

## 阶段映射

| 契约阶段 | DSH 执行方式 |
|---|---|
| Phase 0 确定性准备 | bash 工具直接运行 prepare_paper.py、build_processor_pack.py、build_kb_context.py |
| Phase 1 Paper Cards | `subagent` 工具：每篇论文一个后台子代理，prompt 携带 processor-brief、输入路径与输出约束 |
| Phase 1 完成检查 | bash 运行 `workflow_status.py`；子代理返回/唤醒后只看文件系统状态与退出码，通知信息不是完成证明 |
| Phase 1 修正循环 | `send_message` 向同一子代理发送精确错误项（最多 3 次尝试，之后该篇转串行） |
| Phase 2 确定性 finalize | bash 工具运行 finalize_paper_card.py 与 audit_paper_digest.py |
| Phase 3 批量 link | `subagent` 工具：每批一个 linker 子代理 |
| Phase 4 链接计划审计 | bash 工具运行 audit_link_plan.py |
| Phase 5 发布 | bash 工具运行 publish_wiki.py；禁止用子代理执行 wiki 写入 |

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
- Phase B（写回，仅在用户确认后）：主会话运行 audit_link_plan.py 与
  publish_wiki.py 两个确定性脚本；miner 只写 link-plan 与 work/ 文件，禁止
  子代理执行 wiki 写入。

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
