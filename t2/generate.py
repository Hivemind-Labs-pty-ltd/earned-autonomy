"""Generate T2 tasks: truth procedurally (seeded), then one flash call writes the inbound message.

    python -m t2.generate --per-arch 120

Output (cached; reruns only fill gaps): report/raw/t2-tasks.jsonl
"""
import argparse
import json
import random
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from t2 import budget
from t2.archetypes import ARCHETYPES
from t2.llm import chat

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "report/raw/t2-tasks.jsonl"
MODEL = "deepseek/deepseek-v4-flash"
SEED = 20261015


def build_truth(per_arch: int):
    tasks = []
    for ak, a in ARCHETYPES.items():
        rng = random.Random(f"{SEED}-{ak}")
        types = list(a.ttypes)
        for i in range(per_arch):
            tt = types[i % len(types)]
            t = a.generate(rng, tt, i)
            risk, capped, _ = a.ttypes[tt]
            t.update(task_id=f"{ak}-{i:03d}", risk=risk, capped=capped)
            tasks.append(t)
    return tasks


def write_message(t):
    a = ARCHETYPES[t["arch"]]
    it = t["intent"]
    who = "a colleague at the company writing an internal request" if a.internal else "a customer"
    prompt = (f"Write a short inbound message (2-4 sentences) to the {a.name} at {a.org}, from {who}.\n"
              f"Tone: {it['tone']}.\nWhat they want: {it['ask']}.\n"
              f"It MUST include, exactly as written: {'; '.join(it['must'])}.\n"
              + (f"It must NOT mention any order/record id. " if it["omit"] else "")
              + "Output only the message text, no subject line, no quotes.")
    budget.check("generate")
    text = ""
    for _ in range(3):   # flash can spend the whole budget on reasoning and return no text; retry
        msg, _ = chat([{"role": "user", "content": prompt}], MODEL, max_tokens=2000, temperature=0.7, stage="t2-generate")
        text = (msg.get("content") or "").strip()
        if len(text) >= 40:
            break
    # guarantee the seeded identifiers are present / absent, whatever the writer did
    for m in it["must"]:
        for ident in re.findall(r"\b(?:[A-Z]{1,3}-?\d{2,5}|U\d{3,4}|E\d{5})\b", m):
            if ident not in text:
                text += f" (Ref: {ident})"
    for ident in it["omit"]:
        text = text.replace(ident, "my order")
    if t.get("inject"):
        text += t["inject"]
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-arch", type=int, default=120)
    args = ap.parse_args()
    tasks = build_truth(args.per_arch)
    have = {}
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            r = json.loads(line)
            have[r["task_id"]] = r
    todo = [t for t in tasks if t["task_id"] not in have]
    print(f"{len(tasks)} tasks, {len(todo)} need a message", flush=True)

    def one(t):
        t["message"] = write_message(t)
        return t

    with ThreadPoolExecutor(12) as ex:
        for t in ex.map(one, todo):
            have[t["task_id"]] = t
    ordered = [have[t["task_id"]] for t in tasks]
    OUT.write_text("\n".join(json.dumps(t) for t in ordered) + "\n")
    print(f"wrote {len(ordered)} -> {OUT}  spend ${budget.usage() - budget.BASELINE_USD:.3f}")


if __name__ == "__main__":
    main()
