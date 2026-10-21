"""Build spec/requirements.json and conformance/compliance-matrix.md from spec/requirements/*.md.

    python scripts/build_requirements.py           # regenerate both files
    python scripts/build_requirements.py --check   # also fail if the spec's Test fields and the tests' markers disagree

Every rule in spec/requirements/ is a `## EA-<stage>.<n> <title>` heading followed by `- **Field:** value` lines.
Tests declare the rules they cover with `@pytest.mark.covers("EA-x.y", ...)`.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = ROOT / "spec" / "requirements"
TEST_DIRS = [ROOT / "conformance", ROOT / "engine" / "tests"]
VERSION = "0.7"
TIERS = ("Core", "Standard", "Advanced")
FIELDS = ("Statement", "Condition", "Status", "Tier", "Stability", "Rationale", "Evidence", "Implementation", "Test", "Notes")
KEYWORDS = ("MUST NOT", "SHALL NOT", "SHOULD NOT", "NOT RECOMMENDED", "MUST", "REQUIRED", "SHALL", "SHOULD",
            "RECOMMENDED", "MAY", "OPTIONAL")
STRENGTH = {"MUST NOT": "MUST", "SHALL NOT": "MUST", "MUST": "MUST", "REQUIRED": "MUST", "SHALL": "MUST",
            "SHOULD NOT": "SHOULD", "NOT RECOMMENDED": "SHOULD", "SHOULD": "SHOULD", "RECOMMENDED": "SHOULD",
            "MAY": "MAY", "OPTIONAL": "MAY"}
HEADING = re.compile(r"^## (EA-\d+\.\d+) (.+)$")
FIELD = re.compile(r"^- \*\*(\w+):\*\*\s?(.*)$")
TEST_ID = re.compile(r"`([\w/.-]+\.py::\w+)`")


def parse_rules() -> list[dict]:
    rules = []
    for path in sorted(REQUIREMENTS.glob("*.md")):
        stage_title = path.read_text().splitlines()[0].lstrip("# ").strip()
        current, field = None, None
        for line in path.read_text().splitlines():
            heading = HEADING.match(line)
            if heading:
                current = {"id": heading.group(1), "title": heading.group(2), "stage": stage_title,
                           "file": str(path.relative_to(ROOT))}
                rules.append(current)
                field = None
                continue
            if current is None:
                continue
            match = FIELD.match(line)
            if match and match.group(1) in FIELDS:
                field = match.group(1)
                current[field.lower()] = match.group(2).strip()
            elif field and line.startswith("  ") and line.strip():
                current[field.lower()] = (current[field.lower()] + " " + line.strip()).strip()
            elif not line.strip():
                pass
            else:
                field = None
    for rule in rules:
        statement = rule.get("statement", "")
        found = [k for k in KEYWORDS if re.search(rf"\b{k}\b", statement)]
        rule["keywords"] = sorted({STRENGTH[k] for k in found}, key=["MUST", "SHOULD", "MAY"].index)
        rule["strength"] = rule["keywords"][0] if rule["keywords"] else None
        rule["spec_tests"] = TEST_ID.findall(rule.get("test", ""))
        rule["cite"] = f"v{VERSION}-{rule['id']}"
    return rules


def marked_tests() -> dict[str, list[str]]:
    """rule id -> test ids, from @pytest.mark.covers(...) decorators."""
    covers = defaultdict(list)
    for directory in TEST_DIRS:
        for path in sorted(directory.glob("test_*.py")):
            tree = ast.parse(path.read_text())
            for node in tree.body:
                if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
                    continue
                for decorator in node.decorator_list:
                    if (isinstance(decorator, ast.Call) and getattr(decorator.func, "attr", None) == "covers"):
                        for arg in decorator.args:
                            covers[arg.value].append(f"{path.relative_to(ROOT)}::{node.name}")
    return covers


def all_test_functions() -> set[str]:
    found = set()
    for directory in TEST_DIRS:
        for path in sorted(directory.glob("test_*.py")):
            for node in ast.parse(path.read_text()).body:
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    found.add(f"{path.relative_to(ROOT)}::{node.name}")
    return found


def build(check: bool) -> int:
    rules = parse_rules()
    covers = marked_tests()
    problems = []
    ids = [rule["id"] for rule in rules]
    if len(ids) != len(set(ids)):
        problems.append("duplicate rule ids")
    for rule in rules:
        for name in ("statement", "status", "tier", "stability", "test"):
            if not rule.get(name):
                problems.append(f"{rule['id']}: missing {name}")
        if rule.get("status") not in ("Tested", "Default", "Open"):
            problems.append(f"{rule['id']}: bad status {rule.get('status')}")
        if rule.get("tier") not in TIERS:
            problems.append(f"{rule['id']}: bad tier {rule.get('tier')}")
        if rule.get("stability") not in ("Development", "Stable", "Deprecated"):
            problems.append(f"{rule['id']}: bad stability {rule.get('stability')}")
        if not rule["strength"]:
            problems.append(f"{rule['id']}: statement has no RFC 2119 keyword")
        rule["tests"] = sorted(covers.get(rule["id"], []))
        if sorted(rule["spec_tests"]) != rule["tests"]:
            problems.append(f"{rule['id']}: spec Test field {sorted(rule['spec_tests'])} != markers {rule['tests']}")
    unknown = set(covers) - set(ids)
    if unknown:
        problems.append(f"markers name unknown rules: {sorted(unknown)}")
    existing = all_test_functions()
    for rule in rules:
        for test in rule["spec_tests"]:
            if test not in existing:
                problems.append(f"{rule['id']}: test {test} does not exist")

    output = [{key: rule.get(key) for key in ("id", "cite", "title", "stage", "file", "statement", "condition",
                                              "strength", "keywords", "status", "tier", "stability", "rationale",
                                              "evidence", "implementation", "tests", "notes")} for rule in rules]
    (ROOT / "spec" / "requirements.json").write_text(
        json.dumps({"specification": "Earned Autonomy", "version": VERSION, "status": "Public review draft",
                    "generated_by": "scripts/build_requirements.py", "rules": output}, indent=2, ensure_ascii=False) + "\n")
    (ROOT / "conformance" / "compliance-matrix.md").write_text(matrix(rules))
    for problem in problems:
        print("problem:", problem, file=sys.stderr)
    untested_must = [rule["id"] for rule in rules if rule["strength"] == "MUST" and not rule["tests"]]
    tiers = {tier: sum(rule.get("tier") == tier for rule in rules) for tier in TIERS}
    print(f"{len(rules)} rules ({', '.join(f'{tier} {count}' for tier, count in tiers.items())}); "
          f"MUST without tests: {', '.join(untested_must) or 'none'}")
    return 1 if (check and problems) else 0


def matrix(rules: list[dict]) -> str:
    counts = defaultdict(int)
    for rule in rules:
        counts[(rule["strength"], rule["status"])] += 1
    lines = ["# Compliance matrix", "",
             f"**Generated by `scripts/build_requirements.py` from [`spec/requirements/`](../spec/requirements/). "
             f"Don't edit by hand.** Specification v{VERSION}.", "",
             "For every rule: its strength, its evidence status, where the reference engine implements it, and the tests "
             "that check it. **⚠** marks a MUST rule with no test yet.", "",
             "## Summary", "", "| Strength | Tested | Default | Open | Total |", "|---|--:|--:|--:|--:|"]
    for strength in ("MUST", "SHOULD", "MAY"):
        row = [counts[(strength, status)] for status in ("Tested", "Default", "Open")]
        lines.append(f"| {strength} | {' | '.join(map(str, row))} | {sum(row)} |")
    total = [sum(counts[(s, status)] for s in ("MUST", "SHOULD", "MAY")) for status in ("Tested", "Default", "Open")]
    lines.append(f"| **All** | {' | '.join(map(str, total))} | {sum(total)} |")
    lines += ["", "| Tier | Tested | Default | Open | Total |", "|---|--:|--:|--:|--:|"]
    for tier in TIERS:
        row = [sum(1 for r in rules if r.get("tier") == tier and r["status"] == status) for status in ("Tested", "Default", "Open")]
        lines.append(f"| {tier} | {' | '.join(map(str, row))} | {sum(row)} |")
    must_untested = [r["id"] for r in rules if r["strength"] == "MUST" and not r["tests"]]
    lines += ["", f"MUST rules with no test yet ({len(must_untested)}): {', '.join(must_untested) or 'none'}.", ""]
    stage = None
    for rule in rules:
        if rule["stage"] != stage:
            stage = rule["stage"]
            lines += ["", f"## {stage}", "", "| Rule | Tier | Strength | Status | Implementation | Tests |", "|---|---|---|---|---|---|"]
        tests = "<br>".join(f"`{t.split('::')[1]}`" for t in rule["tests"]) or ("**⚠ none**" if rule["strength"] == "MUST" else "none")
        link = f"[{rule['id']}](../{rule['file']}#{rule['id'].lower().replace('.', '')}-{slug(rule['title'])})"
        lines.append(f"| {link} {rule['title']} | {rule.get('tier')} | {rule['strength']} | {rule['status']} | "
                     f"{rule.get('implementation') or ''} | {tests} |")
    return "\n".join(lines) + "\n"


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9 -]", "", text.lower()).strip().replace(" ", "-")


if __name__ == "__main__":
    sys.exit(build(check="--check" in sys.argv))
