import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Body
from sqlalchemy.orm import Session
from typing import List, Optional

try:
    from backend.database import get_db
    from backend import models, schemas, simulator, agent, memory
except ImportError:
    from database import get_db
    import models, schemas, simulator, agent, memory

router = APIRouter(prefix="/incidents", tags=["Incidents"])

@router.get("/", response_model=List[schemas.IncidentInDB])
def list_incidents(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Incident)
    if status:
        query = query.filter_by(status=status)
    return query.order_by(models.Incident.created_at.desc()).all()

@router.get("/{id}", response_model=schemas.IncidentInDB)
def get_incident(id: int, db: Session = Depends(get_db)):
    incident = db.query(models.Incident).filter_by(id=id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident

def trigger_agent_background(incident_id: int):
    """Executes the SRE Agent LangGraph loop in a background thread."""
    db = next(get_db())
    try:
        agent.run_agent_on_incident(db, incident_id)
    except Exception as e:
        import traceback
        print(f"Error in SRE Agent loop background thread: {e}")
        traceback.print_exc()
    finally:
        db.close()

@router.post("/", response_model=schemas.IncidentInDB)
def trigger_incident_api(
    payload: schemas.IncidentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # 1. Inject the incident and stop/degrade affected services
    db_incident = simulator.inject_incident(
        db=db,
        title=payload.title,
        symptoms=payload.symptoms,
        affected_services=payload.affected_services,
        severity=payload.severity
    )
    
    # 2. Trigger the Agent Loop asynchronously
    background_tasks.add_task(trigger_agent_background, db_incident.id)
    
    return db_incident

@router.post("/{id}/resolve-manual", response_model=schemas.IncidentInDB)
def resolve_incident_manually_api(
    id: int,
    root_cause: str = Body(..., embed=True),
    resolution: str = Body(..., embed=True),
    action_type: str = Body(..., embed=True), # e.g. "Restart Service"
    db: Session = Depends(get_db)
):
    incident = db.query(models.Incident).filter_by(id=id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    if incident.status == "Closed":
        raise HTTPException(status_code=400, detail="Incident already closed")
        
    # 1. Execute the resolution command based on action_type & affected service
    service_name = incident.affected_services.split(",")[0].strip()
    
    # Log manual action
    db_action = models.IncidentAction(
        incident_id=incident.id,
        action_type=action_type,
        command=f"manual_{action_type.lower().replace(' ', '_')}('{service_name}')",
        status="Executing",
        executed_at=datetime.datetime.utcnow()
    )
    db.add(db_action)
    db.commit()
    
    success = False
    try:
        # Perform action
        if "Restart" in action_type:
            simulator.restart_service(db, service_name)
        elif "Reconnect" in action_type:
            simulator.recover_service(db, service_name)
        elif "Clear" in action_type:
            simulator.recover_service(db, service_name)
        else:
            simulator.start_service(db, service_name)
        success = True
    except Exception as e:
        db_action.log = f"Failed to execute manual resolution: {e}"
        db_action.status = "Failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Manual execution failed: {e}")
        
    db_action.status = "Success"
    db_action.log = f"Manual resolution action executed successfully by Engineer. Health restored."
    
    # 2. Store the resolution in Qdrant Vector Memory!
    memory.store_memory(
        db=db,
        title=incident.title,
        symptoms=incident.symptoms,
        affected_services=incident.affected_services,
        root_cause=root_cause,
        resolution=resolution,
        actions_executed=[action_type],
        success_rate=1.0
    )
    
    # 3. Close the Incident
    incident.status = "Closed"
    incident.resolved_at = datetime.datetime.utcnow()
    incident.resolution_type = "human"
    db.commit()
    db.refresh(incident)
    
    # Also log a system event
    log = models.ServiceLog(
        service_name=service_name,
        level="INFO",
        message=f"Incident '{incident.title}' resolved manually by Engineer. Vector memory stored.",
        timestamp=datetime.datetime.utcnow()
    )
    db.add(log)
    db.commit()
    
    return incident
