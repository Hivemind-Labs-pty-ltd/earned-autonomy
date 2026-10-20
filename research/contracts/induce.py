"""Shadow contracts: induce per-task-type contracts from the agent's past actions (PREREG-contracts.md).

A contract = a shallow decision tree over structured task features -> decision class (which writes),
plus a provenance rule per write argument (where its value comes from in the world).
A clause = one tree leaf whose majority class covers >= 90% of its training rows and whose
write arguments all have a provenance rule matching >= 90% of training rows of that class.
"""
from __future__ import annotations

import re

from sklearn.tree import DecisionTreeClassifier

PURITY = 0.90
PROVENANCE_MIN = 0.90
TRAIN_SHARE = 0.30
AMOUNT_RE = re.compile(r"\$\s?([0-9][0-9,]*(?:\.[0-9]+)?)")


# ---- world helpers -----------------------------------------------------------------
def all_records(world):
    out = {}
    for rtype, recs in (world.get("records") or {}).items():
        for rid, rec in (recs or {}).items():
            out[rid] = (rtype, rec)
    return out


def ids_in_message(task):
    recs = all_records(task["world"])
    msg = task.get("message") or ""
    hits = [(msg.find(rid), rid) for rid in recs if rid and msg.find(rid) >= 0]
    return [rid for _, rid in sorted(hits)]


def primary_target(task):
    ids = ids_in_message(task)
    if not ids:
        return None, None
    recs = all_records(task["world"])
    return ids[0], recs[ids[0]][1]


# ---- features ----------------------------------------------------------------------
def raw_features(task):
    tid, rec = primary_target(task)
    f = {"has_target": 1 if tid else 0, "n_ids": len(ids_in_message(task))}
    for k, v in (rec or {}).items():
        if isinstance(v, bool):
            f[f"t.{k}"] = int(v)
        elif isinstance(v, (int, float)):
            f[f"t.{k}"] = float(v)
        elif v is None:
            f[f"t.{k}"] = -1.0
        elif isinstance(v, list):
            f[f"t.{k}.len"] = len(v)
        elif isinstance(v, str):
            f[f"t.{k}=" + v] = 1
    for k, v in task["world"].items():
        if k == "records":
            continue
        if isinstance(v, dict):
            f[f"w.{k}.nonempty"] = int(bool(v))
        elif isinstance(v, list):
            f[f"w.{k}.len"] = len(v)
    return f


def vectorise(rows, columns):
    return [[r.get(c, 0) for c in columns] for r in rows]


# ---- decision class + facts ---------------------------------------------------------
def decision_class(writes):
    return tuple(sorted(w[0] for w in writes)) if writes else ("none",)


def provenance_candidates(task, value):
    """Every rule that would produce `value` for this task, in PREREG order."""
    tid, rec = primary_target(task)
    out = []
    if tid is not None and str(value) == str(tid):
        out.append(("target_id",))
    if rec:
        for k, v in rec.items():
            if _eq(v, value):
                out.append(("target_field", k))
        # one hop: a record referenced by a target field value (logged in DECISIONS.md)
        recs = all_records(task["world"])
        for k, v in rec.items():
            if isinstance(v, str) and v in recs:
                for k2, v2 in recs[v][1].items():
                    if _eq(v2, value):
                        out.append(("linked_field", k, k2))
    for k, v in task["world"].items():
        if isinstance(v, list):
            for i, x in enumerate(v):
                if _eq(x, value):
                    out.append(("world_list", k, i))
    out.append(("const", _norm(value)))
    return out


def apply_rule(task, rule):
    tid, rec = primary_target(task)
    kind = rule[0]
    if kind == "target_id":
        return tid
    if kind == "target_field":
        return None if rec is None else rec.get(rule[1])
    if kind == "linked_field":
        if rec is None:
            return None
        recs = all_records(task["world"])
        ref = rec.get(rule[1])
        return recs[ref][1].get(rule[2]) if isinstance(ref, str) and ref in recs else None
    if kind == "world_list":
        lst = task["world"].get(rule[1]) or []
        return lst[rule[2]] if rule[2] < len(lst) else None
    if kind == "const":
        return rule[1]
    return None


