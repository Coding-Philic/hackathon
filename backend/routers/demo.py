import datetime
import random
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from typing import List

try:
    from backend.database import get_db
    from backend import models, schemas, simulator, agent, memory, routers
except ImportError:
    from database import get_db
    import models, schemas, simulator, agent, memory

router = APIRouter(prefix="/demo", tags=["Demo Controller"])


def _pick_random_scenario():
    """Return a random hospital incident scenario for dynamic demos."""
    return random.choice(list(SERVICE_INCIDENT_SCENARIOS.items()))


def trigger_agent_background(incident_id: int):
    db = next(get_db())
    try:
        agent.run_agent_on_incident(db, incident_id)
    except Exception as e:
        print(f"Error running SRE Agent in Demo: {e}")
    finally:
        db.close()

@router.post("/1", response_model=schemas.IncidentInDB)
def run_demo_1(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Demo 1: Fresh random outage scenario each time to avoid repeating the same incident."""
    # 1. Clear database and vector memory
    # We call our internal clear memories logic
    db.query(models.MemoryEntry).delete()
    db.query(models.IncidentAction).delete()
    db.query(models.AgentDecision).delete()
    db.query(models.Incident).delete()
    db.query(models.ServiceLog).delete()
    
    # 2. Reset services to Running
    services = db.query(models.Service).all()
    if not services:
        simulator.init_services(db)
        services = db.query(models.Service).all()
    else:
        for s in services:
            s.status = "Running"
            s.health_score = 100
            s.error_count = 0
            s.uptime = 0
    db.commit()
    
    # 3. Clear Qdrant collection if client exists
    if memory.qdrant_client:
        try:
            memory.qdrant_client.delete_collection(collection_name=memory.COLLECTION_NAME)
            memory.init_qdrant_collection()
        except Exception as e:
            print(f"Failed to clear Qdrant in Demo 1: {e}")
            
    # 4. Pick a fresh random scenario so Demo 1 produces a different incident on every run.
    service_name, scenario = _pick_random_scenario()
    db_incident = simulator.inject_incident(
        db=db,
        title=scenario["title"],
        symptoms=scenario["symptoms"],
        affected_services=service_name,
        severity=scenario["severity"]
    )
    
    # 5. Run agent loop in background
    background_tasks.add_task(trigger_agent_background, db_incident.id)
    
    return db_incident

# ---------------------------------------------------------------------------
# Dynamic scenario mapping — one entry per hospital service
# When Demo 2 detects a service is down, it looks up the matching incident here
# ---------------------------------------------------------------------------
SERVICE_INCIDENT_SCENARIOS = {
    "Lab Service": {
        "title": "Lab Reports Not Generating",
        "symptoms": "Doctors cannot access laboratory reports. Lab queue worker is unresponsive. File output directory reports 0 records written.",
        "severity": "High",
        "root_cause": "A file descriptor leak in the report generation queue caused the service worker to freeze.",
        "resolution": "Restart the Lab Service to flush file handles and clean the cache directory.",
        "action_type": "Restart Service",
    },
    "Authentication Service": {
        "title": "User Login Failures",
        "symptoms": "Nurses and doctors cannot authenticate. JWT token validation returning Error 500. Session creation rejected.",
        "severity": "High",
        "root_cause": "Session token synchronization buffer overflowed due to high traffic volume, locking login threads.",
        "resolution": "Reset session controller memory cache and clear Authentication session logs.",
        "action_type": "Reset Authentication",
    },
    "Billing Service": {
        "title": "Billing Transactions Failing",
        "symptoms": "Payments locked in invoice queue. Database returns transaction lock timeout. Active invoices stuck in Pending state.",
        "severity": "High",
        "root_cause": "Database lock contention on active invoices table halted the processing thread pool.",
        "resolution": "Clear active transaction queues and re-establish Database Service connection pool.",
        "action_type": "Reconnect Database",
    },
    "Pharmacy Service": {
        "title": "Pharmacy Inventory Sync Failed",
        "symptoms": "Pharmacy inventory synchronization API returned recurring timeouts. Prescription database not synced with local supplier inventory.",
        "severity": "High",
        "root_cause": "Vendor inventory synchronization API returned recurring timeouts, causing backoff loop starvation.",
        "resolution": "Recover Pharmacy Service backoff queue and switch to backup inventory caching server.",
        "action_type": "Enable Backup Service",
    },
    "Database Service": {
        "title": "Database Connection Refused",
        "symptoms": "Telemetry detects database socket refusal. Port 5432 is unresponsive. All dependent services report connection failures.",
        "severity": "Critical",
        "root_cause": "Database connection pool saturated by unindexed query spikes on medical chart tables.",
        "resolution": "Flush connection pool, clear active queries, and recycle Database Service container.",
        "action_type": "Reconnect Database",
    },
    "API Gateway": {
        "title": "API Gateway Timeout",
        "symptoms": "Internal API calls return Gateway Timeout. Gateway routing table is corrupted. Microservice mesh unreachable.",
        "severity": "Medium",
        "root_cause": "API Gateway routing table got desynchronized during an internal network socket flap.",
        "resolution": "Reload API Gateway configuration routing maps and run service status check.",
        "action_type": "Restart Service",
    },
}

@router.post("/2")
def run_demo_2(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Demo 2: FULLY DYNAMIC autonomous agent dispatch.
    - Scans ALL currently stopped or degraded services
    - Creates a tailored incident for each broken service
    - Seeds memory for any service not previously seen (so agent can act autonomously)
    - Runs the SRE agent on every incident in parallel background tasks
    - If nothing is broken: falls back to stopping a random service as a demo target
    """
    # Step 1: Reset the service board so Demo 2 always starts from a clean, healthy state.
    all_services = db.query(models.Service).all()
    if not all_services:
        simulator.init_services(db)
        all_services = db.query(models.Service).all()

    for svc in all_services:
        simulator.recover_service(db, svc.service_name)

    db.commit()

    # Step 2: Force a fresh random outage target for this run, instead of reusing an old broken service.
    target = random.choice(all_services) if all_services else None
    troubled = []
    if target:
        simulator.stop_service(db, target.service_name)
        troubled = [db.query(models.Service).filter_by(service_name=target.service_name).first()]

    created_incidents = []

    for svc in troubled:
        name = svc.service_name

        # Look up the scenario for this specific service
        scenario = SERVICE_INCIDENT_SCENARIOS.get(name, {
            "title": f"{name} Service Failure Detected",
            "symptoms": f"{name} is unresponsive. Telemetry shows repeated health check failures and connection refused errors.",
            "severity": "High",
            "root_cause": f"Unknown failure in {name}. Service process has exited unexpectedly.",
            "resolution": f"Restart {name} and verify all downstream dependencies are healthy.",
            "action_type": "Restart Service",
        })

        # Step 3: Seed memory for this service if it has never been resolved before
        # This means the agent can act autonomously for ANY stopped service
        existing_mem = db.query(models.MemoryEntry).filter_by(title=scenario["title"]).first()
        if not existing_mem:
            memory.store_memory(
                db=db,
                title=scenario["title"],
                symptoms=scenario["symptoms"],
                affected_services=name,
                root_cause=scenario["root_cause"],
                resolution=scenario["resolution"],
                actions_executed=[scenario["action_type"]],
                success_rate=1.0
            )

        # Step 4: Create a live incident for this service
        db_incident = simulator.inject_incident(
            db=db,
            title=scenario["title"],
            symptoms=scenario["symptoms"],
            affected_services=name,
            severity=scenario["severity"]
        )
        created_incidents.append(db_incident)

        # Step 5: Run the SRE agent on each incident in a background thread
        background_tasks.add_task(trigger_agent_background, db_incident.id)

    return {
        "incidents_triggered": len(created_incidents),
        "services_affected": [s.service_name for s in troubled],
        "primary_incident_id": created_incidents[0].id if created_incidents else None,
        "message": (
            f"Agent dispatched for {len(created_incidents)} service(s): "
            + ", ".join(s.service_name for s in troubled)
        )
    }


@router.post("/3")
def run_demo_3(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Demo 3: Scales memory timeline and populates analytics. Injects new Pharmacy outage."""
    # 1. Reset service state & clear past logs to avoid mess, but keep memories!
    db.query(models.IncidentAction).delete()
    db.query(models.AgentDecision).delete()
    db.query(models.Incident).delete()
    db.query(models.ServiceLog).delete()
    
    services = db.query(models.Service).all()
    if not services:
        simulator.init_services(db)
        services = db.query(models.Service).all()
    else:
        for s in services:
            s.status = "Running"
            s.health_score = 100
            s.error_count = 0
            s.uptime = 23840 # simulated uptime
    db.commit()
    
    # 2. Seed multiple vector memories
    # Lab Memory
    memory.store_memory(
        db=db,
        title="Lab Reports Not Generating",
        symptoms="Doctors cannot access laboratory reports. File output directory reports 0 records written.",
        affected_services="Lab Service",
        root_cause="A file descriptor leak in the report generation queue caused the service worker to freeze.",
        resolution="Restart the Lab Service to flush file handles and clean the cache directory.",
        actions_executed=["Restart Service"],
        success_rate=1.0
    )
    # Auth Memory
    memory.store_memory(
        db=db,
        title="User Login Failures",
        symptoms="Doctors and nurses cannot authenticate. Error 500 in JWT token validation endpoint.",
        affected_services="Authentication Service",
        root_cause="Session token synchronization buffer overflowed due to high traffic volume, locking login threads.",
        resolution="Reset session controller memory cache and clear Authentication session logs.",
        actions_executed=["Reset Authentication"],
        success_rate=0.98
    )
    # Billing Memory
    memory.store_memory(
        db=db,
        title="Billing Transactions Failing",
        symptoms="Active invoices stuck in Pending state. Payment processor returns Gateway Timeout.",
        affected_services="Billing Service",
        root_cause="Database lock contention on active invoices table halted the processing thread pool.",
        resolution="Clear active transaction queues and re-establish Database Service connection pool.",
        actions_executed=["Reconnect Database"],
        success_rate=0.92
    )
    # DB Memory
    memory.store_memory(
        db=db,
        title="Database Connection Refused",
        symptoms="All services report database connection timeouts. Health endpoint returning 503.",
        affected_services="Database Service",
        root_cause="Database connection pool saturated by unindexed query spikes on medical chart tables.",
        resolution="Flush connection pool, clear active queries, and recycle Database Service container.",
        actions_executed=["Reconnect Database"],
        success_rate=0.95
    )
    
    # 3. Create historical resolved incidents in SQL so analytics display nicely
    hist_incidents = [
        {
            "title": "Lab Reports Not Generating",
            "symptoms": "Doctors cannot access laboratory reports.",
            "affected_services": "Lab Service",
            "resolution_type": "autonomous",
            "hours_ago": 12,
            "actions": ["Restart Service"],
            "rc": "A file descriptor leak in the report generation queue caused the service worker to freeze.",
            "conf": 0.96
        },
        {
            "title": "User Login Failures",
            "symptoms": "Doctors and nurses cannot authenticate.",
            "affected_services": "Authentication Service",
            "resolution_type": "autonomous",
            "hours_ago": 8,
            "actions": ["Reset Authentication"],
            "rc": "Session token synchronization buffer overflowed due to high traffic volume.",
            "conf": 0.98
        },
        {
            "title": "Billing Transactions Failing",
            "symptoms": "Active invoices stuck in Pending state.",
            "affected_services": "Billing Service",
            "resolution_type": "autonomous",
            "hours_ago": 4,
            "actions": ["Reconnect Database"],
            "rc": "Database lock contention on active invoices table halted the processing thread pool.",
            "conf": 0.92
        },
        {
            "title": "Database Connection Refused",
            "symptoms": "All services report database connection timeouts.",
            "affected_services": "Database Service",
            "resolution_type": "human",
            "hours_ago": 1,
            "actions": ["Reconnect Database"],
            "rc": "Database connection pool saturated by unindexed query spikes.",
            "conf": 0.35
        }
    ]
    
    now = datetime.datetime.utcnow()
    for item in hist_incidents:
        created = now - datetime.timedelta(hours=item["hours_ago"])
        resolved = created + datetime.timedelta(minutes=random.randint(1, 8))
        
        inc = models.Incident(
            title=item["title"],
            symptoms=item["symptoms"],
            affected_services=item["affected_services"],
            status="Closed",
            severity="High",
            created_at=created,
            resolved_at=resolved,
            resolution_type=item["resolution_type"]
        )
        db.add(inc)
        db.commit()
        db.refresh(inc)
        
        # Add historical actions
        for act_type in item["actions"]:
            action = models.IncidentAction(
                incident_id=inc.id,
                action_type=act_type,
                command=f"restart_service('{item['affected_services']}')",
                status="Success",
                log="Autonomous recovery action succeeded. Verification completed.",
                executed_at=resolved
            )
            db.add(action)
            
        # Add Agent Decision
        decision = models.AgentDecision(
            incident_id=inc.id,
            reasoning=f"Analyzed incident symptoms and retrieved memory matches. Resolution action selected: {item['actions'][0]}.",
            confidence=item["conf"],
            actions_proposed=f"Execute {item['actions'][0]}",
            action_selected=item["actions"][0] if item["resolution_type"] == "autonomous" else "Escalate to Human SRE",
            status="Success" if item["resolution_type"] == "autonomous" else "Escalated",
            timestamp=resolved
        )
        db.add(decision)
        db.commit()
        
    # 4. Inject a CURRENT active incident to demonstrate SRE response at scale
    # Incident: Pharmacy Inventory Sync Failed
    db_incident = simulator.inject_incident(
        db=db,
        title="Pharmacy Inventory Sync Failed",
        symptoms="Pharmacy inventory synchronization API returned recurring timeouts. Prescription database not synced with local supplier inventory.",
        affected_services="Pharmacy Service",
        severity="High"
    )
    
    # Run Agent Loop on Pharmacy Incident
    background_tasks.add_task(trigger_agent_background, db_incident.id)
    
    return {
        "message": "Demo 3 scaled dataset populated successfully. Live incident triggered on Pharmacy Service.",
        "active_incident_id": db_incident.id
    }
