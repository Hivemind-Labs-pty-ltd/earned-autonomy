"""Import the real 10x platform code, offline.

Read-only imports from ~/Sites/10xAgent/10xAgent-Backend (override with TENX_BACKEND). No AWS: the platform
secret loader is stubbed the way the backend's unit tests do, and every LLM call (agent, rubric checks,
compliance judge) is routed through OpenRouter to deepseek/deepseek-v4-flash (PREREG-10x "Parity settings").

Run with the global python3 (it has the backend's dependencies); the memory-bench venv lacks PyJWT.
"""
import os
import sys
from pathlib import Path

BACKEND = Path(os.environ.get("TENX_BACKEND") or Path.home() / "Sites/10xAgent/10xAgent-Backend").resolve()
sys.path.insert(0, str(BACKEND / "lambda" / "SharedLayer" / "python"))
sys.path.insert(0, str(BACKEND / "scripts"))

os.environ["SECRET_ARN"] = ""
os.environ.setdefault("AWS_DEFAULT_REGION", "ap-southeast-2")
os.environ["LLM_DIRECT_PROVIDERS"] = ""          # deepseek through OpenRouter, like condition A
os.environ["LLM_FALLBACK"] = "off"
os.environ["OPENROUTER_PROVIDER_ORDER"] = ""     # no host pinning (A didn't pin either)
os.environ["NATIVE_CALLS_ENABLED"] = "all"

if not os.environ.get("OPENROUTER_API_KEY"):
    from dotenv import dotenv_values
    key = (dotenv_values(Path.home() / "Sites/hivemind-runtime/.env") or {}).get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not found in env or ~/Sites/hivemind-runtime/.env")
    os.environ["OPENROUTER_API_KEY"] = key

from AWS import SecretsManager  # noqa: E402

SecretsManager.load_secrets_from_arn = lambda *a, **k: {}

from hivemind_runtime import (AgentSnapshot, AssemblyPolicy, RetryPolicy,  # noqa: E402,F401
                              ToolCallReq, TranscriptMessage, Usage, run_turn)
from hivemind_runtime.registry import Tool, ToolRegistry  # noqa: E402,F401

from Models.AgentBundle import AgentBundle, ChecksConfig  # noqa: E402,F401
from Services import (agent_bundles, agent_definitions, judge_context, llm_gateway,  # noqa: E402,F401
                      message_checks, native_host, pipeline_judges)
from Services.model_rates import step_cost  # noqa: E402,F401
