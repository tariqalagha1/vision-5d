"""
CASCADE LEARNING CHECK — Pipeline Trace Runner
Monkey-patches SQLAlchemy to capture every database read,
then runs plan-understanding on a fresh project.
"""
import uuid, json, os, sys, time, hashlib
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Monkey-patch BEFORE importing anything that uses SQLAlchemy
import sqlalchemy
from sqlalchemy import event

ALL_SQL = []

@event.listens_for(sqlalchemy.engine.Engine, "before_cursor_execute")
def capture_all_sql(conn, cursor, statement, parameters, context, executemany):
    ALL_SQL.append({
        "statement": statement.replace('\n', ' ').strip(),
        "params": str(parameters)[:300],
        "ts": datetime.utcnow().isoformat()
    })

# Now import project modules
from packages.domain.database import SessionLocal, engine
from packages.domain.models import Base, DurableJob, UnderstandingGraph, GraphNode, GraphEdge
from packages.domain.persistence import persist_understanding_graph
from packages.plan_understanding.pipeline import plan_pipeline

# Create fresh project in DB
db = SessionLocal()
Base.metadata.create_all(bind=engine)

tenant_id = uuid.uuid4()
ws_id = uuid.uuid4()
project_id = uuid.uuid4()
source_asset_id = uuid.uuid4()
job_id = uuid.uuid4()

db.execute(sqlalchemy.text(
    "INSERT INTO tenants (id, external_id) VALUES (:id, :ext)"
), {"id": tenant_id, "ext": f"trace-{tenant_id.hex[:8]}"})

db.execute(sqlalchemy.text(
    "INSERT INTO workspaces (id, tenant_id, name, state) VALUES (:id, :tid, :n, :s)"
), {"id": ws_id, "tid": tenant_id, "n": f"trace-ws-{ws_id.hex[:8]}", "s": "ACTIVE"})

db.execute(sqlalchemy.text(
    "INSERT INTO projects (id, workspace_id, tenant_id, name, state, project_type) VALUES (:id, :wid, :tid, :n, :s, :pt)"
), {"id": project_id, "wid": ws_id, "tid": tenant_id, "n": f"TRACE-{project_id.hex[:8]}", "s": "DRAFT", "pt": "residential"})

db.execute(sqlalchemy.text(
    "INSERT INTO jobs (id, tenant_id, workspace_id, project_id, job_type, idempotency_key, state, params) VALUES (:id, :tid, :wid, :pid, :jt, :ik, :s, :p)"
), {"id": job_id, "tid": tenant_id, "wid": ws_id, "pid": project_id,
    "jt": "plan-understanding", "ik": f"trace-{job_id.hex[:8]}", "s": "QUEUED",
    "p": json.dumps({"project_id": str(project_id), "source_asset_id": str(source_asset_id)})})

db.commit()

print(f"FRESH PROJECT: TRACE-{project_id.hex[:8]}")
print(f"  project_id: {project_id}")

# Clear SQL capture to start fresh for the pipeline run
ALL_SQL.clear()

# Run the plan understanding pipeline
test_img = os.path.join(os.path.dirname(__file__), "..", "..", "test_plan.png")
with open(test_img, "rb") as f:
    image_bytes = f.read()

print(f"Running plan_pipeline.process()...")
result = plan_pipeline.process(project_id, source_asset_id, image_bytes)
print(f"Result: {result.graph.room_count()} rooms, {result.graph.wall_count()} walls")

# Persist
graph_db = persist_understanding_graph(db, tenant_id, project_id, source_asset_id, job_id, result.graph)
db.commit()

print(f"Persisted graph: {graph_db.id}")

# Analyze captured SQL
project_id_str = str(project_id)
project_id_short = project_id_str[:12]

cross_project = []
self_project = []
other = []

for s in ALL_SQL:
    stmt = s["statement"].lower()
    params = s["params"].lower()
    if "project" in stmt or "project" in params:
        if project_id_short in stmt or project_id_short in params:
            self_project.append(s)
        else:
            cross_project.append(s)
    else:
        other.append(s)

print(f"\n=== SQL TRACE ===")
print(f"Total SQL: {len(ALL_SQL)}")
print(f"Self-project: {len(self_project)}")
print(f"Cross-project: {len(cross_project)}")
print(f"Other (no project ref): {len(other)}")

if cross_project:
    print(f"\n!!! CROSS-PROJECT QUERIES DETECTED !!!")
    for s in cross_project:
        print(f"  {s['statement'][:200]}")
else:
    print(f"\nNO CROSS-PROJECT QUERIES DETECTED")

# Save results
evidence_dir = os.path.join(os.path.dirname(__file__))
results = {
    "project_id": project_id_str,
    "tenant_id": str(tenant_id),
    "total_sql": len(ALL_SQL),
    "self_project_queries": len(self_project),
    "cross_project_queries": len(cross_project),
    "other_queries": len(other),
    "cross_detected": len(cross_project) > 0,
    "cross_details": [
        {"statement": s["statement"], "params": s["params"]}
        for s in cross_project
    ],
    "self_sample": [
        {"statement": s["statement"], "params": s["params"]}
        for s in self_project[:10]
    ]
}

with open(os.path.join(evidence_dir, "new_run_trace.json"), "w") as f:
    json.dump(results, f, indent=2, default=str)

print(f"\nTrace saved to new_run_trace.json")
db.close()
