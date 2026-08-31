#!/usr/bin/env bash
# Install wiki-paper-card into an Obsidian Vault for one or more agent hosts.
#
# Usage:
#   install.sh [--host claude|dsh|both|codex|all] [--repo-root PATH] VAULT
#
# The script is idempotent and never overwrites existing files or links:
#   - Vault directories are created only when missing.
#   - template/wiki files are copied with no-clobber semantics.
#   - Skills are symlinked into the host skill directory.
#   - adapters/, vendor/, scripts/ are symlinked next to the host skills so the
#     skills' '../../' references (e.g. ../../adapters/dsh/dsh-mode.md) resolve.
#   - A WIKI_PAPER_CARD_ROOT pointer file is written into each host directory
#     (.claude/, .dsh/, or .agents/) with the absolute repository root, so agent sessions
#     can resolve <REPO_ROOT> deterministically without guessing.
#   - CLAUDE.md and AGENTS.md are copied only for selected hosts and only when
#     the target does not exist.
#
# Exit codes: 0 ok, 1 conflict or missing requirement, 2 usage error.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="both"
VAULT=""

usage() {
    cat <<'EOF'
Usage: install.sh [--host claude|dsh|both|codex|all] [--repo-root PATH] VAULT

  --host        which agent host(s) to configure: claude, dsh, both (default), codex, or all
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
    claude|dsh|both|codex|all) ;;
    *) echo "ERROR: --host must be claude, dsh, both, codex, or all." >&2; exit 2 ;;
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
mkdir -p "$VAULT/wiki/sources" \
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

# 3. Host entry files. Claude Code and DSH use CLAUDE.md; Codex uses AGENTS.md.
#    The templates intentionally carry the same host-neutral Vault rules so an
#    all-host install cannot expose DSH to conflicting instructions.
install_entry_file() {
    local name="$1"
    local template="$REPO_ROOT/template/$name"
    local target="$VAULT/$name"
    copy_if_missing "$template" "$target"
    if [[ -e "$target" ]] && ! cmp -s "$template" "$target"; then
        echo "NOTE: $target exists and differs from the template; merge missing sections manually."
    fi
}

[[ "$HOST" == "claude" || "$HOST" == "dsh" || "$HOST" == "both" || "$HOST" == "all" ]] && \
    install_entry_file "CLAUDE.md"
[[ "$HOST" == "codex" || "$HOST" == "all" ]] && install_entry_file "AGENTS.md"

if [[ "$HOST" == "all" ]] && ! cmp -s "$VAULT/CLAUDE.md" "$VAULT/AGENTS.md"; then
    echo "WARNING: $VAULT/CLAUDE.md and $VAULT/AGENTS.md differ; DSH may load both. Merge them so the Vault rules are consistent." >&2
fi

