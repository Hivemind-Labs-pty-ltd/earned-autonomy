"""v1 engine: the v0 engine plus the revisions pre-registered in PREREG-v1.md.

- carry-over: evidence kept across a version that passes its hidden tests (`version_pass`)
- one-level incident demotion is just PolicyConfig(hard_demotion=False)
- pooled trust: per-type bound with an agent-level Beta prior (k_eff = min(k, n_agent))
- eps by risk: per-key epsilon from the action's risk (T1 task type name, T2 meta.risk)

engine.py is untouched so v0 stays reproducible.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from gym.engine import Action, Engine, PolicyConfig, TrustState, wilson_lower, wilson_upper

RISKS = {"low", "med", "high", "capped"}
EPS_BY_RISK = {"low": 0.10, "med": 0.05, "high": 0.03, "capped": 0.0}


@dataclass
class PolicyConfigV1(PolicyConfig):
    pooled_k: int = 0                         # 0 = off
    eps_by_risk: dict | None = None           # None = flat cfg.eps
    version_pass: dict = field(default_factory=dict)   # (agent, version) -> bool; True keeps evidence


def risk_of(a: Action) -> str | None:
    r = (a.meta or {}).get("risk")
    if r in RISKS:
        return r
    return a.task_type if a.task_type in RISKS else None


class EngineV1(Engine):
    def __init__(self, cfg: PolicyConfigV1, **kw):
        super().__init__(cfg, **kw)
        self.key_eps: dict = {}
        self.agent_obs: dict = {}            # agent -> [n, err]

    def eps_for(self, k) -> float:
        return self.key_eps.get(k, self.cfg.eps)

    def st(self, a: Action) -> TrustState:
        cfg = self.cfg
        k = self.key(a)
        if k not in self.state:
            self.state[k] = TrustState(cfg.start_level)
            self.state[k].version = a.version
            if cfg.eps_by_risk is not None:
                r = risk_of(a)
                if r in cfg.eps_by_risk:
                    self.key_eps[k] = cfg.eps_by_risk[r]
        s = self.state[k]
        if s.version != a.version:
            keep = cfg.version_pass.get((a.agent, a.version), False)
            w = 1.0 if keep else cfg.version_w
            s.n *= w
            s.err *= w
            s.version = a.version
            if s.level >= 2 and self.upper(k, s) > self.eps_for(k):
                self._set_level(k, s, 1, "version_change")
        return s

    def upper(self, k, s: TrustState) -> float:
        cfg = self.cfg
        if cfg.pooled_k and cfg.granularity == "type":
            n_a, e_a = self.agent_obs.get(k[0], (0.0, 0.0))
            k_eff = min(cfg.pooled_k, n_a)
            p = e_a / n_a if n_a else 0.0
            return wilson_upper(s.err + k_eff * p, s.n + k_eff)
        return wilson_upper(s.err, s.n)

    def observe(self, k, s: TrustState, err: bool):
        ag = self.agent_obs.setdefault(k[0], [0.0, 0.0])
        ag[0] += 1
        ag[1] += err
        s.n += 1
        s.err += err
        s.since_change += 1
        s.recent.append(err)
        eps = self.eps_for(k)
        if s.level >= 2 and len(s.recent) >= 10:
            if wilson_lower(sum(s.recent), len(s.recent)) > eps:
                self._set_level(k, s, s.level - 1, "rolling_bound")
                return
        if eps > 0 and s.level < 3 and s.since_change >= self.cfg.n_min and self.upper(k, s) <= eps:
            self._set_level(k, s, s.level + 1, "evidence")

    def incident(self, k):
        s = self.state.get(k)
        self.m["incidents"] += 1
        if s is None:
            return
        s.n += 1
        s.err += 1
        ag = self.agent_obs.setdefault(k[0], [0.0, 0.0])
        ag[0] += 1
        ag[1] += 1
        if s.level >= 2:
            self._set_level(k, s, 1 if self.cfg.hard_demotion else s.level - 1, "incident")

    def step(self, a: Action) -> str:
        mode = super().step(a)
        if mode == "auto" and self.ledger and self.ledger[-1]["key"] is not None:
            row = self.ledger[-1]
            row["eps"] = self.eps_for(row["key"])
            row["upper"] = round(self.upper(row["key"], self.state[row["key"]]), 4)
        return mode


def run_stream_v1(actions, cfg: PolicyConfigV1, seed=0, **kw) -> EngineV1:
    e = EngineV1(cfg, seed=seed, **kw)
    for a in actions:
        e.step(a)
    return e


def v1_config(**over) -> PolicyConfigV1:
    """The combined v1 policy (V6)."""
    base = dict(kind="D", hard_demotion=False, pooled_k=20, eps_by_risk=dict(EPS_BY_RISK))
    base.update(over)
    return PolicyConfigV1(**base)
