"""FastAPI app: one CAB page + assessment/decision/outcome APIs."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from . import store as store_mod
from .config import settings
from .graph import run_to_interrupt
from .history import load_history
from .mcp_tools import add_change_note
from .models import AssessmentRecord, ChangeRequest, Outcome

log = logging.getLogger("changeguard")
app = FastAPI(title="ChangeGuard (synthetic)")


class AssessIn(BaseModel):
    title: str
    description: str
    ci: str
    change_type: str = "normal"
    scheduled_at: datetime
    requester: str = "anon-requester"
    rollback_plan_present: bool = False
    rollback_plan_tested: bool = False
    test_evidence: bool = False


class DecisionIn(BaseModel):
    comment: str = ""


class OutcomeIn(BaseModel):
    outcome: Outcome


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    hist = load_history(settings.data_path)
    opts = "".join(f'<option value="{h.id}">{h.id} — {h.title} ({h.ci})</option>' for h in hist[:50])
    recs = store_mod.all_records()[-10:]
    rows = "".join(
        f"<tr><td>{r.id}</td><td>{r.change.title}</td><td>{r.assessment.lane}</td>"
        f"<td>{r.assessment.score}</td><td>{r.decision}</td>"
        f"<td><a href='/assessments/{r.id}'>view</a></td></tr>" for r in recs
    )
    return f"""<!doctype html><html><head><title>ChangeGuard</title>
<style>body{{font-family:sans-serif;max-width:960px;margin:2em auto}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:4px 8px}}</style>
</head><body>
<h1>ChangeGuard — CAB review (synthetic Acme Retail Ltd)</h1>
<h2>1. Assess a change</h2>
<form method="post" action="/assessments/form">
<label>Title <input name="title" value="Orders DB index rebuild" size="40"></label><br>
<label>CI <input name="ci" value="orders-db"></label>
<label>Type <input name="change_type" value="normal"></label><br>
<label>Description <input name="description" value="Rebuild index on orders table during off-hours window" size="60"></label><br>
<label>Scheduled (ISO) <input name="scheduled_at" value="2025-03-14T22:30:00" size="24"></label>
<label>Requester <input name="requester" value="rel-eng-03"></label><br>
<label><input type="checkbox" name="rollback_plan_present" checked> rollback present</label>
<label><input type="checkbox" name="rollback_plan_tested"> rollback tested</label>
<label><input type="checkbox" name="test_evidence" checked> test evidence</label><br>
<button type="submit">Assess</button></form>
<h2>2. Or pick a historical CR</h2>
<form method="post" action="/assessments/historical">
<select name="change_id">{opts}</select><button type="submit">Assess historical</button></form>
<h2>Recent assessments</h2>
<table><tr><th>id</th><th>title</th><th>lane</th><th>score</th><th>decision</th><th></th></tr>{rows}</table>
<p>APIs: POST /assessments, GET /assessments/{{id}}, POST /assessments/{{id}}/approve|reject|request-info, POST /assessments/{{id}}/outcome</p>
</body></html>"""


@app.post("/assessments")
def assess(body: AssessIn) -> JSONResponse:
    cr = ChangeRequest(id=f"CR-{uuid4().hex[:6]}", **body.model_dump())
    rec = run_to_interrupt(cr)
    log.info(json.dumps({"request_id": rec.id, "lane": rec.assessment.lane, "score": rec.assessment.score}))
    return JSONResponse(rec.model_dump(mode="json"))


@app.get("/assessments/{rid}")
def get_assessment(rid: str) -> JSONResponse:
    rec = store_mod.get(rid)
    if rec is None:
        raise HTTPException(404, "unknown assessment")
    return JSONResponse(rec.model_dump(mode="json"))


def _decide(rid: str, decision: str, comment: str) -> AssessmentRecord:
    rec = store_mod.get(rid)
    if rec is None:
        raise HTTPException(404, "unknown assessment")
    rec.decision = decision  # type: ignore[assignment]
    rec.decision_comment = comment
    try:
        add_change_note(rec.change.id, f"CAB {decision}: {comment}", approved=True)
    except PermissionError as e:  # pragma: no cover - approved=True always passes
        raise HTTPException(500, str(e)) from e
    store_mod.save(rec)
    return rec


@app.post("/assessments/{rid}/approve")
def approve(rid: str, body: DecisionIn) -> JSONResponse:
    return JSONResponse(_decide(rid, "approved", body.comment).model_dump(mode="json"))


@app.post("/assessments/{rid}/reject")
def reject(rid: str, body: DecisionIn) -> JSONResponse:
    return JSONResponse(_decide(rid, "rejected", body.comment).model_dump(mode="json"))


@app.post("/assessments/{rid}/request-info")
def request_info(rid: str, body: DecisionIn) -> JSONResponse:
    return JSONResponse(_decide(rid, "needs-info", body.comment).model_dump(mode="json"))


@app.post("/assessments/{rid}/outcome")
def record_outcome(rid: str, body: OutcomeIn) -> JSONResponse:
    rec = store_mod.get(rid)
    if rec is None:
        raise HTTPException(404, "unknown assessment")
    rec.outcome = body.outcome
    store_mod.save(rec)
    return JSONResponse(rec.model_dump(mode="json"))


# --- tiny form handlers for the one-page UI (no JS needed) ---
from fastapi import Form  # noqa: E402
from fastapi.responses import RedirectResponse  # noqa: E402


@app.post("/assessments/form")
def assess_form(
    title: str = Form(""), description: str = Form(""), ci: str = Form("orders-db"),
    change_type: str = Form("normal"), scheduled_at: str = Form("2025-03-14T22:30:00"),
    requester: str = Form("anon"), rollback_plan_present: str | None = Form(None),
    rollback_plan_tested: str | None = Form(None), test_evidence: str | None = Form(None),
) -> RedirectResponse:
    cr = ChangeRequest(
        id=f"CR-{uuid4().hex[:6]}", title=title, description=description, ci=ci,
        change_type=change_type,  # type: ignore[arg-type]
        scheduled_at=datetime.fromisoformat(scheduled_at), requester=requester,
        rollback_plan_present=rollback_plan_present is not None,
        rollback_plan_tested=rollback_plan_tested is not None,
        test_evidence=test_evidence is not None,
    )
    rec = run_to_interrupt(cr)
    return RedirectResponse(f"/view/{rec.id}", status_code=303)


@app.post("/assessments/historical")
def assess_historical(change_id: str = Form("")) -> RedirectResponse:
    hist = load_history(settings.data_path)
    h = next((x for x in hist if x.id == change_id), None)
    if h is None:
        raise HTTPException(404, "unknown change")
    cr = ChangeRequest(**{k: v for k, v in h.model_dump().items() if k != "outcome"})
    rec = run_to_interrupt(cr)
    return RedirectResponse(f"/view/{rec.id}", status_code=303)


@app.get("/view/{rid}", response_class=HTMLResponse)
def view(rid: str) -> str:
    rec = store_mod.get(rid)
    if rec is None:
        raise HTTPException(404, "unknown assessment")
    a = rec.assessment
    rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in a.breakdown.contributions.items())
    ev = "".join(f"<li>[{e.id}] ({e.kind}) {e.snippet} — {e.confidence}</li>" for e in rec.evidence)
    sims = "".join(f"<li>{s['id']} → {s['outcome']}: {s['title']}</li>" for s in rec.similar)
    claims = "".join(
        f"<li>{c.text} <i>[{', '.join(c.evidence_ids)}]</i></li>" for c in (rec.explanation.claims if rec.explanation else [])
    )
    return f"""<!doctype html><html><head><title>{rec.id}</title>
