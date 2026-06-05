import datetime
import logging
from typing import TypedDict, List, Dict, Any, Optional
from sqlalchemy.orm import Session
from langgraph.graph import StateGraph, END

try:
    from backend.config import settings
    from backend import models
    from backend import simulator
    from backend import memory
    from backend.database import SessionLocal
except ImportError:
    from config import settings
    import models
    import simulator
    import memory
    from database import SessionLocal

logger = logging.getLogger(__name__)

# --- AGENT STATE SPECIFICATION ---
class AgentState(TypedDict):
    db: Session
    incident_id: int
    title: str
    symptoms: str
    affected_services: List[str]
    status: str
    severity: str
    memory_matches: List[Dict[str, Any]]
    proposed_plan: Optional[Dict[str, Any]]
    executed_actions: List[Dict[str, Any]]
    retry_count: int
    escalate: bool
    reasoning: str
    confidence: float

# --- LOCAL RULE-BASED DIAGNOSTICS (SRE KNOWLEDGE BASE) ---
# Used as fallback or when LLM_PROVIDER is "mock" to provide realistic SRE diagnosis
DIAGNOSTIC_RULES = [
    {
        "keywords": ["lab", "report", "generating"],
        "root_cause": "A file descriptor leak in the report generation queue caused the service worker to freeze.",
        "resolution": "Restart the Lab Service to flush file handles and clean the cache directory.",
        "action_type": "Restart Service",
        "service": "Lab Service",
        "command": "restart_service"
    },
    {
        "keywords": ["login", "auth", "credential", "verification"],
        "root_cause": "Session token synchronization buffer overflowed due to high traffic volume, locking login threads.",
        "resolution": "Reset session controller memory cache and clear Authentication session logs.",
        "action_type": "Reset Authentication",
        "service": "Authentication Service",
        "command": "restart_service"
    },
    {
        "keywords": ["billing", "payment", "invoice"],
        "root_cause": "Database lock contention on active invoices table halted the processing thread pool.",
        "resolution": "Clear active transaction queues and re-establish Database Service connection pool.",
        "action_type": "Reconnect Database",
        "service": "Billing Service",
        "command": "recover_service"
    },
    {
        "keywords": ["db", "database", "sql", "refused"],
        "root_cause": "Database connection pool saturated by unindexed query spikes on medical chart tables.",
        "resolution": "Flush connection pool, clear active queries, and recycle Database Service container.",
        "action_type": "Reconnect Database",
        "service": "Database Service",
        "command": "restart_service"
    },
    {
        "keywords": ["gateway", "api", "route", "timeout"],
        "root_cause": "API Gateway routing table got desynchronized during an internal network socket flap.",
        "resolution": "Reload API Gateway configuration routing maps and run service status check.",
        "action_type": "Restart Service",
        "service": "API Gateway",
        "command": "restart_service"
    },
    {
        "keywords": ["pharmacy", "inventory", "prescription"],
        "root_cause": "Vendor inventory synchronization API returned recurring timeouts, causing backoff loop starvation.",
        "resolution": "Recover Pharmacy Service backoff queue and switch to backup inventory caching server.",
        "action_type": "Enable Backup Service",
        "service": "Pharmacy Service",
        "command": "recover_service"
    }
]

def analyze_incident_details(title: str, symptoms: str) -> Dict[str, Any]:
    """Pattern matching diagnosis that matches SRE rules."""
    text = (title + " " + symptoms).lower()
    for rule in DIAGNOSTIC_RULES:
        if any(kw in text for kw in rule["keywords"]):
            return rule
            
    # Default fallback SRE diagnosis
    return {
        "root_cause": "Unknown system performance degradation. Potential microservice socket disconnect.",
        "resolution": "Execute service restart of all affected modules and perform dependency check.",
        "action_type": "Restart Service",
        "service": title.split()[0] if title else "API Gateway",
        "command": "restart_service"
    }

# --- LANGGRAPH GRAPH NODES ---

