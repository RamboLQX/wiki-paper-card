# Agent 升级与 Topic 迁移说明

本文档供 Agent 处理已经安装并使用过的 `wiki-paper-card` Vault。升级分为两件互不捆绑的事：

1. 更新仓库、Skill、脚本和宿主适配；
2. 将旧 Topic 转换为当前页面和状态结构。

仅升级运行入口时，不得改写 `raw/` 或 `wiki/`。禁止隐式全库迁移，但允许用户查看预览后明确批准全部合格 Topic。

## 推荐给 Agent 的请求

```text
请升级 wiki-paper-card。
项目仓库：/absolute/path/to/wiki-paper-card
Obsidian Vault：/absolute/path/to/vault
运行宿主：claude / dsh / both / codex / all

先执行只读检查，区分运行入口升级和 Topic 内容迁移。
在我确认迁移范围前，不要修改 wiki/ 中的任何页面。
```

## 第一步：只读检查

```bash
python3 "$REPO_ROOT/scripts/upgrade_vault.py" inspect \
  --wiki-root "$VAULT_ROOT" \
  --report "$VAULT_ROOT/work/upgrade/$RUN_ID/inspection.json"
```

报告会给出当前运行版本、宿主链接和入口文件差异，并将 Topic 分成：当前格式、可利用旧 marker 迁移、需要重建迁移计划、状态损坏和需手工复核。

`inspect` 不改写 `raw/` 或 `wiki/`；如指定 `--report`，只在 `work/` 中写入检查报告。

## 第二步：升级运行入口

更新仓库前先检查 Git 工作树。存在本地修改、分支分叉或无法快进时应停止，不使用 reset 或 stash 规避冲突。

在已确认更新目标后可执行：

```bash
git -C "$REPO_ROOT" pull --ff-only
"$REPO_ROOT/scripts/install.sh" --repo-root "$REPO_ROOT" --host "$HOST" --runtime-only "$VAULT_ROOT"
PYTHONDONTWRITEBYTECODE=1 python3 "$REPO_ROOT/scripts/smoke_test.py"
```

安装器依然不覆盖已有 `CLAUDE.md` 或 `AGENTS.md`。如与新模板不同，Agent 应列出待合并段落，不擅自覆盖。`.wiki-paper-card/runtime-version` 只表示运行代码版本，不表示 Topic 已迁移。

## 第三步：选择 Topic 迁移范围

Agent 应提供三种用户选项：

- 暂不迁移，旧页继续保留；
- 仅迁移本次需要更新的 Topic；
- 先生成全部合格 Topic 的迁移预览，用户确认后执行。

损坏状态和需手工复核的页面不进入自动批次。

## 第四步：生成迁移计划

Agent/linker 必须读取每个旧 Topic 及其引用的 source pages，生成 schema 3.0、`purpose: "migration"` 的完整计划。每个 action 只能是 `update_topic`，并携带精确 `base_topic_sha256`、完整叙述、证据台账、对照表、开放问题和研究空白。

迁移前先把人读预览和 `migration-plan.json` 写入 `work/upgrade/<run-id>/`，等用户确认。

## 第五步：演练并执行

```bash
python3 "$REPO_ROOT/scripts/upgrade_vault.py" apply \
  --wiki-root "$VAULT_ROOT" \
  --plan "$VAULT_ROOT/work/upgrade/$RUN_ID/migration-plan.json" \
  --run-dir "$VAULT_ROOT/work/upgrade/$RUN_ID"
```

脚本先在完整 `wiki/` 副本中发布和审计，校验写入白名单后才备份并提交差异。过期哈希、缺失来源、审计错误或越界写入都不会触碰真实 Wiki。

## 回滚

```bash
python3 "$REPO_ROOT/scripts/upgrade_vault.py" rollback \
  --wiki-root "$VAULT_ROOT" \
  --run-dir "$VAULT_ROOT/work/upgrade/$RUN_ID"
```

只有当所有迁移文件仍与记录的迁移后 SHA-256 一致时才回滚。如用户之后编辑了任何相关页面，脚本会在零写入状态下拒绝回滚。

完整机器契约见 [`upgrade-contract.md`](../skills/wiki-paper-card/references/upgrade-contract.md)。
