import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
try:
    from backend.database import Base
except ImportError:
    from database import Base

class Service(Base):
    __tablename__ = 'services'
    
    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(String(50), default='Running') # Running, Stopped, Degraded
    health_score = Column(Integer, default=100) # 0 to 100
    uptime = Column(Integer, default=0) # in seconds
    error_count = Column(Integer, default=0)
    last_restart = Column(DateTime, default=datetime.datetime.utcnow)

class Incident(Base):
    __tablename__ = 'incidents'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    symptoms = Column(Text, nullable=False)
    affected_services = Column(String(200), nullable=False) # comma-separated
    status = Column(String(50), default='Open') # Open, Investigating, Resolving, Closed, Escalated
    severity = Column(String(50), default='High') # Low, Medium, High, Critical
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    resolution_type = Column(String(50), nullable=True) # human, autonomous, none
    
    actions = relationship("IncidentAction", back_populates="incident")
    decisions = relationship("AgentDecision", back_populates="incident")

class IncidentAction(Base):
    __tablename__ = 'incident_actions'
    
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey('incidents.id'), nullable=False)
    action_type = Column(String(100), nullable=False) # e.g. Restart Service, Reconnect Database
    command = Column(String(200), nullable=False)
    status = Column(String(50), default='Pending') # Pending, Executing, Success, Failed
    log = Column(Text, nullable=True)
    executed_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    incident = relationship("Incident", back_populates="actions")

class MemoryEntry(Base):
    __tablename__ = 'memory_entries'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    symptoms = Column(Text, nullable=False)
    affected_services = Column(String(200), nullable=False)
    root_cause = Column(Text, nullable=False)
    resolution = Column(Text, nullable=False)
    actions_executed = Column(Text, nullable=False) # comma-separated list of actions
    success_rate = Column(Float, default=1.0)
    vector_id = Column(String(100), nullable=True) # UUID in Qdrant
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class AgentDecision(Base):
    __tablename__ = 'agent_decisions'
    
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey('incidents.id'), nullable=False)
    reasoning = Column(Text, nullable=False)
    confidence = Column(Float, default=0.0) # 0.0 to 1.0
    actions_proposed = Column(Text, nullable=False)
    action_selected = Column(String(100), nullable=False)
    status = Column(String(50), default='Proposed') # Proposed, Executed, Success, Failed
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    incident = relationship("Incident", back_populates="decisions")

class ServiceLog(Base):
    __tablename__ = 'service_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String(100), nullable=False, index=True)
    level = Column(String(20), default='INFO') # INFO, WARNING, ERROR, CRITICAL
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
