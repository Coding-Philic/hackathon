import datetime
import random
import logging
import threading
import time
from sqlalchemy.orm import Session
try:
    from backend.database import SessionLocal
    from backend import models
except ImportError:
    from database import SessionLocal
    import models

logger = logging.getLogger(__name__)

# Service list definition
DEFAULT_SERVICES = [
    {
        "service_name": "Lab Service",
        "status": "Running",
        "health_score": 100,
        "uptime": 0,
        "error_count": 0
    },
    {
        "service_name": "Authentication Service",
        "status": "Running",
        "health_score": 100,
        "uptime": 0,
        "error_count": 0
    },
    {
        "service_name": "Billing Service",
        "status": "Running",
        "health_score": 100,
        "uptime": 0,
        "error_count": 0
    },
    {
        "service_name": "Pharmacy Service",
        "status": "Running",
        "health_score": 100,
        "uptime": 0,
        "error_count": 0
    },
    {
        "service_name": "Database Service",
        "status": "Running",
        "health_score": 100,
        "uptime": 0,
        "error_count": 0
    },
    {
        "service_name": "API Gateway",
        "status": "Running",
        "health_score": 100,
        "uptime": 0,
        "error_count": 0
    }
]

def init_services(db: Session):
    """Seed services if database is empty."""
    for service_data in DEFAULT_SERVICES:
        exists = db.query(models.Service).filter_by(service_name=service_data["service_name"]).first()
        if not exists:
            db_service = models.Service(
                service_name=service_data["service_name"],
                status=service_data["status"],
                health_score=service_data["health_score"],
                uptime=service_data["uptime"],
                error_count=service_data["error_count"],
                last_restart=datetime.datetime.utcnow()
            )
            db.add(db_service)
            
            # Add initial log
            log = models.ServiceLog(
                service_name=service_data["service_name"],
                level="INFO",
                message=f"Service {service_data['service_name']} initialized.",
                timestamp=datetime.datetime.utcnow()
            )
            db.add(log)
    db.commit()

# --- SERVICE CONTROLLER LAYER FUNCTIONS ---

def get_service_status(db: Session, name: str) -> models.Service:
    return db.query(models.Service).filter_by(service_name=name).first()

def start_service(db: Session, name: str) -> models.Service:
    service = get_service_status(db, name)
    if service:
        service.status = "Running"
        service.health_score = 100
        service.error_count = 0
        service.last_restart = datetime.datetime.utcnow()
        
        log = models.ServiceLog(
            service_name=name,
            level="INFO",
            message=f"Service started by controller.",
            timestamp=datetime.datetime.utcnow()
        )
        db.add(log)
        db.commit()
        db.refresh(service)
    return service

def stop_service(db: Session, name: str) -> models.Service:
    service = get_service_status(db, name)
    if service:
        service.status = "Stopped"
        service.health_score = 0
        service.error_count += 1
        
        log = models.ServiceLog(
            service_name=name,
            level="CRITICAL",
            message=f"Service stopped (Failure detected).",
            timestamp=datetime.datetime.utcnow()
        )
        db.add(log)
        db.commit()
        db.refresh(service)
    return service

def restart_service(db: Session, name: str) -> models.Service:
    service = get_service_status(db, name)
    if service:
        service.status = "Running"
        service.health_score = 100
        service.error_count = 0
        service.last_restart = datetime.datetime.utcnow()
        
        log = models.ServiceLog(
            service_name=name,
            level="INFO",
            message=f"Service restarted successfully.",
            timestamp=datetime.datetime.utcnow()
        )
        db.add(log)
        db.commit()
        db.refresh(service)
    return service

def degrade_service(db: Session, name: str, health_score: int, reason: str) -> models.Service:
    service = get_service_status(db, name)
    if service:
        service.status = "Degraded"
        service.health_score = max(0, min(99, health_score))
        service.error_count += 1
        
        log = models.ServiceLog(
            service_name=name,
            level="ERROR",
            message=f"Service performance degraded: {reason}.",
            timestamp=datetime.datetime.utcnow()
        )
        db.add(log)
        db.commit()
        db.refresh(service)
    return service

def recover_service(db: Session, name: str) -> models.Service:
    service = get_service_status(db, name)
    if service:
        service.status = "Running"
        service.health_score = 100
        service.error_count = 0
        
        log = models.ServiceLog(
            service_name=name,
            level="INFO",
            message=f"Service performance recovered to normal.",
            timestamp=datetime.datetime.utcnow()
        )
        db.add(log)
        db.commit()
        db.refresh(service)
    return service

