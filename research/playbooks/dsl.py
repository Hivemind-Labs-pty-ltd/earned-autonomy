"""The playbook language and its interpreter.

A playbook (JSON) is the approved procedure for one task type. Code does everything except two things the model
does: extract slot values from the inbound message, and write the reply from facts code supplies.

Playbook fields:
  task_type    "<arch>:<ttype>"
  rules        the written policy rules this playbook implements (cited by number in branches)
  slots        {name: {"type": "id"|"email"|"text"|"bool"|"number", "desc": "..."}}   extracted by the model
  lookups      ordered list; each binds an alias:
                 {"as": a, "collection": c, "by": "<slot or expression giving the id>"}      record by id
                 {"as": a, "collection": c, "match": {"field": f, "slot": s}, "only_if_missing": a2}
                     find records whose field equals the slot (case-insensitive); one → bind, many → outcome "ask",
                     none → outcome "ask". With only_if_missing, runs only when alias a2 is unbound.
                 {"as": a, "special": "free_slots" | "price_list" | "kb" | "deletion_request", "arg": "<expr>"}
  verify       [{"if": "<expr that must be TRUE for a problem>", "then": "ask"|"decline"|"escalate", "rule": n,
                 "outcome": "..."}]  checked in order after lookups
  branches     [{"if": "<expr>", "do": "write"|"inform"|"ask"|"decline"|"escalate", "write": tool, "args": {k: expr},
                 "rule": n, "outcome": "what happened, for the writer", "facts": {name: expr}, "require": [name]}]
                 first match wins; a playbook should end with an "if": "True" fallback
  message      {"facts": {name: expr}, "require": [name], "forbid": "..."}  defaults merged with the branch's

Expressions are a small, safe subset of Python: names (slots and aliases), attribute access on records
(missing → None), comparisons, and/or/not, `in`, `x if c else y`, constants, and lower(), len(), str(), float().
"""
from __future__ import annotations

import ast

SAFE_CALLS = {"lower": lambda x: str(x).lower() if x is not None else None, "len": lambda x: len(x or []),
              "str": str, "float": lambda x: float(x) if x not in (None, "") else None}


class Missing:
    """A value that isn't there: comparisons with it are false, attribute access on it stays Missing."""

    def __getattr__(self, _):
        return self

    def __eq__(self, other):
        return isinstance(other, Missing) or other is None

    def __bool__(self):
        return False

    def __repr__(self):
        return "None"

    __hash__ = object.__hash__


MISSING = Missing()


def _cmp(op, a, b):
    if isinstance(op, (ast.Is, ast.IsNot)):
        same = (a is b) or (isinstance(a, Missing) and b is None) or (a is None and isinstance(b, Missing))
        return same if isinstance(op, ast.Is) else not same
    if isinstance(op, ast.Eq):
        return a == b
    if isinstance(op, ast.NotEq):
        return not (a == b)
    if isinstance(op, (ast.In, ast.NotIn)):
        try:
            r = a in (b or [])
        except TypeError:
            r = False
        return r if isinstance(op, ast.In) else not r
    if a is None or b is None or isinstance(a, Missing) or isinstance(b, Missing):
        return False
    try:
        if isinstance(op, ast.Lt):
            return a < b
        if isinstance(op, ast.LtE):
            return a <= b
        if isinstance(op, ast.Gt):
            return a > b
        if isinstance(op, ast.GtE):
            return a >= b
    except TypeError:
        return False
    raise ValueError(f"operator {type(op).__name__} not allowed")


def evaluate(expr: str, env: dict):
    tree = ast.parse(str(expr), mode="eval")

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant):
            return n.value
        if isinstance(n, ast.Name):
            if n.id in ("True", "False", "None"):
                return {"True": True, "False": False, "None": None}[n.id]
            v = env.get(n.id, MISSING)
            return MISSING if v is None and n.id not in env else v
        if isinstance(n, ast.Attribute):
            base = ev(n.value)
            if isinstance(base, dict):
                return base.get(n.attr, MISSING) if base.get(n.attr) is not None else (None if n.attr in base else MISSING)
            return MISSING
        if isinstance(n, ast.Subscript):
            base, key = ev(n.value), ev(n.slice)
            if isinstance(base, dict):
                return base.get(key, MISSING)
            if isinstance(base, list) and isinstance(key, int) and -len(base) <= key < len(base):
                return base[key]
            return MISSING
        if isinstance(n, ast.BoolOp):
            vals = [ev(v) for v in n.values]
            return all(vals) if isinstance(n.op, ast.And) else any(vals)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
            return not ev(n.operand)
        if isinstance(n, ast.Compare):
            left = ev(n.left)
            for op, comp in zip(n.ops, n.comparators):
                right = ev(comp)
                if not _cmp(op, left, right):
                    return False
                left = right
            return True
        if isinstance(n, ast.IfExp):
            return ev(n.body) if ev(n.test) else ev(n.orelse)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in SAFE_CALLS and not n.keywords:
            return SAFE_CALLS[n.func.id](*[ev(a) for a in n.args])
        if isinstance(n, (ast.List, ast.Tuple)):
            return [ev(e) for e in n.elts]
        raise ValueError(f"expression not allowed: {ast.dump(n)[:80]}")

    v = ev(tree)
    return None if isinstance(v, Missing) else v
