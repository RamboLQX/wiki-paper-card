# Vault Upgrade Contract

Use this workflow when the user asks to update, upgrade, migrate, or repair an
existing wiki-paper-card installation. Runtime installation and Wiki content
migration are separate operations. Updating runtime code never implies that a
legacy Topic was migrated.

## Required Inputs

Resolve and verify:

- `<REPO_ROOT>` using the normal host pointer rules;
- `<VAULT_ROOT>` as the existing Obsidian Vault;
- the installed host or hosts;
- whether the user wants runtime-only work, affected Topics, selected Topics,
  or an explicitly previewed whole-Vault migration.

Do not infer a whole-Vault migration from a generic update request.

## Phase 1: Read-Only Inspection

Run:

```bash
python3 "<REPO_ROOT>/scripts/upgrade_vault.py" inspect \
  --wiki-root "<VAULT_ROOT>" \
  --report "<VAULT_ROOT>/work/upgrade/<run-id>/inspection.json"
```

The report classifies every Topic as:

- `current`: valid schema 3.0 sidecar;
- `legacy-marker`: complete legacy schema 3.0 managed markers;
- `legacy-plain`: neither valid sidecar nor complete markers;
- `invalid-state`: a present sidecar is unreadable or invalid;
- `manual-review`: the Topic itself cannot be safely read or is a symlink.

Report the counts in user language. Schema names and sidecar paths belong in
the detailed report, not in the opening explanation.

Inspection does not alter `raw/` or `wiki/`. Writing the requested report under
`work/` is the only filesystem output.

## Phase 2: Runtime Upgrade

Runtime upgrade may update the repository checkout and rerun `install.sh` for
the already confirmed host and Vault. Before changing the checkout:

1. inspect the current branch, upstream, and working-tree status;
2. stop on local modifications or branch divergence; never reset or stash them;
3. use a fast-forward-only update to the user-confirmed release or branch;
4. rerun `install.sh --runtime-only` with the existing host and absolute Vault path;
5. run `scripts/smoke_test.py`;
6. report any existing `CLAUDE.md` / `AGENTS.md` difference for manual merge.

The installer writes `.wiki-paper-card/runtime-version` only after the selected
host layout has no hard conflicts. That marker describes runtime code only.
It does not authorize or claim Topic migration.

Runtime-only work must leave `raw/` and `wiki/` byte-identical.

## Phase 3: Migration Scope Confirmation

Offer these scopes after inspection:

1. no Topic migration;
2. only Topics required by the current paper/linker operation;
3. user-selected Topic paths;
4. all eligible legacy Topics shown in the inspection report.

The fourth option is allowed only after the user explicitly approves the
reported scope. `invalid-state` and `manual-review` targets never enter an
automatic batch.

## Phase 4: Semantic Migration Plan

One fresh linker creates a schema 3.0 `purpose: "migration"` plan. It reads the
exact legacy Topic bytes and every source page needed to rebuild the Topic.
Each action:

- is `update_topic`, never `create_topic`;
- carries `existing_page` and exact `base_topic_sha256`;
- lists every supporting source page in `papers`;
- supplies complete `index_summary`, narrative, evidence ledger, comparisons,
  open questions, and research gaps;
- preserves stable IDs and origins when legacy markers expose them;
- assigns new stable IDs only when a plain legacy page has no prior identity;
- carries forward source-grounded content and does not invent missing evidence.

Migration is not a lifecycle-edit operation. Plans must not contain removal or
annotation fields. Existing unknown sections and `## 研究者备注` remain outside
publisher ownership and are preserved. The known obsolete `## 关键发现` and
`## 争议与矛盾` sections are removed only after their evidence has been rebuilt
into the schema 3.0 narrative and ledger.

Write the plan and a human-readable preview under
`work/upgrade/<run-id>/`. The preview lists every target, source set, hash, and
content section that will be replaced. Do not apply before user approval.

## Phase 5: Staged Apply

After approval, run:

```bash
python3 "<REPO_ROOT>/scripts/upgrade_vault.py" apply \
  --wiki-root "<VAULT_ROOT>" \
  --plan "<VAULT_ROOT>/work/upgrade/<run-id>/migration-plan.json" \
  --run-dir "<VAULT_ROOT>/work/upgrade/<run-id>"
```

The wrapper audits the plan, copies the complete `wiki/` into a staging Vault,
publishes and audits there, rejects writes outside the selected Topics,
sidecars, index, log, knowledge tree, and research dashboard, then backs up and
commits only the staged differences. `raw/` and source pages are not migration
write targets.

An exact replay is a successful no-op. A stale page hash, missing source,
invalid plan, unexpected write path, or failed staged audit leaves the real
Wiki unchanged.

## Rollback

Run:

```bash
python3 "<REPO_ROOT>/scripts/upgrade_vault.py" rollback \
  --wiki-root "<VAULT_ROOT>" \
  --run-dir "<VAULT_ROOT>/work/upgrade/<run-id>"
```

Rollback restores every file from `backup-manifest.json` only while each file
still matches its recorded post-migration SHA-256. If a migrated file has been
edited since, rollback stops before changing anything. There is no force flag.

## Closing Summary

Report separately:

- runtime version and host-layout result;
- Topic inspection counts;
- selected and migrated Topic paths;
- audit results and backup manifest;
- deferred or blocked Topics;
- whether user action remains.
