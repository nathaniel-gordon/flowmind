"""Demo workflows + handlers: order fulfillment and a data pipeline with a QA gate."""
from __future__ import annotations

import random

from .engine import Step, Workflow

_FLAKY_STATE = {"charge_failures_left": 1}


# ---------------- handlers (order fulfillment) ----------------

def validate_order(ctx, order_total: float = 0.0, items: int = 0):
    if order_total <= 0 or items <= 0:
        raise ValueError("invalid order")
    return {"ok": True, "total": order_total, "items": items,
            "needs_review": order_total > 1000}


def reserve_inventory(ctx):
    items = ctx["outputs"]["validate"]["items"]
    return {"reserved": items, "warehouse": "W-1"}


def charge_payment(ctx):
    """Fails on the first attempt (simulated PSP timeout) to demonstrate retries."""
    if _FLAKY_STATE["charge_failures_left"] > 0:
        _FLAKY_STATE["charge_failures_left"] -= 1
        raise TimeoutError("payment provider timeout")
    total = ctx["outputs"]["validate"]["total"]
    return {"charged": total, "txn": f"TX{random.randint(10000, 99999)}"}


def ship_order(ctx):
    return {"tracking": f"TRK{random.randint(100000, 999999)}", "carrier": "FastShip"}


def notify_customer(ctx):
    trk = ctx["outputs"]["ship"]["tracking"]
    return {"sent": True, "message": f"Your order shipped: {trk}"}


ORDER_HANDLERS = {"validate_order": validate_order, "reserve_inventory": reserve_inventory,
                  "charge_payment": charge_payment, "ship_order": ship_order,
                  "notify_customer": notify_customer}


def order_workflow(order_total: float = 1450.0, items: int = 3) -> Workflow:
    return Workflow("order-fulfillment", [
        Step("validate", run="validate_order",
             params={"order_total": order_total, "items": items}),
        Step("reserve", run="reserve_inventory", needs=["validate"]),
        Step("charge", run="charge_payment", needs=["validate"], retries=2),
        Step("fraud_review", kind="approval", needs=["charge"],
             when="steps.validate.output.needs_review == True"),
        Step("ship", run="ship_order", needs=["reserve", "charge", "fraud_review"]),
        Step("notify", run="notify_customer", needs=["ship"]),
    ])


# ---------------- handlers (data pipeline) ----------------

def extract(ctx, rows: int = 1000, bad_pct: float = 0.04):
    return {"rows": rows, "bad_rows": int(rows * bad_pct)}


def profile(ctx):
    e = ctx["outputs"]["extract"]
    bad_pct = e["bad_rows"] / e["rows"] * 100
    return {"bad_pct": round(bad_pct, 2), "quality_ok": bad_pct <= 5.0}


def quarantine(ctx):
    e = ctx["outputs"]["extract"]
    return {"quarantined": e["bad_rows"], "destination": "s3://quarantine/"}


def load(ctx):
    e = ctx["outputs"]["extract"]
    return {"loaded": e["rows"] - e["bad_rows"], "table": "analytics.orders"}


def report(ctx):
    loaded = (ctx["outputs"].get("load") or {}).get("loaded", 0)
    return {"report": f"pipeline finished, {loaded} rows loaded"}


PIPELINE_HANDLERS = {"extract": extract, "profile": profile, "quarantine": quarantine,
                     "load": load, "report": report}


def pipeline_workflow(rows: int = 1000, bad_pct: float = 0.04) -> Workflow:
    return Workflow("data-pipeline", [
        Step("extract", run="extract", params={"rows": rows, "bad_pct": bad_pct}),
        Step("profile", run="profile", needs=["extract"]),
        Step("quarantine", run="quarantine", needs=["extract", "profile"],
             when="steps.profile.output.quality_ok == False"),
        Step("load", run="load", needs=["extract", "profile"],
             when="steps.profile.output.quality_ok == True"),
        Step("summarize", kind="agent", needs=["load", "quarantine"],
             run="summarize the pipeline outcome for the data team"),
        Step("report", run="report", needs=["load"]),
    ])


def offline_agent_handler(goal: str, ctx: dict):
    """Deterministic agent step: composes a summary from upstream outputs."""
    parts = [f"{k}: {v}" for k, v in ctx["outputs"].items() if v is not None]
    return {"summary": f"[agent] {goal} -> " + ("; ".join(parts) if parts else "nothing ran")}
