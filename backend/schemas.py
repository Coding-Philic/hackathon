from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Service Schemas
class ServiceBase(BaseModel):
    service_name: str
    status: str
    health_score: int
    uptime: int
    error_count: int
    last_restart: datetime

class ServiceCreate(ServiceBase):
    pass

class ServiceUpdate(BaseModel):
    status: Optional[str] = None
    health_score: Optional[int] = None
    uptime: Optional[int] = None
    error_count: Optional[int] = None
    last_restart: Optional[datetime] = None

class ServiceInDB(ServiceBase):
    id: int
    
    class Config:
        from_attributes = True

# Incident Action Schemas
class IncidentActionBase(BaseModel):
    action_type: str
    command: str
    status: str
    log: Optional[str] = None
    executed_at: datetime

class IncidentActionCreate(BaseModel):
    action_type: str
    command: str
    status: str = "Pending"
    log: Optional[str] = None

class IncidentActionInDB(IncidentActionBase):
    id: int
    incident_id: int
    
    class Config:
        from_attributes = True

# Agent Decision Schemas
class AgentDecisionBase(BaseModel):
    reasoning: str
    confidence: float
    actions_proposed: str
    action_selected: str
    status: str
    timestamp: datetime

class AgentDecisionCreate(BaseModel):
    reasoning: str
    confidence: float
    actions_proposed: str
    action_selected: str
    status: str = "Proposed"

class AgentDecisionInDB(AgentDecisionBase):
    id: int
    incident_id: int
    
    class Config:
        from_attributes = True

# Incident Schemas
class IncidentBase(BaseModel):
    title: str
    symptoms: str
    affected_services: str
    status: str
    severity: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolution_type: Optional[str] = None

class IncidentCreate(BaseModel):
    title: str
    symptoms: str
    affected_services: str
    severity: str = "High"

class IncidentUpdate(BaseModel):
    status: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_type: Optional[str] = None

class IncidentInDB(IncidentBase):
    id: int
    actions: List[IncidentActionInDB] = []
    decisions: List[AgentDecisionInDB] = []
    
    class Config:
        from_attributes = True

# Memory Entry Schemas
class MemoryEntryBase(BaseModel):
    title: str
    symptoms: str
    affected_services: str
    root_cause: str
    resolution: str
    actions_executed: str
    success_rate: float
    vector_id: Optional[str] = None
    timestamp: datetime

class MemoryEntryCreate(BaseModel):
    title: str
    symptoms: str
    affected_services: str
    root_cause: str
    resolution: str
    actions_executed: str
    success_rate: float = 1.0

class MemoryEntryInDB(MemoryEntryBase):
    id: int
    
    class Config:
        from_attributes = True

# Service Log Schemas
class ServiceLogBase(BaseModel):
    service_name: str
    level: str
    message: str
    timestamp: datetime

class ServiceLogInDB(ServiceLogBase):
    id: int
    
    class Config:
        from_attributes = True

# Custom response schemas for UI
class SystemHealthOverview(BaseModel):
    total_incidents: int
    resolved_incidents: int
    autonomous_resolutions: int
    human_escalations: int
    avg_resolution_time_sec: float
    memory_growth_count: int
    recommendation_accuracy: float
    agent_success_rate: float
    most_common_failures: List[dict]