# 4. Symlink skills for the selected host(s). Existing links to the same target
#    are kept; anything else is reported as a conflict, never replaced.
link_skills() {
    local skills_dir="$1"
    mkdir -p "$skills_dir"
    for skill in wiki-paper-card wiki-shared wiki-gap-mining; do
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

# 5. Symlink the resource directories the skills reach via '../../' into the
#    host directory (e.g. .dsh/, .claude/). The skill files reference
#    ../../adapters, ../../vendor and ../../scripts from inside the skill
#    directory; DSH resolves such references lexically against the skill base
#    directory, so those siblings must exist next to the host skills.
link_host_resources() {
    local host_dir="$1"
    mkdir -p "$host_dir"
    for name in adapters vendor scripts; do
        local link="$host_dir/$name"
        local target="$REPO_ROOT/$name"
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

# Write the repository root pointer into the host directory. Agent sessions
# read this file when WIKI_PAPER_CARD_ROOT is not set in the environment, so
# <REPO_ROOT> resolution never depends on model inference of the skill
# symlink target. The value is derived from --repo-root, so a changed repo
# path updates the file (this is the one exception to no-overwrite).
write_repo_root_pointer() {
    local host_dir="$1"
    mkdir -p "$host_dir"
    local pointer="$host_dir/WIKI_PAPER_CARD_ROOT"
    if [[ -d "$pointer" ]]; then
        report_conflict "$pointer is a directory; expected a pointer file"
        return
    fi
    if [[ -e "$pointer" ]]; then
        if [[ "$(cat "$pointer")" == "$REPO_ROOT" ]]; then
            echo "keep  $pointer (unchanged)"
        else
            printf '%s\n' "$REPO_ROOT" > "$pointer"
            echo "update $pointer -> $REPO_ROOT"
        fi
    else
        printf '%s\n' "$REPO_ROOT" > "$pointer"
        echo "write $pointer -> $REPO_ROOT"
    fi
}

# Verify the skills' '../../' references resolve for this host. Lexically,
# <host_dir>/skills/<skill>/../../ equals <host_dir>/, so checking the sibling
# paths directly validates what the selected host will resolve at runtime. A failure means
# the install is incomplete and sessions would hit "cannot read ... not found".
# The WIKI_PAPER_CARD_ROOT pointer must also exist and point at a repo whose
# pinned upstream router is readable.
verify_host_resources() {
    local host_dir="$1"
    local host="$2"
    local missing=""
    for rel in \
        "vendor/nature-paper-card/SKILL.md" \
        "scripts/build_processor_pack.py"; do
        if [[ ! -r "$host_dir/$rel" ]]; then
            missing="$missing $rel"
        fi
    done
    local adapter_refs=()
    case "$host" in
        claude)
            adapter_refs=(
                "adapters/claude-code/agents/wiki-processor.md"
                "adapters/claude-code/agents/wiki-linker.md"
            )
            ;;
        dsh) adapter_refs=("adapters/dsh/dsh-mode.md") ;;
        codex) adapter_refs=("adapters/codex/codex-mode.md") ;;
    esac
    local rel
    for rel in "${adapter_refs[@]}"; do
        if [[ ! -r "$host_dir/$rel" ]]; then
            missing="$missing $rel"
        fi
    done
    local pointer="$host_dir/WIKI_PAPER_CARD_ROOT"
    if [[ ! -r "$pointer" ]]; then
        missing="$missing WIKI_PAPER_CARD_ROOT"
    else
        local pointer_root
        pointer_root="$(cat "$pointer")"
        if [[ -z "$pointer_root" || ! -r "$pointer_root/vendor/nature-paper-card/SKILL.md" ]]; then
            echo "ERROR: $pointer 指向的仓库缺少 vendor/nature-paper-card/SKILL.md（$pointer_root）；请确认 WIKI_PAPER_CARD_ROOT 指向 wiki-paper-card 仓库根目录。" >&2
            CONFLICTS=1
        fi
    fi
    if [[ -n "$missing" ]]; then
        echo "ERROR: $host_dir: skill 的 ../../ 资源引用无法解析（缺少:${missing}）；请确认 adapters/vendor/scripts 链接与 WIKI_PAPER_CARD_ROOT 指针正确。" >&2
        CONFLICTS=1
    else
        echo "ok    $host_dir: $host 宿主的 skill ../../ 资源引用与 WIKI_PAPER_CARD_ROOT 指针可解析"
    fi
}

install_claude() {
    link_skills "$VAULT/.claude/skills"
    link_host_resources "$VAULT/.claude"
    write_repo_root_pointer "$VAULT/.claude"
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
    verify_host_resources "$VAULT/.claude" "claude"
}

install_dsh() {
    link_skills "$VAULT/.dsh/skills"
    link_host_resources "$VAULT/.dsh"
    write_repo_root_pointer "$VAULT/.dsh"
    verify_host_resources "$VAULT/.dsh" "dsh"
}

install_codex() {
    link_skills "$VAULT/.agents/skills"
    link_host_resources "$VAULT/.agents"
    write_repo_root_pointer "$VAULT/.agents"
    verify_host_resources "$VAULT/.agents" "codex"
}

[[ "$HOST" == "claude" || "$HOST" == "both" || "$HOST" == "all" ]] && install_claude
[[ "$HOST" == "dsh" || "$HOST" == "both" || "$HOST" == "all" ]] && install_dsh
[[ "$HOST" == "codex" || "$HOST" == "all" ]] && install_codex

echo ""
echo "Install complete for host: $HOST"
echo "Repository root pointer(s) written for the selected host(s):"
[[ "$HOST" == "claude" || "$HOST" == "both" || "$HOST" == "all" ]] && \
    echo "  $VAULT/.claude/WIKI_PAPER_CARD_ROOT = $REPO_ROOT"
[[ "$HOST" == "dsh" || "$HOST" == "both" || "$HOST" == "all" ]] && \
    echo "  $VAULT/.dsh/WIKI_PAPER_CARD_ROOT = $REPO_ROOT"
[[ "$HOST" == "codex" || "$HOST" == "all" ]] && \
    echo "  $VAULT/.agents/WIKI_PAPER_CARD_ROOT = $REPO_ROOT"
echo "Optional: export WIKI_PAPER_CARD_ROOT=$REPO_ROOT"
echo ""
echo "Next: open $VAULT in Obsidian and invoke:"
echo "  Use wiki-paper-card to process raw/papers/example.pdf."
echo "Verify with:"
echo "  PYTHONDONTWRITEBYTECODE=1 WIKI_PAPER_CARD_ROOT=$REPO_ROOT python3 $REPO_ROOT/scripts/smoke_test.py"

exit "$CONFLICTS"