def node_analyze_incident(state: AgentState) -> Dict[str, Any]:
    """Analyzes symptoms and isolates affected microservices."""
    logger.info(f"Node: Analyze Incident {state['incident_id']}")
    
    # Update incident state in DB
    db = state["db"]
    incident = db.query(models.Incident).filter_by(id=state["incident_id"]).first()
    if incident:
        incident.status = "Investigating"
        db.commit()
        
    return {
        "status": "Investigating",
        "reasoning": f"Analyzing symptoms: '{state['symptoms']}'. Affected services isolated: {state['affected_services']}."
    }

def node_search_memory(state: AgentState) -> Dict[str, Any]:
    """Queries Qdrant vector database for historical memories of similar incidents."""
    logger.info("Node: Search Memory")
    db = state["db"]
    
    # Perform similarity search
    matches = memory.search_memories(db, state["title"], state["symptoms"], limit=5)
    
    # Log memory search results
    logger.info(f"Found {len(matches)} historical incident memories.")
    return {"memory_matches": matches}

def node_evaluate_matches(state: AgentState) -> Dict[str, Any]:
    """Evaluates memory matches and determines if we can act autonomously."""
    logger.info("Node: Evaluate Matches")
    matches = state["memory_matches"]
    
    # We look for a highly confident match (similarity score >= 0.70 or overlap)
    best_match = None
    if matches:
        # Check if best match is above threshold
        first_match = matches[0]
        # In mock vector mode, similarity score is 'score' (which goes up to 1.0)
        # We check if the score is high enough
        score = first_match.get("score", 0.0)
        if score >= 0.70:
            best_match = first_match
            
    if best_match:
        reasoning = f"Retrieved historical incident match: '{best_match['title']}' (Confidence: {int(best_match['score']*100)}%). Retrieving resolution plan: '{best_match['resolution']}'."
        confidence = best_match["score"]
        proposed_plan = {
            "root_cause": best_match["root_cause"],
            "resolution": best_match["resolution"],
            "action_type": best_match["actions_executed"][0] if best_match["actions_executed"] else "Restart Service",
            "service": best_match["affected_services"].split(",")[0],
            "command": "restart_service" if "restart" in best_match["resolution"].lower() else "recover_service",
            "is_autonomous": True
        }
        escalate = False
    else:
        # First-time Incident Flow
        reasoning = "No historical incident memory matches found in vector DB. Analyzing symptoms from telemetry logs."
        confidence = 0.40 # low confidence for new incidents
        proposed_plan = None
        escalate = True # Escalate to engineer for manual resolution!
        
    return {
        "reasoning": reasoning,
        "confidence": confidence,
        "proposed_plan": proposed_plan,
        "escalate": escalate
    }

def node_generate_plan(state: AgentState) -> Dict[str, Any]:
    """Generates the resolution plan (either autonomous or recommending an engineer fix)."""
    logger.info("Node: Generate Plan")
    db = state["db"]
    
    if state["proposed_plan"]:
        # We already have an autonomous plan from memory!
        plan = state["proposed_plan"]
    else:
        # No memory found. We perform investigation & suggest root cause for the Engineer.
        analysis = analyze_incident_details(state["title"], state["symptoms"])
        plan = {
            "root_cause": analysis["root_cause"],
            "resolution": analysis["resolution"],
            "action_type": analysis["action_type"],
            "service": analysis["service"],
            "command": analysis["command"],
            "is_autonomous": False
        }
        
    # Write Agent Decision to database
    decision = models.AgentDecision(
        incident_id=state["incident_id"],
        reasoning=state["reasoning"],
        confidence=state["confidence"],
        actions_proposed=plan["resolution"],
        action_selected=plan["action_type"] if plan["is_autonomous"] else "Escalate to Human SRE",
        status="Proposed" if plan["is_autonomous"] else "Escalated",
        timestamp=datetime.datetime.utcnow()
    )
    db.add(decision)
    db.commit()
    
    return {"proposed_plan": plan}