def _norm(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    if isinstance(v, (list, dict)):
        return repr(v)
    return v


def _eq(a, b):
    return _norm(a) == _norm(b)


def args_equal(a, b):
    if set(a) != set(b):
        return False
    return all(_eq(a[k], b[k]) for k in a)


# ---- the contract ------------------------------------------------------------------
class Contract:
    """One task type's contract: a tree, its clauses (leaves), and argument provenance per class."""

    def __init__(self, train_tasks, train_writes):
        feats = [raw_features(t) for t in train_tasks]
        self.columns = sorted({c for f in feats for c in f})
        y = ["|".join(decision_class(w)) for w in train_writes]
        self.tree = DecisionTreeClassifier(max_depth=3, min_samples_leaf=5, random_state=0)
        self.tree.fit(vectorise(feats, self.columns), y)
        leaves = self.tree.apply(vectorise(feats, self.columns))
        by_leaf = {}
        for leaf, cls in zip(leaves, y):
            by_leaf.setdefault(int(leaf), []).append(cls)
        self.prov = self._provenance(train_tasks, train_writes)
        self.clauses = {}
        for leaf, classes in by_leaf.items():
            top = max(set(classes), key=classes.count)
            if classes.count(top) / len(classes) < PURITY:
                continue
            tools = [] if top == "none" else top.split("|")
            if all((tool, arg) in self.prov for tool in tools for arg in self._arg_names(tool)):
                self.clauses[leaf] = top

    def _arg_names(self, tool):
        return self.arg_names.get(tool, [])

    def _provenance(self, tasks, writes):
        counts, totals, self.arg_names = {}, {}, {}
        for task, ws in zip(tasks, writes):
            for tool, args in ws:
                self.arg_names.setdefault(tool, sorted(args))
                for arg, val in args.items():
                    totals[(tool, arg)] = totals.get((tool, arg), 0) + 1
                    for rule in set(provenance_candidates(task, val)):
                        counts.setdefault((tool, arg), {})
                        counts[(tool, arg)][rule] = counts[(tool, arg)].get(rule, 0) + 1
        out = {}
        for key, total in totals.items():
            ranked = sorted(counts.get(key, {}).items(), key=lambda kv: (-kv[1], _order(kv[0])))
            if ranked and ranked[0][1] / total >= PROVENANCE_MIN:
                out[key] = ranked[0][0]
        return out

    def predict(self, task):
        """Returns (clause_id or None, predicted writes or None)."""
        x = vectorise([raw_features(task)], self.columns)
        leaf = int(self.tree.apply(x)[0])
        cls = self.clauses.get(leaf)
        if cls is None:
            return None, None
        if cls == "none":
            return leaf, []
        writes = []
        for tool in cls.split("|"):
            args = {arg: apply_rule(task, self.prov[(tool, arg)]) for arg in self._arg_names(tool)}
            if any(v is None for v in args.values()):
                return leaf, None
            writes.append([tool, args])
        return leaf, writes


def _order(rule):
    return ["target_id", "target_field", "linked_field", "world_list", "const"].index(rule[0])


def writes_agree(pred, actual):
    if pred is None:
        return False
    if decision_class(pred) != decision_class(actual):
        return False
    a = sorted(actual, key=lambda w: w[0])
    p = sorted(pred, key=lambda w: w[0])
    return all(args_equal(pw[1], aw[1]) for pw, aw in zip(p, a))


def wording_ok(reply, task, pred):
    allowed = {float(x) for x in (task.get("allowed_amounts") or [])}
    for _, args in (pred or []):
        for v in args.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                allowed.add(float(v))
    for m in AMOUNT_RE.findall(reply or ""):
        try:
            v = float(m.replace(",", ""))
        except ValueError:
            continue
        if v not in allowed:
            return False
    return True


def contract_correct(task, pred):
    """The contract's own decision + facts against the seeded truth."""
    return pred is not None and writes_agree(pred, task.get("expected_writes") or [])
