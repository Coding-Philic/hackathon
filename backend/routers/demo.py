import datetime
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
    """Demo 1: Memory Empty, Lab Service Stopped. Agent cannot fix it -> Escalates."""
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
            
    # 4. Inject Incident: Lab Reports Not Generating
    db_incident = simulator.inject_incident(
        db=db,
        title="Lab Reports Not Generating",
        symptoms="Doctors cannot access laboratory reports. File output directory reports 0 records written.",
        affected_services="Lab Service",
        severity="High"
    )
    
    # 5. Run agent loop in background
    background_tasks.add_task(trigger_agent_background, db_incident.id)
    
    return db_incident

@router.post("/2", response_model=schemas.IncidentInDB)
def run_demo_2(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Demo 2: Same Outage, Agent retrieves memory, executes autonomous restart."""
    # 1. Make sure Lab Service is Running or Stopped. We'll set it to Stopped.
    simulator.stop_service(db, "Lab Service")
    
    # 2. Seed memory entry if not exists (in case user skipped Demo 1 manual resolution)
    existing_mem = db.query(models.MemoryEntry).filter_by(title="Lab Reports Not Generating").first()
    if not existing_mem:
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
        
    # 3. Inject same Incident again
    db_incident = simulator.inject_incident(
        db=db,
        title="Lab Reports Not Generating",
        symptoms="Doctors cannot access laboratory reports. File output directory reports 0 records written.",
        affected_services="Lab Service",
        severity="High"
    )
    
    # 4. Run SRE Agent asynchronously
    background_tasks.add_task(trigger_agent_background, db_incident.id)
    
    return db_incident

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
