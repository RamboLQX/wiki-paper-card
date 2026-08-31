# DeepSeek Harness Adapter

DeepSeek Harness (DSH) 运行宿主适配。DSH 会话通过 skill 目录发现本框架，通过
bash 工具执行确定性脚本，通过 subagent 工具承担 processor 与 linker 角色。
详细编排映射见 [dsh-mode.md](dsh-mode.md)。

## Install

用仓库根目录的 `scripts/install.sh` 一键安装：

```bash
/path/to/wiki-paper-card/scripts/install.sh --host dsh /path/to/vault
```

脚本会：补齐 Vault 目录、no-clobber 复制模板 Wiki 文件、把
`wiki-paper-card` 与 `wiki-shared` 链接到 `$VAULT/.dsh/skills/`、复制
`template/CLAUDE.md`（DSH 自动加载 Vault 根目录的 `CLAUDE.md` / `AGENTS.md`），
并把仓库根写入 `$VAULT/.dsh/WIKI_PAPER_CARD_ROOT` 指针文件。

随后可在 DSH 的会话环境中设置项目根目录（可选，未设置时会话自动读取
`$VAULT/.dsh/WIKI_PAPER_CARD_ROOT`）：

```bash
export WIKI_PAPER_CARD_ROOT=/path/to/wiki-paper-card
```

## Invoke

```text
Use wiki-paper-card to process raw/papers/example.pdf.
```

DSH 会话会从 `.dsh/skills/` 发现 `wiki-paper-card` skill 并按其工作流契约执行。