<style>body{{font-family:sans-serif;max-width:960px;margin:2em auto}}</style></head><body>
<a href="/">← back</a><h1>{rec.change.title}</h1>
<p>CI {rec.change.ci} · {rec.change.change_type} · {rec.change.scheduled_at} · requester {rec.change.requester}</p>
<h2>Lane: {a.lane} — score {a.score}</h2>
<table><tr><th>driver</th><th>points</th></tr>{rows}</table>
<h3>Similar past changes</h3><ul>{sims}</ul>
<h3>Evidence</h3><ul>{ev}</ul>
<h3>Explanation</h3><p>{rec.explanation.summary if rec.explanation else 'n/a'}</p><ul>{claims}</ul>
<h3>Critic</h3><p>grounded={rec.critic.grounded if rec.critic else '?'} rate={rec.critic.grounding_rate if rec.critic else '?'}</p>
<h3>Decision (current: {rec.decision})</h3>
<form method="post" action="/ui/{rec.id}/approve">comment <input name="comment" size="40"><button>Approve</button></form>
<form method="post" action="/ui/{rec.id}/reject">comment <input name="comment" size="40"><button>Reject</button></form>
<form method="post" action="/ui/{rec.id}/request-info">comment <input name="comment" size="40"><button>Request info</button></form>
<form method="post" action="/ui/{rec.id}/outcome">outcome
<select name="outcome"><option>success</option><option>failed</option><option>caused-incident</option><option>rolled-back</option></select>
<button>Record outcome (PIR)</button></form>
</body></html>"""


@app.post("/ui/{rid}/approve")
def ui_approve(rid: str, comment: str = Form("")) -> RedirectResponse:
    _decide(rid, "approved", comment)
    return RedirectResponse(f"/view/{rid}", status_code=303)


@app.post("/ui/{rid}/reject")
def ui_reject(rid: str, comment: str = Form("")) -> RedirectResponse:
    _decide(rid, "rejected", comment)
    return RedirectResponse(f"/view/{rid}", status_code=303)


@app.post("/ui/{rid}/request-info")
def ui_info(rid: str, comment: str = Form("")) -> RedirectResponse:
    _decide(rid, "needs-info", comment)
    return RedirectResponse(f"/view/{rid}", status_code=303)


@app.post("/ui/{rid}/outcome")
def ui_outcome(rid: str, outcome: Outcome = Form("success")) -> RedirectResponse:
    rec = store_mod.get(rid)
    if rec is None:
        raise HTTPException(404, "unknown assessment")
    rec.outcome = outcome
    store_mod.save(rec)
    return RedirectResponse(f"/view/{rid}", status_code=303)


def history_path() -> Path:
    return Path(settings.data_path)
