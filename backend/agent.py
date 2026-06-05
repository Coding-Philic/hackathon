import json
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


# ---------------------------------------------------------------------------
# LOCAL RULE-BASED DIAGNOSTICS — used as fallback in mock mode or on LLM error
# ---------------------------------------------------------------------------
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

def _rule_based_analyze(title: str, symptoms: str) -> Dict[str, Any]:
    """Keyword-matching fallback used by mock mode and as LLM error recovery."""
    text = (title + " " + symptoms).lower()
    for rule in DIAGNOSTIC_RULES:
        if any(kw in text for kw in rule["keywords"]):
            return rule
    return {
        "root_cause": "Unknown system performance degradation. Potential microservice socket disconnect.",
        "resolution": "Execute service restart of all affected modules and perform dependency check.",
        "action_type": "Restart Service",
        "service": title.split()[0] if title else "API Gateway",
        "command": "restart_service"
    }


# ---------------------------------------------------------------------------
# LLM GATEWAY — transparently handles OpenAI / Gemini / mock
# ---------------------------------------------------------------------------

def call_llm(prompt: str, system_prompt: str = "") -> str:
    """
    Sends a prompt to the configured LLM and returns the raw text response.
    Falls back to an empty string on failure so callers can handle gracefully.
    """
    provider = settings.LLM_PROVIDER

    if provider == "openai" and settings.OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.2,
                max_tokens=800,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"OpenAI call failed: {e}")
            return ""

    elif provider == "gemini" and settings.GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=system_prompt if system_prompt else None
            )
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.warning(f"Gemini call failed: {e}")
            return ""

    # mock / unknown provider — return empty string to trigger rule-based fallback
    return ""


def _parse_json_from_llm(raw: str) -> Optional[Dict]:
    """Safely extracts a JSON object from an LLM response (handles markdown fences)."""
    if not raw:
        return None
    # Strip markdown code fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find the first { ... } block
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start:end])
            except json.JSONDecodeError:
                pass
    logger.warning(f"Could not parse JSON from LLM response: {raw[:200]}")
    return None


# ---------------------------------------------------------------------------
# LLM-POWERED ANALYSIS HELPERS (used inside nodes)
# ---------------------------------------------------------------------------

SYSTEM_SRE = (
    "You are an expert Site Reliability Engineer (SRE) AI for a hospital IT platform. "
    "You reason carefully about microservice incidents and respond ONLY with valid JSON. "
    "Never include markdown, explanations, or extra text outside the JSON object."
)

def llm_triage_incident(title: str, symptoms: str) -> Dict[str, Any]:
    """
    Calls the LLM to perform incident triage.
    Returns: { root_cause, resolution, action_type, service, command, reasoning }
    Falls back to rule-based on LLM failure or mock mode.
    """
    prompt = f"""You are triaging a hospital microservice incident.

Incident Title: {title}
Symptoms: {symptoms}

Available services: Lab Service, Authentication Service, Billing Service, Pharmacy Service, Database Service, API Gateway.
Available commands: restart_service, recover_service.

Respond with a single JSON object:
{{
  "root_cause": "A concise technical root cause in 1-2 sentences.",
  "resolution": "Step-by-step resolution plan in 1-2 sentences.",
  "action_type": "One of: Restart Service | Reset Authentication | Reconnect Database | Enable Backup Service",
  "service": "Exact name of the primary affected service from the list above.",
  "command": "restart_service or recover_service",
  "reasoning": "Your internal SRE chain-of-thought in 2-3 sentences explaining why you diagnosed this."
}}"""

    raw = call_llm(prompt, system_prompt=SYSTEM_SRE)
    parsed = _parse_json_from_llm(raw)

    if parsed and all(k in parsed for k in ("root_cause", "resolution", "action_type", "service", "command")):
        logger.info(f"LLM triage successful for '{title}'")
        return parsed

    # Fallback to rule-based
    logger.info(f"Using rule-based fallback for triage of '{title}'")
    rule = _rule_based_analyze(title, symptoms)
    rule["reasoning"] = (
        f"No LLM provider active (mode: {settings.LLM_PROVIDER}). "
        f"Rule-based diagnosis: symptoms match pattern for {rule['service']}."
    )
    return rule


