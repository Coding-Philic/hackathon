from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List

try:
    from backend.database import get_db
    from backend import models, schemas, simulator
except ImportError:
    from database import get_db
    import models, schemas, simulator

router = APIRouter(prefix="/services", tags=["Services"])

@router.get("/", response_model=List[schemas.ServiceInDB])
def list_services(db: Session = Depends(get_db)):
    services = db.query(models.Service).all()
    # If not seeded, initialize them
    if not services:
        simulator.init_services(db)
        services = db.query(models.Service).all()
    return services

@router.get("/{name}", response_model=schemas.ServiceInDB)
def get_service(name: str, db: Session = Depends(get_db)):
    service = db.query(models.Service).filter_by(service_name=name).first()
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found.")
    return service

@router.post("/{name}/start", response_model=schemas.ServiceInDB)
def start_service_api(name: str, db: Session = Depends(get_db)):
    service = simulator.start_service(db, name)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found.")
    return service

@router.post("/{name}/stop", response_model=schemas.ServiceInDB)
def stop_service_api(name: str, db: Session = Depends(get_db)):
    service = simulator.stop_service(db, name)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found.")
    return service

@router.post("/{name}/restart", response_model=schemas.ServiceInDB)
def restart_service_api(name: str, db: Session = Depends(get_db)):
    service = simulator.restart_service(db, name)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found.")
    return service

@router.post("/{name}/degrade", response_model=schemas.ServiceInDB)
def degrade_service_api(
    name: str, 
    health_score: int = Body(..., embed=True), 
    reason: str = Body(..., embed=True), 
    db: Session = Depends(get_db)
):
    service = simulator.degrade_service(db, name, health_score, reason)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found.")
    return service

@router.post("/{name}/recover", response_model=schemas.ServiceInDB)
def recover_service_api(name: str, db: Session = Depends(get_db)):
    service = simulator.recover_service(db, name)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found.")
    return service

@router.post("/{name}/health-check")
def check_health_api(name: str, db: Session = Depends(get_db)):
    result = simulator.health_check(db, name)
    if result["status"] == "Unknown":
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found.")
    return result

@router.get("/{name}/logs", response_model=List[schemas.ServiceLogInDB])
def get_service_logs(name: str, limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(models.ServiceLog)\
        .filter_by(service_name=name)\
        .order_by(models.ServiceLog.timestamp.desc())\
        .limit(limit)\
        .all()
    return logs
