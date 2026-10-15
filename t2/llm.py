"""Minimal OpenRouter chat client for T2 (pattern copied from hivemind-memory-bench/gates/openrouter.py).

Cost comes off the wire (`usage.include`), every call is appended to report/raw/t2-spend.jsonl.
Supports OpenAI-style `tools`.
"""
import json
import os
import threading
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "report/raw/t2-spend.jsonl"
URL = "https://openrouter.ai/api/v1/chat/completions"
_lock = threading.Lock()
_local = threading.local()
SPEND = {"usd": 0.0, "calls": 0}


class OutOfCredit(RuntimeError):
    pass


def api_key() -> str:
    if os.environ.get("OPENROUTER_API_KEY"):
        return os.environ["OPENROUTER_API_KEY"]
    from dotenv import dotenv_values
    for p in (ROOT / ".env", Path.home() / "Sites/hivemind-runtime/.env",
              Path.home() / "Sites/hivemind-memory-bench/.env"):
        if p.exists():
            k = (dotenv_values(p) or {}).get("OPENROUTER_API_KEY")
            if k:
                os.environ["OPENROUTER_API_KEY"] = k
                return k
    raise RuntimeError("OPENROUTER_API_KEY not found")


def _session():
    if not hasattr(_local, "s"):
        _local.s = requests.Session()
    return _local.s


def chat(messages, model, tools=None, max_tokens=1200, temperature=0, stage="t2"):
    """Returns (message dict, usage dict)."""
    body = {"model": model, "messages": messages, "temperature": temperature,
            "max_tokens": max_tokens, "usage": {"include": True}}
    if tools:
        body["tools"] = tools
    headers = {"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json",
               "X-Title": "hivemind-trust-gym"}
    delay, last = 2.0, None
    for attempt in range(6):
        try:
            r = _session().post(URL, headers=headers, json=body, timeout=180)
            if r.status_code == 402:
                raise OutOfCredit(r.text[:300])
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"HTTP {r.status_code}: {r.text[:200]}")
            r.raise_for_status()
            data = r.json()
            if "choices" not in data or not data["choices"]:
                raise requests.HTTPError(f"no choices: {json.dumps(data)[:200]}")
            break
        except OutOfCredit:
            raise
        except Exception as exc:  # noqa: BLE001
            last = str(exc)
            if attempt == 5:
                raise
            print(f"    retry {attempt + 1} in {delay:.0f}s: {last[:120]}", flush=True)
            time.sleep(delay)
            delay *= 2
    msg = data["choices"][0]["message"]
    u = data.get("usage") or {}
    usage = {"cost": float(u.get("cost") or 0.0), "in": int(u.get("prompt_tokens") or 0),
             "out": int(u.get("completion_tokens") or 0), "finish": data["choices"][0].get("finish_reason")}
    with _lock:
        SPEND["usd"] += usage["cost"]
        SPEND["calls"] += 1
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with open(LEDGER, "a") as f:
            f.write(json.dumps({"stage": stage, "model": model, "usd": round(usage["cost"], 6),
                                "in": usage["in"], "out": usage["out"], "t": time.time()}) + "\n")
    return msg, usage
