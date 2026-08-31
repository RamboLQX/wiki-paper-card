# Codex Adapter

Codex 运行宿主适配。Codex 从 Vault 的 `.agents/skills/` 发现本框架，由主会话运行确定性脚本，用子 Agent 承担 processor、linker 与 miner 角色。详细映射见 [codex-mode.md](codex-mode.md)。

## 安装

在仓库根目录使用安装脚本：

```bash
./scripts/install.sh --host codex /absolute/path/to/vault
```

脚本会使用 no-clobber 语义安装 Vault 模板，链接三个 Skill 与共享资源，写入 `.agents/WIKI_PAPER_CARD_ROOT`，并在 Vault 根目录安装 `AGENTS.md`。现有不同内容的 `AGENTS.md` 不会被覆盖；按安装提示人工合并缺失规则。

## 调用

从 Vault 根目录启动 Codex 任务，然后请求：

```text
Use wiki-paper-card to process raw/papers/example.pdf.
```

Codex 应从 `.agents/skills/` 发现 `wiki-paper-card`，并按 `codex-mode.md` 映射执行。
