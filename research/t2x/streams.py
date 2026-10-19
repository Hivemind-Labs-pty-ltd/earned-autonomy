"""Turn T2-10x run files into engine streams (report/raw/t2-stream-10x-<cond>-<variant>.jsonl).

Same row schema and the same "organisation's day" order as t2.streams. Agent names: B "<arch>-10xrt-<variant>",
C "<arch>-10x-<variant>", D "<arch>-10xd-<variant>". D rows carry the version they ran under and that version's
gating result (meta.hidden_pass, meta.carried, meta.suite_n) so the trust engine can apply carry-over.

    python3 -m t2x.streams [--smoke]
"""
import argparse
import json
from pathlib import Path

from t2.streams import day_order, row

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "report/raw/t2-runs"
ARCHS = ("cs", "ws", "it", "ap", "of", "do")


def load(p):
    out = {}
    if p.exists():
        for l in p.read_text().splitlines():
            r = json.loads(l)
            if "error" not in r:
                out[r["task_id"]] = r
    return out


def write(name, rows):
    p = ROOT / f"report/raw/t2-stream-{name}.jsonl"
    p.write_text("\n".join(json.dumps(x) for x in rows) + "\n")
    print(f"{p.name}: {len(rows)} rows, err rate {sum(x['true_err'] for x in rows) / max(1, len(rows)):.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    tag = "-smoke" if args.smoke else ""
    for cond, label in (("B", "10xrt"), ("C", "10x")):
        for v in ("good", "sloppy"):
            runs = load(RUNS / f"10x-{cond}-{v}.jsonl")
            if runs:
                write(f"10x-{cond}-{v}{tag}", [row(runs[t], f"{runs[t]['arch']}-{label}-{v}", "v1")
                                               for t in day_order(list(runs))])
    for v in ("good", "sloppy"):
        runs, gate = {}, {}
        for arch in ARCHS:
            st_p = ROOT / f"report/raw/t2x-loop-{arch}-{v}{tag}.json"
            if not st_p.exists():
                continue
            st = json.loads(st_p.read_text())
            for ver, info in st["versions"].items():
                gate[(arch, ver)] = info
            for p in sorted(RUNS.glob(f"10x-D-{v}-{arch}{tag}-c*.jsonl")):
                runs.update(load(p))
        if runs:
            rows = []
            for t in day_order(list(runs)):
                r = runs[t]
                x = row(r, f"{r['arch']}-10xd-{v}", r.get("version", "v1"))
                info = gate.get((r["arch"], r.get("version", "v1")), {})
                x["meta"].update(hidden_pass=info.get("hidden_pass"), carried=info.get("carried"),
                                 suite_n=info.get("suite_n"), kb_reads=len(r.get("kb_reads") or []))
                rows.append(x)
            write(f"10x-D-{v}{tag}", rows)


if __name__ == "__main__":
    main()
