"""Re-grade stored T2 runs from their recorded writes + reply (grading is deterministic; no LLM calls).

Keeps the previous verdict as serious_strict / reasons_strict.
    python -m t2.regrade
"""
import json
from pathlib import Path

from t2.archetypes import grade
from t2.commit_grader import CANDIDATE, key, load_cache

ROOT = Path(__file__).resolve().parent.parent


def main():
    tasks = {json.loads(l)["task_id"]: json.loads(l) for l in (ROOT / "report/raw/t2-tasks.jsonl").read_text().splitlines()}
    commits = load_cache()
    changed = total = 0
    import sys
    pat = sys.argv[1] if len(sys.argv) > 1 else "*.jsonl"
    for p in sorted((ROOT / "report/raw/t2-runs").glob(pat)):
        out = []
        for l in p.read_text().splitlines():
            r = json.loads(l)
            if "error" not in r:
                if "serious_strict" not in r:
                    r["serious_strict"], r["reasons_strict"] = r["serious"], r["reasons"]
                rep = r["reply"] or ""
                cv = commits.get(key(rep), False) if CANDIDATE.search(rep) else False
                g = grade(tasks[r["task_id"]], r["writes"], rep, commit_verdict=cv)
                total += 1
                changed += g["serious"] != r["serious"]
                r.update(serious=g["serious"], reasons=g["reasons"], success=g["success"], injected=g["injected"])
            out.append(json.dumps(r))
        p.write_text("\n".join(out) + "\n")
    print(f"regraded {total} rows, {changed} verdicts changed")


if __name__ == "__main__":
    main()
