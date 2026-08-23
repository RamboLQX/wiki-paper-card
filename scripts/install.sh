#!/usr/bin/env bash
# Install wiki-paper-card into an Obsidian Vault for one or more agent hosts.
#
# Usage:
#   install.sh [--host claude|dsh|both] [--repo-root PATH] VAULT
#
# The script is idempotent and never overwrites existing files or links:
#   - Vault directories are created only when missing.
#   - template/wiki files are copied with no-clobber semantics.
#   - Skills are symlinked into the host skill directory.
#   - CLAUDE.md is copied only when the target does not exist.
#
# Exit codes: 0 ok, 1 conflict or missing requirement, 2 usage error.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="both"
VAULT=""

usage() {
    cat <<'EOF'
Usage: install.sh [--host claude|dsh|both] [--repo-root PATH] VAULT

  --host        which agent host(s) to configure: claude, dsh, or both (default)
  --repo-root   wiki-paper-card repository path (default: parent of this script)
  VAULT         target Obsidian Vault directory
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --host)
            [[ $# -ge 2 ]] || { echo "ERROR: --host requires a value." >&2; exit 2; }
            HOST="$2"; shift 2
            ;;
        --repo-root)
            [[ $# -ge 2 ]] || { echo "ERROR: --repo-root requires a value." >&2; exit 2; }
            REPO_ROOT="$(cd "$2" && pwd)"; shift 2
            ;;
        -h|--help)
            usage; exit 0
            ;;
        -*)
            echo "ERROR: unknown option: $1" >&2; usage >&2; exit 2
            ;;
        *)
            [[ -z "$VAULT" ]] || { echo "ERROR: multiple VAULT arguments." >&2; exit 2; }
            VAULT="$1"; shift
            ;;
    esac
done

case "$HOST" in
    claude|dsh|both) ;;
    *) echo "ERROR: --host must be claude, dsh, or both." >&2; exit 2 ;;
esac

[[ -n "$VAULT" ]] || { echo "ERROR: VAULT argument is required." >&2; usage >&2; exit 2; }
[[ -d "$REPO_ROOT/skills" && -d "$REPO_ROOT/template" ]] || {
    echo "ERROR: $REPO_ROOT does not look like a wiki-paper-card repository (skills/ or template/ missing)." >&2
    exit 1
}

VAULT="$(cd "$VAULT" 2>/dev/null && pwd)" || {
    echo "ERROR: vault directory does not exist: $VAULT" >&2
    exit 1
}

CONFLICTS=0
report_conflict() {
    echo "CONFLICT: $1" >&2
    CONFLICTS=1
}

# 1. Vault directory skeleton.
mkdir -p "$VAULT/raw/papers"
mkdir -p "$VAULT/wiki/sources" "$VAULT/wiki/entities" \
         "$VAULT/wiki/topics" "$VAULT/wiki/meta" "$VAULT/work"

# 2. No-clobber copy of template wiki files.
copy_if_missing() {
    local src="$1" dst="$2"
    if [[ -e "$dst" ]]; then
        echo "keep  $dst"
        return
    fi
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    echo "copy  $dst"
}
copy_if_missing "$REPO_ROOT/template/wiki/index.md" "$VAULT/wiki/index.md"
copy_if_missing "$REPO_ROOT/template/wiki/log.md" "$VAULT/wiki/log.md"
copy_if_missing "$REPO_ROOT/template/wiki/meta/paper-processing-conventions.md" \
                "$VAULT/wiki/meta/paper-processing-conventions.md"

# 3. CLAUDE.md (DSH auto-loads CLAUDE.md/AGENTS.md from the vault root; Claude
#    Code reads CLAUDE.md too). Never overwrite an existing file.
copy_if_missing "$REPO_ROOT/template/CLAUDE.md" "$VAULT/CLAUDE.md"
if [[ -e "$VAULT/CLAUDE.md" ]] && ! cmp -s "$REPO_ROOT/template/CLAUDE.md" "$VAULT/CLAUDE.md"; then
    echo "NOTE: $VAULT/CLAUDE.md exists and differs from the template; merge missing sections manually."
fi

# 4. Symlink skills for the selected host(s). Existing links to the same target
#    are kept; anything else is reported as a conflict, never replaced.
link_skills() {
    local skills_dir="$1"
    mkdir -p "$skills_dir"
    for skill in wiki-paper-card wiki-shared; do
        local link="$skills_dir/$skill"
        local target="$REPO_ROOT/skills/$skill"
        if [[ -L "$link" ]]; then
            if [[ "$(readlink "$link")" == "$target" ]]; then
                echo "link  $link (unchanged)"
            else
                report_conflict "$link points to $(readlink "$link"), expected $target"
            fi
        elif [[ -e "$link" ]]; then
            report_conflict "$link exists and is not a symlink"
        else
            ln -s "$target" "$link"
            echo "link  $link -> $target"
        fi
    done
}

install_claude() {
    link_skills "$VAULT/.claude/skills"
    mkdir -p "$VAULT/.claude/agents"
    for agent in "$REPO_ROOT"/adapters/claude-code/agents/*.md; do
        [[ -e "$agent" ]] || continue
        local dst="$VAULT/.claude/agents/$(basename "$agent")"
        if [[ -e "$dst" ]]; then
            if cmp -s "$agent" "$dst"; then
                echo "keep  $dst (unchanged)"
            else
                report_conflict "$dst exists and differs from $agent"
            fi
        else
            cp "$agent" "$dst"
            echo "copy  $dst"
        fi
    done
}

install_dsh() {
    link_skills "$VAULT/.dsh/skills"
}

[[ "$HOST" == "claude" || "$HOST" == "both" ]] && install_claude
[[ "$HOST" == "dsh" || "$HOST" == "both" ]] && install_dsh

echo ""
echo "Install complete for host: $HOST"
echo "Set the repository root for agent sessions:"
echo "  export WIKI_PAPER_CARD_ROOT=$REPO_ROOT"
echo ""
echo "Next: open $VAULT in Obsidian and invoke:"
echo "  Use wiki-paper-card to process raw/papers/example.pdf."
echo "Verify with:"
echo "  PYTHONDONTWRITEBYTECODE=1 WIKI_PAPER_CARD_ROOT=$REPO_ROOT python3 $REPO_ROOT/scripts/smoke_test.py"

exit "$CONFLICTS"
