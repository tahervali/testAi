"""Multi-agent simulation engine with SSE streaming."""

import asyncio
import json
import os
import secrets
from datetime import datetime, timezone

import anthropic
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Agent, Solution, Rating, Log
from search import search_solutions

MODEL = "claude-sonnet-4-5"

WAVE_TASKS = {
    1: [
        "clean and normalize dataframe column names for pipeline ingestion",
        "validate and standardize date fields across multiple formats",
        "deduplicate records and merge overlapping beneficiary entries",
    ],
    2: [
        "build a data cleaning pipeline: normalize columns, validate dates, and deduplicate records",
        "prepare beneficiary dataset for reporting: clean fields, standardize formats, remove duplicates",
    ],
    3: [
        "end-to-end beneficiary data pipeline: ingest raw data, clean all fields, validate, deduplicate, and generate quality report",
    ],
}


def _log(db: Session, event: str, agent_name: str, payload: dict):
    entry = Log(event=event, agent_name=agent_name, payload=payload)
    db.add(entry)
    db.commit()


def _ensure_agent(db: Session, name: str) -> Agent:
    agent = db.query(Agent).filter(Agent.name == name).first()
    if not agent:
        agent = Agent(name=name, api_key=f"sim_{secrets.token_urlsafe(16)}")
        db.add(agent)
        db.commit()
        db.refresh(agent)
    return agent


async def _call_claude(client: anthropic.AsyncAnthropic, system: str, prompt: str) -> str:
    resp = await client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


