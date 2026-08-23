#!/usr/bin/env python3
"""Post-publish Obsidian render smoke check (soft gate).

Opens every page written by the last publish in the running Obsidian app and,
through the official Obsidian CLI, verifies that Markdown actually rendered:
heading decorations exist, and no raw `[[...]]` wikilinks or `**...**` bold
markers remain in the rendered text.

Soft gate by default: when the Obsidian CLI is missing, the command-line
interface is disabled, or the app does not respond, the check reports
`skipped` and exits 0, so batch publishing never depends on the GUI. Pass
--strict to turn `fail` and `skipped` into a non-zero exit.

The check opens each page in a temporary tab and closes it afterwards. It
never writes vault content.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

CLI_CANDIDATES = (
    "obsidian",
    "/Applications/Obsidian.app/Contents/MacOS/obsidian-cli",
)

OPEN_JS_TEMPLATE = (
    "(async () => {{"
    " const f = app.vault.getAbstractFileByPath({path!r});"
    " if (!f) return JSON.stringify({{error: 'not in vault'}});"
    " const leaf = app.workspace.getLeaf('tab');"
    " await leaf.openFile(f);"
    " await new Promise(r => setTimeout(r, 400));"
    " return 'ok';"
    " }})()"
)

CHECK_JS = (
    "(async () => {"
    " const leaf = app.workspace.getMostRecentLeaf();"
    " const c = leaf.containerEl;"
    " const ed = leaf.view.editor;"
    " const sample = () => {"
    "  const cmLines = [...c.querySelectorAll('.cm-line')];"
    "  let headers = 0;"
    "  let text = '';"
    "  if (cmLines.length) {"
    "   headers = cmLines.filter(l => l.className.includes('HyperMD-header')).length;"
    "   text = cmLines.map(l => l.textContent).join('\\n');"
    "  } else {"
    "   const rv = c.querySelector('.markdown-reading-view');"
    "   text = rv ? rv.textContent : '';"
    "   headers = c.querySelectorAll('h1, h2, h3').length;"
    "  }"
    "  const rawLinks = (text.match(/\\[\\[/g) || []).length;"
    "  const rawBold = (text.match(/\\*\\*/g) || []).length;"
    "  return {headers: headers, rawLinks: rawLinks, rawBold: rawBold};"
    " };"
    " if (!ed) return JSON.stringify(sample());"
    " const top = sample();"
    " ed.scrollIntoView({from: {line: ed.lastLine(), ch: 0}, to: {line: ed.lastLine(), ch: 0}}, true);"
    " await new Promise(r => setTimeout(r, 500));"
    " const bottom = sample();"
    " return JSON.stringify({"
    "  headers: top.headers + bottom.headers,"
    "  rawLinks: top.rawLinks + bottom.rawLinks,"
    "  rawBold: top.rawBold + bottom.rawBold"
    " });"
    " })()"
)

CLOSE_JS = "(() => { app.workspace.getMostRecentLeaf().detach(); return 'ok'; })()"

PAGE_KINDS = {"source", "entity", "topic"}


def find_cli() -> str | None:
    if os.environ.get("WIKI_PAPER_CARD_SMOKE_DISABLE"):
        return None
    found = shutil.which("obsidian")
    if found:
        return found
    for candidate in CLI_CANDIDATES[1:]:
        if Path(candidate).is_file():
            return candidate
    return None


def read_publish_report(report_path: Path) -> tuple[list[str], str]:
    """Return (page_paths, status) from a publish-report.json."""
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read publish report: {exc}") from exc
    pages: list[str] = []
    for item in report.get("writes", []):
        if not isinstance(item, dict):
            continue
        if item.get("kind") not in PAGE_KINDS:
            continue
        path = str(item.get("path", ""))
        if path:
            pages.append(path)
    return pages, str(report.get("summary", {}).get("status", "unknown"))


class SmokeCheck:
    """Runs the CLI-backed checks; `run` is injectable for tests."""

    def __init__(self, cli: str | None, timeout: float = 30.0, vault: str | None = None) -> None:
        self.cli = cli
        self.timeout = timeout
        self.vault = vault

    def run(self, arguments: list[str]) -> tuple[int, str, str]:
        command = [self.cli] if self.cli else []
        if self.vault:
            command.append(f"vault={self.vault}")
        command.extend(arguments)
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except (OSError, subprocess.TimeoutExpired) as exc:
            return -1, "", str(exc)

    def eval(self, code: str) -> tuple[int, str]:
        returncode, stdout, stderr = self.run(["eval", f"code={code}"])
        if returncode != 0:
            return returncode, (stderr or stdout or "eval failed")
        marker = "=> "
        if stdout.startswith(marker):
            stdout = stdout[len(marker) :].strip()
        return 0, stdout

    def check_page(self, page_path: str) -> dict[str, Any]:
        open_code, open_result = self.eval(OPEN_JS_TEMPLATE.format(path=page_path))
        if open_code != 0:
            return {"page": page_path, "status": "unknown", "error": open_result[:200]}
        if "not in vault" in open_result:
            return {
                "page": page_path,
                "status": "fail",
                "problems": ["page not found in the active vault; check --vault"],
            }
        check_code, payload = self.eval(CHECK_JS)
        try:
            self.eval(CLOSE_JS)
        except Exception:  # pragma: no cover - defensive
            pass
        if check_code != 0:
            return {"page": page_path, "status": "unknown", "error": payload[:200]}
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return {"page": page_path, "status": "unknown", "error": payload[:200]}
        problems: list[str] = []
        if int(data.get("headers", 0)) <= 0:
            problems.append("no heading decorations rendered")
        if int(data.get("rawLinks", 0)) > 0:
            problems.append(f"{data['rawLinks']} raw [[ wikilinks not compiled")
        if int(data.get("rawBold", 0)) > 0:
            problems.append(f"{data['rawBold']} raw ** bold markers not compiled")
        status = "fail" if problems else "pass"
        return {
            "page": page_path,
            "status": status,
            "headers": data.get("headers"),
            "raw_links": data.get("rawLinks"),
            "raw_bold": data.get("rawBold"),
            "problems": problems,
        }


def cli_available(cli: str | None) -> tuple[bool, str]:
    if cli is None:
        return False, "obsidian CLI not found (install Obsidian 1.12+ and enable Command line interface)"
    try:
        result = subprocess.run(
            [cli, "help"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"obsidian CLI did not respond: {exc}"
    if result.returncode != 0:
        return False, (result.stderr or result.stdout or "obsidian CLI unavailable").strip()
    return True, ""


def run_check(report_path: Path, strict: bool, timeout: float, vault: str | None) -> dict[str, Any]:
    pages, publish_status = read_publish_report(report_path)
    if not pages:
        return {
            "schema_version": "1.0",
            "summary": {"status": "skipped", "reason": "publish report contains no page writes"},
            "pages": [],
        }
    cli = find_cli()
    available, reason = cli_available(cli)
    if not available:
        return {
            "schema_version": "1.0",
            "summary": {
                "status": "skipped",
                "reason": reason,
                "publish_status": publish_status,
                "strict": strict,
            },
            "pages": [],
        }
    check = SmokeCheck(cli, timeout=timeout, vault=vault)
    results = [check.check_page(page) for page in pages]
    failures = [item for item in results if item["status"] == "fail"]
    unknowns = [item for item in results if item["status"] == "unknown"]
    status = "pass"
    if failures or unknowns:
        status = "fail"
    return {
        "schema_version": "1.0",
        "summary": {
            "status": status,
            "pages": len(results),
            "passed": sum(item["status"] == "pass" for item in results),
            "failed": len(failures),
            "unknown": len(unknowns),
            "publish_status": publish_status,
            "strict": strict,
        },
        "pages": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Post-publish Obsidian render smoke check (soft gate by default)."
    )
    parser.add_argument("--report", type=Path, required=True, help="Path to publish-report.json.")
    parser.add_argument("--output", type=Path, help="Write the smoke report as JSON.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on fail or skipped.")
    parser.add_argument("--timeout", type=float, default=30.0, help="Per-command timeout in seconds.")
    parser.add_argument("--vault", help="Obsidian vault name; defaults to the active vault.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_path = args.report.expanduser().resolve()
    if not report_path.is_file():
        print("ERROR: --report must point to an existing publish report.", file=sys.stderr)
        return 2
    smoke = run_check(report_path, args.strict, args.timeout, args.vault)
    summary = smoke["summary"]
    print(f"Obsidian smoke status: {summary['status']}")
    if summary.get("reason"):
        print(f"  reason: {summary['reason']}")
    else:
        print(
            f"  pages={summary.get('pages', 0)}, passed={summary.get('passed', 0)}, "
            f"failed={summary.get('failed', 0)}, unknown={summary.get('unknown', 0)}"
        )
    for item in smoke.get("pages", []):
        if item["status"] == "pass":
            continue
        print(f"  {item['status'].upper():7} {item['page']}: {item.get('problems') or item.get('error')}")
    if args.output:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(smoke, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote smoke report: {output}")
    if args.strict and summary["status"] in {"fail", "skipped"}:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
