# Codex Mode

Codex 宿主下的编排映射。主会话使用 shell 运行 prepare、finalize、audit、publish 和 `workflow_status.py`；子 Agent 只负责生成各自独立的 `work/` 中间产物，禁止直接写入 `wiki/`。

## 处理范围

主会话在 Phase 0 前按 router 固定一次 `card-only`、`wiki-topic` 或
`wiki-full`。用户已经明确时直接执行；只有“处理/分析论文”而未说明是否需要
Topic 与研究空白时，询问一次，不逐篇询问。所有 processor prompt 都必须携带
该模式。`card-only` 不创建 manifest、digest 或 linker，Paper Card 审计通过后
结束且不写 `wiki/`；另外两种模式才进入 link/publish。

## 环境确认

- 从 Vault 根目录启动 Codex；项目 Skill 位于 `<VAULT_ROOT>/.agents/skills/`。
- `<REPO_ROOT>` 只按以下顺序解析：
  1. `WIKI_PAPER_CARD_ROOT` 环境变量；
  2. `<VAULT_ROOT>/.agents/WIKI_PAPER_CARD_ROOT` 指针文件。
- 解析后必须验证 `<REPO_ROOT>/vendor/nature-paper-card/SKILL.md` 可读；失败即停止，不猜测路径或尝试其他宿主指针。
- Skill 文档内的 `../../` 引用以 Skill 目录为基准换算成绝对路径。
- 运行 Python 脚本时设置 `PYTHONDONTWRITEBYTECODE=1`。
- 派发子 Agent 前确认当前 sandbox 允许写入目标 `work/<paper>/`。

## 阶段映射

| 契约阶段 | Codex 执行方式 |
|---|---|
| Phase 0 确定性准备 | 主会话运行 prepare、processor pack 和 KB context；仅 Wiki 模式运行 batch manifest |
| Phase 1 Paper Cards | 每篇论文创建一个 fresh processor 子 Agent，prompt 引用共享 `processor-brief.md` 与 schema |
| Phase 1 完成检查 | 子 Agent 返回后以所选 `--mode` 运行一次 `workflow_status.py`；完成通知不代替文件与退出码验证 |
| Phase 1 修正循环 | 向同一 processor 发送精确 audit 错误，最多三次；之后该篇转主会话串行处理 |
| Phase 2 确定性 finalize | 所有模式运行 card finalize；仅 Wiki 模式运行 digest identity finalize 与 manifest-aware digest audit |
| Phase 3 批量 link | 仅 Wiki 模式在全部卡片与 digest 通过后创建一个 fresh linker 子 Agent，并传入 `workflow_mode` |
| Phase 4 链接计划审计 | 主会话使用同一 batch manifest 运行 `audit_link_plan.py` |
| Phase 5 发布 | 仅主会话使用同一 batch manifest 运行 `publish_wiki.py` |

## 并发与恢复

- 每篇论文一个独立 processor，框架上限为同时三个；实际并发数不得超过当前会话可用子 Agent 槽位。
- 每个 processor 只写自己的 `work/<paper-name>/`；完成后释放槽位，不复用已完成 processor 处理其他论文。
- Wiki 模式下全批次只创建一个 linker，并等待所有 card、digest 和 audit 通过；`card-only` 不创建 linker。
- 无子 Agent 能力时串行执行，并向用户说明主会话上下文消耗会增加。

## 空白挖掘

- Phase A 创建一个 miner 子 Agent，只写 `work/gap-mining-report.md`。
- 用户确认候选后，使用当前 Codex 客户端的同 Agent follow-up 能力继续同一 miner，生成 `link-plan.json`。
- 无法恢复原 miner 时，主会话按报告中同名同构字段机械映射生成计划，不新建一个缺失 Phase A 上下文的 miner。
- audit 和 publish 仍只由主会话执行。
- mining publish 的 `narrative_refresh.required` 为 true 时，为报告中的全部 Topic 创建一个 fresh linker；不要按 Topic 分别创建，也不要重跑 processor。
- linker 生成 `purpose: "refresh"` 的 `work/topic-refresh-plan.json`；主会话再次执行 audit 和 publish。成功后提示清除，失败时保留待刷新状态并停止。