def llm_evaluate_memory_matches(
    title: str, symptoms: str, matches: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calls the LLM to decide whether memory matches are sufficient for autonomous action.
    Returns: { should_act: bool, confidence: float, reasoning: str, best_match_index: int }
    Falls back to threshold-based rule if LLM unavailable.
    """
    if not matches:
        return {
            "should_act": False,
            "confidence": 0.30,
            "reasoning": "No historical incident memories found in vector database. First-time occurrence — escalating to human SRE for manual investigation and resolution.",
            "best_match_index": -1
        }

    # Summarise top-3 matches for the LLM
    match_summary = ""
    for i, m in enumerate(matches[:3]):
        match_summary += (
            f"\n[Match {i}] Title: {m['title']} | Score: {m.get('score', 0):.2f}\n"
            f"  Symptoms: {m['symptoms']}\n"
            f"  Root Cause: {m['root_cause']}\n"
            f"  Resolution: {m['resolution']}\n"
            f"  Actions: {m.get('actions_executed', [])}\n"
        )

    prompt = f"""You are an SRE AI reviewing historical incident memories for a new incident.

NEW INCIDENT
Title: {title}
Symptoms: {symptoms}

HISTORICAL MEMORY MATCHES (from Qdrant vector DB):
{match_summary}

Decide whether the new incident is similar enough to a past resolved incident to allow AUTONOMOUS action.

Respond with a single JSON object:
{{
  "should_act": true or false,
  "confidence": 0.0 to 1.0,
  "best_match_index": 0, 1, or 2 (index of the best match, or -1 if none applies),
  "reasoning": "2-3 sentences explaining your decision, mentioning specific evidence from symptoms and memory."
}}

Rules:
- should_act = true only if confidence >= 0.70
- If symptoms and match are clearly about the same service and failure mode, prefer should_act = true
- If the match is from a completely different service or failure type, should_act = false"""

    raw = call_llm(prompt, system_prompt=SYSTEM_SRE)
    parsed = _parse_json_from_llm(raw)

    if parsed and "should_act" in parsed and "confidence" in parsed:
        logger.info(f"LLM memory evaluation: should_act={parsed['should_act']}, confidence={parsed['confidence']}")
        return parsed

    # Rule-based fallback
    logger.info("Using threshold-based fallback for memory evaluation")
    best = matches[0]
    score = best.get("score", 0.0)
    if score >= 0.70:
        return {
            "should_act": True,
            "confidence": score,
            "best_match_index": 0,
            "reasoning": (
                f"Historical memory match found: '{best['title']}' "
                f"(similarity {int(score * 100)}%). Resolution: '{best['resolution']}'. "
                f"Proceeding with autonomous recovery."
            )
        }
    return {
        "should_act": False,
        "confidence": score,
        "best_match_index": -1,
        "reasoning": (
            f"Best memory match score ({int(score * 100)}%) below confidence threshold. "
            "Escalating to human SRE for manual investigation."
        )
    }


def llm_generate_plan(
    title: str, symptoms: str, best_match: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calls the LLM to generate a concrete resolution plan.
    Uses memory match as context if available, otherwise reasons from symptoms alone.
    Returns: { root_cause, resolution, action_type, service, command, is_autonomous }
    """
    if best_match:
        context = (
            f"A similar past incident was: '{best_match['title']}'\n"
            f"Past root cause: {best_match['root_cause']}\n"
            f"Past resolution: {best_match['resolution']}\n"
            f"Past actions: {best_match.get('actions_executed', [])}"
        )
    else:
        context = "No historical memory match was found. Diagnose from symptoms alone."

    prompt = f"""Generate a precise SRE resolution plan for this hospital microservice incident.

INCIDENT
Title: {title}
Symptoms: {symptoms}

MEMORY CONTEXT
{context}

Available services: Lab Service, Authentication Service, Billing Service, Pharmacy Service, Database Service, API Gateway.
Available commands: restart_service, recover_service.

Respond with a single JSON object:
{{
  "root_cause": "Technical root cause in 1-2 sentences.",
  "resolution": "Actionable resolution steps in 1-2 sentences.",
  "action_type": "One of: Restart Service | Reset Authentication | Reconnect Database | Enable Backup Service",
  "service": "Exact name of the primary affected service.",
  "command": "restart_service or recover_service",
  "is_autonomous": {str(best_match is not None).lower()}
}}"""

    raw = call_llm(prompt, system_prompt=SYSTEM_SRE)
    parsed = _parse_json_from_llm(raw)

    if parsed and all(k in parsed for k in ("root_cause", "resolution", "action_type", "service", "command")):
        # Ensure is_autonomous is set correctly
        parsed["is_autonomous"] = best_match is not None
        logger.info(f"LLM plan generated for '{title}': {parsed['action_type']} on {parsed['service']}")
        return parsed

    # Rule-based fallback
    logger.info(f"Using rule-based fallback for plan generation of '{title}'")
    rule = _rule_based_analyze(title, symptoms)
    rule["is_autonomous"] = best_match is not None
    return rule


# ---------------------------------------------------------------------------
# LANGGRAPH GRAPH NODES
# ---------------------------------------------------------------------------

def node_analyze_incident(state: AgentState) -> Dict[str, Any]:
    """Calls LLM to triage symptoms and identify the likely root cause."""
    logger.info(f"Node: Analyze Incident {state['incident_id']}")

    db = state["db"]
    incident = db.query(models.Incident).filter_by(id=state["incident_id"]).first()
    if incident:
        incident.status = "Investigating"
        db.commit()

    # LLM triage — returns reasoning even in mock mode
    triage = llm_triage_incident(state["title"], state["symptoms"])
    reasoning = triage.get(
        "reasoning",
        f"Analyzing symptoms: '{state['symptoms']}'. Affected services: {state['affected_services']}."
    )

    return {
        "status": "Investigating",
        "reasoning": reasoning,
        # Stash triage result so plan node can reuse it
        "proposed_plan": None  # will be set in generate_plan node
    }


def node_search_memory(state: AgentState) -> Dict[str, Any]:
    """Queries Qdrant vector database for historical memories of similar incidents."""
    logger.info("Node: Search Memory")
    db = state["db"]
    matches = memory.search_memories(db, state["title"], state["symptoms"], limit=5)
    logger.info(f"Found {len(matches)} historical incident memories.")
    return {"memory_matches": matches}


def node_evaluate_matches(state: AgentState) -> Dict[str, Any]:
    """LLM evaluates memory matches and decides whether to act autonomously or escalate."""
    logger.info("Node: Evaluate Matches")

    evaluation = llm_evaluate_memory_matches(
        state["title"], state["symptoms"], state["memory_matches"]
    )

    should_act = evaluation.get("should_act", False)
    confidence = evaluation.get("confidence", 0.30)
    reasoning = evaluation.get("reasoning", "")
    best_idx = evaluation.get("best_match_index", -1)

    proposed_plan = None
    if should_act and best_idx >= 0 and best_idx < len(state["memory_matches"]):
        best = state["memory_matches"][best_idx]
        proposed_plan = {
            "root_cause": best["root_cause"],
            "resolution": best["resolution"],
            "action_type": best["actions_executed"][0] if best["actions_executed"] else "Restart Service",
            "service": best["affected_services"].split(",")[0].strip(),
            "command": "restart_service" if "restart" in best["resolution"].lower() else "recover_service",
            "is_autonomous": True,
            "_best_match": best   # passed to generate_plan for LLM context
        }

    return {
        "reasoning": reasoning,
        "confidence": confidence,
        "proposed_plan": proposed_plan,
        "escalate": not should_act
    }


def node_generate_plan(state: AgentState) -> Dict[str, Any]:
    """LLM synthesises a full resolution plan from symptoms + memory context."""
    logger.info("Node: Generate Plan")
    db = state["db"]

    if state["proposed_plan"]:
        # Already have a plan from memory evaluation — let LLM refine it
        best_match = state["proposed_plan"].get("_best_match")
        plan = llm_generate_plan(state["title"], state["symptoms"], best_match)
        plan["is_autonomous"] = True
    else:
        # No match — LLM diagnoses from scratch; result will be shown to engineer
        plan = llm_generate_plan(state["title"], state["symptoms"], None)
        plan["is_autonomous"] = False

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
        return {"status": "Escalated"}

    service_name = plan["service"]
    command_name = plan["command"]
    action_type = plan["action_type"]

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

    actions = list(state["executed_actions"])
    actions.append({
        "action_id": db_action.id,
        "action_type": action_type,
        "status": db_action.status,
        "service": service_name
    })

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
    service = db.query(models.Service).filter_by(service_name=service_name).first()

    is_healthy = False
    if service:
        is_healthy = (service.status == "Running" and service.health_score >= 80)

    if is_healthy:
        logger.info(f"Verification Success for service {service_name}.")
        incident = db.query(models.Incident).filter_by(id=state["incident_id"]).first()
        if incident:
            incident.status = "Closed"
            incident.resolved_at = datetime.datetime.utcnow()
            incident.resolution_type = "autonomous"
            db.commit()

        decision = db.query(models.AgentDecision).filter_by(incident_id=state["incident_id"]).order_by(models.AgentDecision.id.desc()).first()
        if decision:
            decision.status = "Success"
            db.commit()

        return {
            "status": "Closed",
            "reasoning": f"Service '{service_name}' health verified successfully. Health score: {service.health_score}."
        }
    else:
        new_retry = state["retry_count"] + 1
        logger.warning(f"Verification Failed for {service_name}. Retry attempt {new_retry}.")

        if new_retry <= 1:
            return {
                "retry_count": new_retry,
                "reasoning": f"Verification failed. Health score: {service.health_score if service else 0}. Scheduling retry execution."
            }
        else:
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


# ---------------------------------------------------------------------------
# LANGGRAPH ROUTING
# ---------------------------------------------------------------------------

def route_eval(state: AgentState) -> str:
    return "escalate" if state["escalate"] else "act"


def route_verify(state: AgentState) -> str:
    if state["status"] == "Closed":
        return "close"
    elif state["escalate"]:
        return "escalate"
    return "retry"


# ---------------------------------------------------------------------------
# COMPILE STATE GRAPH
# ---------------------------------------------------------------------------

def build_sre_agent_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("analyze", node_analyze_incident)
    workflow.add_node("search_memory", node_search_memory)
    workflow.add_node("evaluate", node_evaluate_matches)
    workflow.add_node("plan", node_generate_plan)
    workflow.add_node("execute", node_execute_action)
    workflow.add_node("verify", node_verify_status)
    workflow.add_node("escalate_incident", node_escalate_to_engineer)
    workflow.add_node("save_memory", node_save_resolution_memory)

    workflow.set_entry_point("analyze")

    workflow.add_edge("analyze", "search_memory")
    workflow.add_edge("search_memory", "evaluate")
    workflow.add_edge("evaluate", "plan")

    workflow.add_conditional_edges(
        "plan",
        route_eval,
        {
            "escalate": "escalate_incident",
            "act": "execute"
        }
    )

    workflow.add_edge("execute", "verify")

    workflow.add_conditional_edges(
        "verify",
        route_verify,
        {
            "close": "save_memory",
            "escalate": "escalate_incident",
            "retry": "execute"
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

    provider = settings.LLM_PROVIDER
    logger.info(
        f"Triggering LangGraph SRE agent for incident: '{incident.title}' "
        f"[LLM provider: {provider}]"
    )
    sre_agent.invoke(initial_state)
    logger.info(f"Finished agent loop for incident {incident_id}.")