def node_execute_action(state: AgentState) -> Dict[str, Any]:
    """Executes the recovery action via the Service Controller Engine."""
    logger.info("Node: Execute Action")
    db = state["db"]
    plan = state["proposed_plan"]
    
    if state["escalate"]:
        # If marked for escalation, we skip autonomous execution and alert engineer
        return {"status": "Escalated"}
        
    service_name = plan["service"]
    command_name = plan["command"]
    action_type = plan["action_type"]
    
    # Create action row in postgres (executing status)
    db_action = models.IncidentAction(
        incident_id=state["incident_id"],
        action_type=action_type,
        command=f"{command_name}('{service_name}')",
        status="Executing",
        executed_at=datetime.datetime.utcnow()
    )
    db.add(db_action)
    db.commit()
    db.refresh(db_action)
    
    # Call service controller
    log_content = ""
    success = False
    try:
        if command_name == "restart_service":
            simulator.restart_service(db, service_name)
            log_content = f"Restart signal sent to {service_name}. PID re-assigned. Port binding successful."
            success = True
        elif command_name == "recover_service":
            simulator.recover_service(db, service_name)
            log_content = f"Recovery routine run on {service_name}. Connection pooling re-synchronized."
            success = True
        else:
            simulator.start_service(db, service_name)
            log_content = f"Start signal sent to {service_name}."
            success = True
    except Exception as e:
        log_content = f"Service controller execution error: {str(e)}"
        success = False
        
    db_action.status = "Success" if success else "Failed"
    db_action.log = log_content
    db.commit()
    
    # Record action executed
    actions = list(state["executed_actions"])
    actions.append({
        "action_id": db_action.id,
        "action_type": action_type,
        "status": db_action.status,
        "service": service_name
    })
    
    # Update incident status to Resolving
    incident = db.query(models.Incident).filter_by(id=state["incident_id"]).first()
    if incident:
        incident.status = "Resolving"
        db.commit()
        
    return {
        "executed_actions": actions,
        "status": "Resolving",
        "reasoning": f"Executed action '{action_type}' autonomously on '{service_name}'."
    }

def node_verify_status(state: AgentState) -> Dict[str, Any]:
    """Verifies service health after recovery action execution."""
    logger.info("Node: Verify Status")
    db = state["db"]
    plan = state["proposed_plan"]
    
    service_name = plan["service"]
    # Check current status
    service = db.query(models.Service).filter_by(service_name=service_name).first()
    
    is_healthy = False
    if service:
        # Service must be Running and health score must be high
        is_healthy = (service.status == "Running" and service.health_score >= 80)
        
    if is_healthy:
        # Success!
        logger.info(f"Verification Success for service {service_name}.")
        incident = db.query(models.Incident).filter_by(id=state["incident_id"]).first()
        if incident:
            incident.status = "Closed"
            incident.resolved_at = datetime.datetime.utcnow()
            incident.resolution_type = "autonomous"
            db.commit()
            
        # Update agent decision status
        decision = db.query(models.AgentDecision).filter_by(incident_id=state["incident_id"]).order_by(models.AgentDecision.id.desc()).first()
        if decision:
            decision.status = "Success"
            db.commit()
            
        return {
            "status": "Closed",
            "reasoning": f"Service '{service_name}' health verified successfully. Health score: {service.health_score}."
        }
    else:
        # Failure. We trigger a retry or escalate
        new_retry = state["retry_count"] + 1
        logger.warning(f"Verification Failed for {service_name}. Retry attempt {new_retry}.")
        
        if new_retry <= 1:
            # We retry once
            return {
                "retry_count": new_retry,
                "reasoning": f"Verification failed. Health score remaining at {service.health_score if service else 0}. Scheduling retry execution."
            }
        else:
            # Escalated after retry
            return {
                "retry_count": new_retry,
                "escalate": True,
                "reasoning": f"Verification failed after retry. Health score remains low ({service.health_score if service else 0}). Escalating to human SRE."
            }

def node_escalate_to_engineer(state: AgentState) -> Dict[str, Any]:
    """Escalates incident to human engineers."""
    logger.info("Node: Escalate to Engineer")
    db = state["db"]
    
    incident = db.query(models.Incident).filter_by(id=state["incident_id"]).first()
    if incident:
        incident.status = "Escalated"
        db.commit()
        
    decision = db.query(models.AgentDecision).filter_by(incident_id=state["incident_id"]).order_by(models.AgentDecision.id.desc()).first()
    if decision:
        decision.status = "Failed" if state["retry_count"] > 0 else "Escalated"
        db.commit()
        
    return {
        "status": "Escalated",
        "reasoning": f"Incident escalated to human operations team. Reason: {state['reasoning']}"
    }

