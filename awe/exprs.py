"""Tiny safe condition evaluator for `when:` expressions.

Grammar:  steps.<id>.output[.<key>]  <op>  <literal>     op in ==, !=, >, >=, <, <=, in
Also supports bare `steps.<id>.output.<key>` (truthiness) and `not <expr>`.
No eval(): parsing is explicit, so workflow specs cannot execute arbitrary code.
"""
from __future__ import annotations

import re
from typing import Any

_OPS = ["==", "!=", ">=", "<=", ">", "<", " in "]


def _resolve(path: str, state: dict) -> Any:
    parts = path.strip().split(".")
    if parts[0] != "steps" or len(parts) < 3:
        raise ValueError(f"unsupported reference: {path}")
    step_id, field = parts[1], parts[2]
    if step_id not in state:
        raise KeyError(f"unknown step in condition: {step_id}")
    value: Any = state[step_id].get(field)
    for key in parts[3:]:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            value = getattr(value, key, None)
    return value


def _literal(tok: str) -> Any:
    tok = tok.strip()
    if tok in ("True", "true"):
        return True
    if tok in ("False", "false"):
        return False
    if tok in ("None", "null"):
        return None
    if re.fullmatch(r"-?\d+", tok):
        return int(tok)
    if re.fullmatch(r"-?\d+\.\d+", tok):
        return float(tok)
    if (tok.startswith("'") and tok.endswith("'")) or (tok.startswith('"') and tok.endswith('"')):
        return tok[1:-1]
    raise ValueError(f"unsupported literal: {tok}")


def evaluate(expr: str, state: dict) -> bool:
    expr = expr.strip()
    if expr.startswith("not "):
        return not evaluate(expr[4:], state)
    for op in _OPS:
        if op in expr:
            left, right = expr.split(op, 1)
            lv = _resolve(left, state)
            rv = _literal(right)
            op = op.strip()
            return {"==": lambda: lv == rv, "!=": lambda: lv != rv,
                    ">": lambda: lv > rv, ">=": lambda: lv >= rv,
                    "<": lambda: lv < rv, "<=": lambda: lv <= rv,
                    "in": lambda: lv in rv}[op]()
    return bool(_resolve(expr, state))
