"""AgentStack — Agent-native solution registry."""

import asyncio
import json
import secrets

from fastapi import FastAPI, Depends, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import engine, Base, get_db
from models import Agent, Solution, Rating, Log
from search import search_solutions
from simulation import run_wave

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AgentStack", description="Agent-native solution registry", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Auth helper ───────────────────────────────────────────────────

def get_agent_by_key(x_api_key: str = Header(...), db: Session = Depends(get_db)) -> Agent:
    agent = db.query(Agent).filter(Agent.api_key == x_api_key).first()
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return agent


# ─── Request schemas ───────────────────────────────────────────────

class AgentSignup(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)


class SolutionPush(BaseModel):
    task_description: str = Field(..., min_length=1)
    solution_type: str = Field(default="artifact", pattern="^(artifact|tool_call|subagent|skill)$")
    solution: str = Field(..., min_length=1)
    language: str = Field(default="python", max_length=64)
    tags: list[str] = Field(default_factory=list)
    input_schema: str = Field(default="")
    output_schema: str = Field(default="")
    composed_from: list[str] = Field(default_factory=list)


class RateBody(BaseModel):
    rating: int = Field(..., ge=0, le=1)


class WaveBody(BaseModel):
    wave: int = Field(..., ge=1, le=3)


# ─── Agent endpoints ──────────────────────────────────────────────

@app.post("/agents/signup")
def signup(body: AgentSignup, db: Session = Depends(get_db)):
    existing = db.query(Agent).filter(Agent.name == body.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Agent name already taken")
    agent = Agent(name=body.name, api_key=f"ask_{secrets.token_urlsafe(24)}")
    db.add(agent)
    db.commit()
    db.refresh(agent)
    _log(db, "signup", agent.name, {"agent_id": agent.id})
    return agent.to_dict()


@app.get("/agents")
def list_agents(db: Session = Depends(get_db)):
    agents = db.query(Agent).order_by(Agent.created_at.desc()).all()
    return [a.to_dict() for a in agents]


# ─── Solution endpoints ───────────────────────────────────────────

@app.get("/solutions")
def list_solutions(db: Session = Depends(get_db)):
    solutions = db.query(Solution).order_by(Solution.success_rate.desc()).all()
    return [s.to_dict() for s in solutions]


@app.get("/solutions/search")
def search(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    all_solutions = db.query(Solution).all()
    results = search_solutions(all_solutions, q, limit=5)
    return [{"solution": s.to_dict(), "score": round(sc, 2)} for s, sc in results]


@app.post("/solutions", status_code=201)
def push_solution(
    body: SolutionPush,
    agent: Agent = Depends(get_agent_by_key),
    db: Session = Depends(get_db),
):
    sol = Solution(
        task_description=body.task_description,
        solution_type=body.solution_type,
        solution=body.solution,
        language=body.language,
        tags=body.tags,
        input_schema=body.input_schema,
        output_schema=body.output_schema,
        agent_id=agent.id,
        agent_name=agent.name,
        composed_from=body.composed_from,
    )
    db.add(sol)
    agent.push_count += 1
    db.commit()
    db.refresh(sol)
    _log(db, "push", agent.name, {"solution_id": sol.id})
    return sol.to_dict()


@app.get("/solutions/{solution_id}")
def get_solution(solution_id: str, db: Session = Depends(get_db)):
    sol = db.query(Solution).filter(Solution.id == solution_id).first()
    if not sol:
        raise HTTPException(status_code=404, detail="Solution not found")
    return sol.to_dict()


@app.post("/solutions/{solution_id}/rate")
def rate_solution(
    solution_id: str,
    body: RateBody,
    agent: Agent = Depends(get_agent_by_key),
    db: Session = Depends(get_db),
):
    sol = db.query(Solution).filter(Solution.id == solution_id).first()
    if not sol:
        raise HTTPException(status_code=404, detail="Solution not found")

    rating = Rating(solution_id=solution_id, agent_name=agent.name, rating=body.rating)
    db.add(rating)

    sol.attempt_count += 1
    all_ratings = db.query(Rating).filter(Rating.solution_id == solution_id).all()
    # Include the new one we just added
    total = sum(r.rating for r in all_ratings) + body.rating
    count = len(all_ratings) + 1
    sol.success_rate = total / count

    db.commit()
    _log(db, "rate", agent.name, {"solution_id": solution_id, "rating": body.rating})
    return {"success": True, "new_success_rate": sol.success_rate}


# ─── Logs & stats ─────────────────────────────────────────────────

@app.get("/logs")
def list_logs(limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db)):
    logs = db.query(Log).order_by(Log.created_at.desc()).limit(limit).all()
    return [l.to_dict() for l in logs]


@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    total_agents = db.query(Agent).count()
    total_solutions = db.query(Solution).count()
    total_ratings = db.query(Rating).count()
    total_pulls = sum(a.pull_count for a in db.query(Agent).all())
    total_pushes = sum(a.push_count for a in db.query(Agent).all())

    atomic = db.query(Solution).filter(Solution.composed_from == "[]").count()
    # SQLite stores JSON arrays as strings, so also check for empty list
    atomic2 = db.query(Solution).filter(Solution.composed_from == None).count()
    all_solutions = db.query(Solution).all()
    atomic_count = sum(1 for s in all_solutions if not s.composed_from)
    composed_count = total_solutions - atomic_count

    avg_success = 0.0
    if all_solutions:
        avg_success = sum(s.success_rate for s in all_solutions) / len(all_solutions)

    return {
        "total_agents": total_agents,
        "total_solutions": total_solutions,
        "atomic_solutions": atomic_count,
        "composed_solutions": composed_count,
        "total_ratings": total_ratings,
        "total_pulls": total_pulls,
        "total_pushes": total_pushes,
        "avg_success_rate": round(avg_success, 3),
    }


# ─── Simulation SSE ───────────────────────────────────────────────

@app.post("/simulate/wave")
async def simulate_wave(body: WaveBody):
    queue: asyncio.Queue = asyncio.Queue()

    async def event_generator():
        task = asyncio.create_task(run_wave(body.wave, queue))
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=120)
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("step") == "wave_complete":
                    break
                if event.get("step") == "error" and event.get("agent") == "system":
                    break
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'agent': 'system', 'step': 'timeout'})}\n\n"
                break
        # Make sure the task is done
        if not task.done():
            task.cancel()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ─── Health ────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"service": "AgentStack", "version": "0.1.0", "docs": "/docs"}


# ─── Internal helper ──────────────────────────────────────────────

def _log(db: Session, event: str, agent_name: str, payload: dict):
    entry = Log(event=event, agent_name=agent_name, payload=payload)
    db.add(entry)
    db.commit()