def node_save_resolution_memory(state: AgentState) -> Dict[str, Any]:
    """Saves the resolution mapping to vector memory on successful autonomous recovery."""
    logger.info("Node: Save Resolution Memory")
    db = state["db"]
    plan = state["proposed_plan"]
    
    # Save the resolution memory back to database & Qdrant
    # This cements the SRE's self-learning capability
    memory.store_memory(
        db=db,
        title=state["title"],
        symptoms=state["symptoms"],
        affected_services=",".join(state["affected_services"]),
        root_cause=plan["root_cause"],
        resolution=plan["resolution"],
        actions_executed=[plan["action_type"]],
        success_rate=1.0
    )
    
    return {"reasoning": "Incident closed successfully. Resolution details persisted to Qdrant vector memory."}

# --- LANGGRAPH WORKFLOW ROUTING LOGIC ---

def route_eval(state: AgentState) -> str:
    """Routes after Evaluating Memory Matches."""
    if state["escalate"]:
        return "escalate"
    return "act"

def route_verify(state: AgentState) -> str:
    """Routes after Verification checks."""
    if state["status"] == "Closed":
        return "close"
    elif state["escalate"]:
        return "escalate"
    else:
        return "retry"

# --- COMPILE STATE GRAPH ---

def build_sre_agent_graph():
    workflow = StateGraph(AgentState)
    
    # Register Nodes
    workflow.add_node("analyze", node_analyze_incident)
    workflow.add_node("search_memory", node_search_memory)
    workflow.add_node("evaluate", node_evaluate_matches)
    workflow.add_node("plan", node_generate_plan)
    workflow.add_node("execute", node_execute_action)
    workflow.add_node("verify", node_verify_status)
    workflow.add_node("escalate_incident", node_escalate_to_engineer)
    workflow.add_node("save_memory", node_save_resolution_memory)
    
    # Set Entry Point
    workflow.set_entry_point("analyze")
    
    # Define Edges
    workflow.add_edge("analyze", "search_memory")
    workflow.add_edge("search_memory", "evaluate")
    workflow.add_edge("evaluate", "plan")
    
    # Conditional Routing from Plan
    workflow.add_conditional_edges(
        "plan",
        route_eval,
        {
            "escalate": "escalate_incident",
            "act": "execute"
        }
    )
    
    workflow.add_edge("execute", "verify")
    
    # Conditional Routing from Verify
    workflow.add_conditional_edges(
        "verify",
        route_verify,
        {
            "close": "save_memory",
            "escalate": "escalate_incident",
            "retry": "execute"  # Loop back for retry
        }
    )
    
    workflow.add_edge("save_memory", END)
    workflow.add_edge("escalate_incident", END)
    
    return workflow.compile()

# Instantiated Agent Graph Runner
sre_agent = build_sre_agent_graph()

def run_agent_on_incident(db: Session, incident_id: int):
    """Entrypoint function to execute the full LangGraph SRE agent loop on an incident."""
    incident = db.query(models.Incident).filter_by(id=incident_id).first()
    if not incident:
        logger.error(f"Incident with ID {incident_id} not found.")
        return
        
    # Build Initial State
    initial_state: AgentState = {
        "db": db,
        "incident_id": incident.id,
        "title": incident.title,
        "symptoms": incident.symptoms,
        "affected_services": [s.strip() for s in incident.affected_services.split(",")],
        "status": incident.status,
        "severity": incident.severity,
        "memory_matches": [],
        "proposed_plan": None,
        "executed_actions": [],
        "retry_count": 0,
        "escalate": False,
        "reasoning": "Starting agent investigation.",
        "confidence": 0.0
    }
    
    # Execute Graph
    logger.info(f"Triggering LangGraph agent loop for incident: '{incident.title}'")
    sre_agent.invoke(initial_state)
    logger.info(f"Finished agent loop for incident {incident_id}.")