def health_check(db: Session, name: str) -> dict:
    service = get_service_status(db, name)
    if not service:
        return {"service_name": name, "status": "Unknown", "health_score": 0}
    
    # Random chance of throwing warnings if degraded
    if service.status == "Degraded":
        warning_msg = random.choice([
            "CPU utilization exceeded 85%.",
            "Slow response times detected in external database query.",
            "Queue lag is growing."
        ])
        log = models.ServiceLog(
            service_name=name,
            level="WARNING",
            message=warning_msg,
            timestamp=datetime.datetime.utcnow()
        )
        db.add(log)
        db.commit()
        
    return {
        "service_name": service.service_name,
        "status": service.status,
        "health_score": service.health_score,
        "uptime": service.uptime,
        "error_count": service.error_count
    }

# --- SIMULATED BACKGROUND THREAD ENGINE ---

stop_simulator_flag = False

def run_simulation_loop():
    """Runs a background loop that updates uptime and inserts periodic standard logs."""
    global stop_simulator_flag
    while not stop_simulator_flag:
        time.sleep(5)
        db = SessionLocal()
        try:
            services = db.query(models.Service).all()
            if not services:
                init_services(db)
                continue
                
            for service in services:
                if service.status == "Running":
                    service.uptime += 5
                    # Randomly log operational info (10% chance)
                    if random.random() < 0.1:
                        messages = {
                            "Lab Service": "Lab test requests processed successfully.",
                            "Authentication Service": "User session token validated successfully.",
                            "Billing Service": "Payment transactions processed.",
                            "Pharmacy Service": "Pharmacy inventory synchronized with vendor API.",
                            "Database Service": "Database connection pool healthy. Active connections: 4.",
                            "API Gateway": "Routing API requests smoothly."
                        }
                        log = models.ServiceLog(
                            service_name=service.service_name,
                            level="INFO",
                            message=messages.get(service.service_name, "Operational status normal."),
                            timestamp=datetime.datetime.utcnow()
                        )
                        db.add(log)
                elif service.status == "Degraded":
                    service.uptime += 5
                    # 30% chance to log error detail
                    if random.random() < 0.3:
                        log = models.ServiceLog(
                            service_name=service.service_name,
                            level="ERROR",
                            message=f"Performance latency high. Active thread count: {random.randint(80, 150)}",
                            timestamp=datetime.datetime.utcnow()
                        )
                        db.add(log)
                else: # Stopped
                    if random.random() < 0.3:
                        log = models.ServiceLog(
                            service_name=service.service_name,
                            level="CRITICAL",
                            message=f"Service unavailable. Connection refused.",
                            timestamp=datetime.datetime.utcnow()
                        )
                        db.add(log)
            db.commit()
        except Exception as e:
            logger.error(f"Error in simulator background loop: {e}")
        finally:
            db.close()

def start_simulator():
    global stop_simulator_flag
    stop_simulator_flag = False
    thread = threading.Thread(target=run_simulation_loop, daemon=True)
    thread.start()
    return thread

# --- INCIDENT INJECTION ENGINE FOR DEMOS ---

def inject_incident(db: Session, title: str, symptoms: str, affected_services: str, severity: str = "High") -> models.Incident:
    """Injects an incident and updates the affected service state to Stopped or Degraded."""
    # Split affected services
    services_list = [s.strip() for s in affected_services.split(",")]
    
    # Degrade/Stop the services
    for s_name in services_list:
        service = get_service_status(db, s_name)
        if service:
            if "Database" in title or "Timeout" in title or "Connection" in title:
                degrade_service(db, s_name, 20, "Database connection timeout")
            elif "Auth" in title or "Login" in title:
                degrade_service(db, s_name, 10, "Token verification failed repeatedly")
            else:
                stop_service(db, s_name)
    
    # Create incident row
    db_incident = models.Incident(
        title=title,
        symptoms=symptoms,
        affected_services=affected_services,
        status="Open",
        severity=severity,
        created_at=datetime.datetime.utcnow()
    )
    db.add(db_incident)
    db.commit()
    db.refresh(db_incident)
    
    # Log incident creation
    for s_name in services_list:
        log = models.ServiceLog(
            service_name=s_name,
            level="CRITICAL",
            message=f"Incident '{title}' reported. Health degraded.",
            timestamp=datetime.datetime.utcnow()
        )
        db.add(log)
    db.commit()
    
    return db_incident
