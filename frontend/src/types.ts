export interface Service {
  id: number;
  service_name: string;
  status: 'Running' | 'Stopped' | 'Degraded';
  health_score: number;
  uptime: number;
  error_count: number;
  last_restart: string;
}

export interface IncidentAction {
  id: number;
  incident_id: number;
  action_type: string;
  command: string;
  status: 'Pending' | 'Executing' | 'Success' | 'Failed';
  log: string | null;
  executed_at: string;
}

export interface AgentDecision {
  id: number;
  incident_id: number;
  reasoning: string;
  confidence: number;
  actions_proposed: string;
  action_selected: string;
  status: 'Proposed' | 'Executed' | 'Success' | 'Failed' | 'Escalated';
  timestamp: string;
}

export interface Incident {
  id: number;
  title: string;
  symptoms: string;
  affected_services: string;
  status: 'Open' | 'Investigating' | 'Resolving' | 'Closed' | 'Escalated';
  severity: 'Low' | 'Medium' | 'High' | 'Critical';
  created_at: string;
  resolved_at: string | null;
  resolution_type: 'human' | 'autonomous' | 'none' | null;
  actions: IncidentAction[];
  decisions: AgentDecision[];
}

export interface MemoryEntry {
  id: number;
  title: string;
  symptoms: string;
  affected_services: string;
  root_cause: string;
  resolution: string;
  actions_executed: string;
  success_rate: number;
  vector_id: string | null;
  timestamp: string;
}

export interface ServiceLog {
  id: number;
  service_name: string;
  level: 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
  message: string;
  timestamp: string;
}

export interface SystemHealthOverview {
  total_incidents: number;
  resolved_incidents: number;
  autonomous_resolutions: number;
  human_escalations: number;
  avg_resolution_time_sec: number;
  memory_growth_count: number;
  recommendation_accuracy: number;
  agent_success_rate: number;
  most_common_failures: { service: string; count: number }[];
}