async def run_agent(
    task: str,
    agent_name: str,
    queue: asyncio.Queue,
):
    """Run a single simulated agent through the full loop."""
    db = SessionLocal()
    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    async def emit(step: str, data: dict = None):
        event = {"agent": agent_name, "step": step, **(data or {})}
        await queue.put(event)

    try:
        agent = _ensure_agent(db, agent_name)
        await emit("think", {"task": task})

        # Step 1: Decompose task into subtasks
        await emit("decompose", {"status": "calling claude..."})
        decompose_result = await _call_claude(
            client,
            "You are a task decomposition engine. Given a task, break it into 2-3 atomic subtasks. Return ONLY a JSON array of strings.",
            f"Decompose this task into 2-3 atomic subtasks:\n\n{task}",
        )

        # Parse subtasks
        try:
            # Try to extract JSON array from response
            import re
            match = re.search(r'\[.*\]', decompose_result, re.DOTALL)
            subtasks = json.loads(match.group()) if match else [task]
        except (json.JSONDecodeError, AttributeError):
            subtasks = [task]

        await emit("decompose", {"subtasks": subtasks})

        # Step 2: For each subtask, search the registry
        pulled_solutions = []
        all_solutions = db.query(Solution).all()

        for subtask in subtasks:
            results = search_solutions(all_solutions, subtask, limit=3)
            if results:
                best, score = results[0]
                await emit("hit", {
                    "subtask": subtask,
                    "solution_id": best.id,
                    "score": round(score, 2),
                    "task_description": best.task_description,
                })
                pulled_solutions.append(best)
                # Increment pull count
                best_in_db = db.query(Solution).filter(Solution.id == best.id).first()
                if best_in_db:
                    agent.pull_count += 1
                    db.commit()
                _log(db, "pull", agent_name, {"solution_id": best.id, "subtask": subtask})
            else:
                await emit("miss", {"subtask": subtask})
                _log(db, "miss", agent_name, {"subtask": subtask})

        # Step 3: Compose a full solution, reusing pulled artifacts
        await emit("compose", {"status": "calling claude...", "reusing": len(pulled_solutions)})

        reuse_context = ""
        if pulled_solutions:
            reuse_context = "\n\nYou can reuse these existing solutions:\n"
            for ps in pulled_solutions:
                reuse_context += f"\n--- Solution: {ps.task_description} ---\n{ps.solution}\n"

        compose_result = await _call_claude(
            client,
            "You are a Python developer. Write a complete, working Python solution for the given task. Return ONLY the Python code, no markdown fences.",
            f"Write a Python solution for:\n\n{task}{reuse_context}",
        )

        # Clean up markdown fences if present
        code = compose_result.strip()
        if code.startswith("```"):
            lines = code.split("\n")
            lines = lines[1:]  # remove opening fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            code = "\n".join(lines)

        await emit("compose", {"status": "done", "code_length": len(code)})

        # Step 4: Evaluate the solution
        await emit("test", {"status": "calling claude..."})
        eval_result = await _call_claude(
            client,
            'You are a code reviewer. Evaluate if the solution is correct and complete. Return ONLY a JSON object: {"pass": true/false, "reason": "..."}',
            f"Task: {task}\n\nSolution:\n{code}",
        )

        try:
            import re
            match = re.search(r'\{.*\}', eval_result, re.DOTALL)
            eval_data = json.loads(match.group()) if match else {"pass": True, "reason": "assumed pass"}
        except (json.JSONDecodeError, AttributeError):
            eval_data = {"pass": True, "reason": "assumed pass"}

        passed = eval_data.get("pass", True)
        await emit("test", {"passed": passed, "reason": eval_data.get("reason", "")})

        # Step 5: Rate pulled artifacts
        for ps in pulled_solutions:
            rating_val = 1 if passed else 0
            rating = Rating(
                solution_id=ps.id,
                agent_name=agent_name,
                rating=rating_val,
            )
            db.add(rating)

            # Update success_rate on the solution
            sol = db.query(Solution).filter(Solution.id == ps.id).first()
            if sol:
                sol.attempt_count += 1
                # Recalculate success_rate from all ratings
                all_ratings = db.query(Rating).filter(Rating.solution_id == ps.id).all()
                if all_ratings:
                    sol.success_rate = sum(r.rating for r in all_ratings) / len(all_ratings)
                db.commit()

            await emit("rate", {"solution_id": ps.id, "rating": rating_val})

        # Step 6: Push the composed solution
        composed_from = [ps.id for ps in pulled_solutions]
        new_solution = Solution(
            task_description=task,
            solution_type="artifact",
            solution=code,
            language="python",
            tags=_extract_tags(task),
            agent_id=agent.id,
            agent_name=agent_name,
            success_rate=1.0 if passed else 0.0,
            attempt_count=1,
            composed_from=composed_from,
        )
        db.add(new_solution)
        agent.push_count += 1
        db.commit()
        db.refresh(new_solution)

        _log(db, "push", agent_name, {
            "solution_id": new_solution.id,
            "task": task,
            "composed_from": composed_from,
        })

        await emit("push", {
            "solution_id": new_solution.id,
            "composed_from": composed_from,
        })
        await emit("done", {"solution_id": new_solution.id, "passed": passed})

    except Exception as e:
        await emit("error", {"message": str(e)})
    finally:
        db.close()


def _extract_tags(task: str) -> list[str]:
    """Extract simple tags from a task description."""
    keywords = [
        "clean", "normalize", "validate", "date", "deduplicate", "merge",
        "pipeline", "dataframe", "column", "records", "beneficiary",
        "reporting", "ingest", "quality", "format", "standardize",
    ]
    words = task.lower().split()
    return [k for k in keywords if any(k in w for w in words)]


async def run_wave(wave: int, queue: asyncio.Queue):
    """Run all agents in a wave concurrently."""
    tasks = WAVE_TASKS.get(wave, [])
    if not tasks:
        await queue.put({"agent": "system", "step": "error", "message": f"Invalid wave: {wave}"})
        return

    await queue.put({"agent": "system", "step": "wave_start", "wave": wave, "agent_count": len(tasks)})

    agent_tasks = []
    for i, task in enumerate(tasks):
        agent_name = f"wave{wave}-agent-{i+1}"
        agent_tasks.append(run_agent(task, agent_name, queue))

    await asyncio.gather(*agent_tasks)
    await queue.put({"agent": "system", "step": "wave_complete", "wave": wave})
