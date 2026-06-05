import { useState, useEffect } from 'react';
import { Service, Incident, MemoryEntry, ServiceLog, SystemHealthOverview } from './types';
import Dashboard from './components/Dashboard';
import ServicesMonitor from './components/ServicesMonitor';
import IncidentManagement from './components/IncidentManagement';
import MemoryTimeline from './components/MemoryTimeline';
import AgentDecisions from './components/AgentDecisions';
import Analytics from './components/Analytics';
import Settings from './components/Settings';
import DemoControl from './components/DemoControl';
import { 
  Activity, Cpu, ShieldAlert, History, BrainCircuit, BarChart3, Settings as SettingsIcon, Sparkles, Radio, ShieldCheck
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const SERVICES_LIST = [
  "Lab Service",
  "Authentication Service",
  "Billing Service",
  "Pharmacy Service",
  "Database Service",
  "API Gateway"
];

const AUTO_SIM_SCENARIOS = [
  { title: "Lab Reports Not Generating", symptoms: "Doctors cannot access lab reports. Laboratory queue worker is unresponsive.", affected_services: "Lab Service", severity: "High" },
  { title: "User Login Failures", symptoms: "Nurses cannot authenticate. JWT token validation returning Error 500.", affected_services: "Authentication Service", severity: "High" },
  { title: "Billing Transactions Failing", symptoms: "Payments locked in invoice queue. Database returns transaction lock timeout.", affected_services: "Billing Service", severity: "High" },
  { title: "Database Connection Refused", symptoms: "Telemetry detects database socket refusal. Port 5432 is unresponsive.", affected_services: "Database Service", severity: "Critical" },
  { title: "API Gateway Timeout", symptoms: "Internal API calls return Gateway Timeout. Gateway routing table is corrupted.", affected_services: "API Gateway", severity: "Medium" }
];

export default function App() {
  const [activeTab, setActiveTab] = useState<string>('demo');
  const [services, setServices] = useState<Service[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [memories, setMemories] = useState<MemoryEntry[]>([]);
  const [recentLogs, setRecentLogs] = useState<ServiceLog[]>([]);
  const [analytics, setAnalytics] = useState<SystemHealthOverview>({
    total_incidents: 0,
    resolved_incidents: 0,
    autonomous_resolutions: 0,
    human_escalations: 0,
    avg_resolution_time_sec: 0,
    memory_growth_count: 0,
    recommendation_accuracy: 0.9,
    agent_success_rate: 0.95,
    most_common_failures: []
  });

  const [autoSimEnabled, setAutoSimEnabled] = useState<boolean>(false);

  // --- DATA FETCH ROUTINES ---
  
  const fetchServices = async () => {
    try {
      const res = await fetch(`${API_URL}/api/services/`);
      if (res.ok) {
        const data = await res.json();
        setServices(data);
      }
    } catch (err) {
      console.error("Error fetching services", err);
    }
  };

  const fetchIncidents = async () => {
    try {
      const res = await fetch(`${API_URL}/api/incidents/`);
      if (res.ok) {
        const data = await res.json();
        setIncidents(data);
      }
    } catch (err) {
      console.error("Error fetching incidents", err);
    }
  };

  const fetchMemories = async () => {
    try {
      const res = await fetch(`${API_URL}/api/memories/`);
      if (res.ok) {
        const data = await res.json();
        setMemories(data);
      }
    } catch (err) {
      console.error("Error fetching memories", err);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const res = await fetch(`${API_URL}/api/analytics/overview`);
      if (res.ok) {
        const data = await res.json();
        setAnalytics(data);
      }
    } catch (err) {
      console.error("Error fetching analytics", err);
    }
  };

  const fetchAllLogs = async () => {
    try {
      const promises = SERVICES_LIST.map(name => 
        fetch(`${API_URL}/api/services/${encodeURIComponent(name)}/logs?limit=15`)
          .then(res => res.ok ? res.json() : [])
          .catch(() => [])
      );
      const results = await Promise.all(promises);
      const combined = results.flat() as ServiceLog[];
      combined.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
      setRecentLogs(combined.slice(0, 35));
    } catch (err) {
      console.error("Error fetching unified logs", err);
    }
  };

  const refreshAllData = () => {
    fetchServices();
    fetchIncidents();
    fetchMemories();
    fetchAnalytics();
    fetchAllLogs();
  };

  // Poll databases every 2 seconds to keep stats and logs live
  useEffect(() => {
    refreshAllData();
    const interval = setInterval(refreshAllData, 2000);
    return () => clearInterval(interval);
  }, []);

  // --- AUTO INCIDENT SIMULATION HANDLER ---
  useEffect(() => {
    if (!autoSimEnabled) return;

    const injectAutoIncident = async () => {
      // Pick random scenario
      const scenario = AUTO_SIM_SCENARIOS[Math.floor(Math.random() * AUTO_SIM_SCENARIOS.length)];
      
      // Check if this service is already down to avoid flooding
      const serviceObj = services.find(s => s.service_name === scenario.affected_services);
      if (serviceObj && serviceObj.status !== 'Running') {
        return; // skip if already stopped/degraded
      }

      try {
        await fetch(`${API_URL}/api/incidents/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(scenario)
        });
        refreshAllData();
      } catch (err) {
        console.error("Auto incident injection failed", err);
      }
    };

    const interval = setInterval(injectAutoIncident, 45000); // Inject every 45s
    return () => clearInterval(interval);
  }, [autoSimEnabled, services]);

  const triggerDemoFromDashboard = async (demoNum: number) => {
    try {
      await fetch(`${API_URL}/api/demo/${demoNum}`, { method: 'POST' });
      refreshAllData();
      setActiveTab('incidents');
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="flex h-screen bg-dark-900 text-slate-100 overflow-hidden font-sans">
      
      {/* SIDEBAR NAVIGATION */}
      <aside className="w-64 bg-slate-950 border-r border-slate-800/80 flex flex-col justify-between shrink-0">
        <div className="space-y-6 py-6">
          
          {/* Logo Header */}
          <div className="px-6 flex items-center gap-3">
            <div className="h-10 w-10 bg-cyan-500/10 border border-cyan-500/30 rounded flex items-center justify-center shadow-[0_0_15px_rgba(6,182,212,0.1)]">
              <Radio className="text-cyan-400 h-5 w-5 animate-pulse-slow" />
            </div>
            <div>
              <h2 className="text-sm font-bold tracking-wider text-white uppercase font-mono">MediOps AI</h2>
              <span className="text-[9px] text-slate-500 font-mono tracking-widest uppercase">SRE Agent v1.0</span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1.5 px-3">
            <button
              onClick={() => setActiveTab('demo')}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded text-sm font-medium transition ${
                activeTab === 'demo' 
                  ? 'bg-slate-900 text-white border border-slate-800' 
                  : 'text-slate-400 hover:bg-slate-900/30 hover:text-slate-200'
              }`}
            >
              <Sparkles className={`h-4.5 w-4.5 ${activeTab === 'demo' ? 'text-cyan-400' : 'text-slate-500'}`} />
              Demo Controller
            </button>

            <button
              onClick={() => setActiveTab('dashboard')}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded text-sm font-medium transition ${
                activeTab === 'dashboard' 
                  ? 'bg-slate-900 text-white border border-slate-800' 
                  : 'text-slate-400 hover:bg-slate-900/30 hover:text-slate-200'
              }`}
            >
              <Activity className={`h-4.5 w-4.5 ${activeTab === 'dashboard' ? 'text-cyan-400' : 'text-slate-500'}`} />
              Dashboard Overview
            </button>

            <button
              onClick={() => setActiveTab('services')}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded text-sm font-medium transition ${
                activeTab === 'services' 
                  ? 'bg-slate-900 text-white border border-slate-800' 
                  : 'text-slate-400 hover:bg-slate-900/30 hover:text-slate-200'
              }`}
            >
              <Cpu className={`h-4.5 w-4.5 ${activeTab === 'services' ? 'text-cyan-400' : 'text-slate-500'}`} />
              Services Monitor
            </button>

            <button
              onClick={() => setActiveTab('incidents')}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded text-sm font-medium transition ${
                activeTab === 'incidents' 
                  ? 'bg-slate-900 text-white border border-slate-800' 
                  : 'text-slate-400 hover:bg-slate-900/30 hover:text-slate-200'
              }`}
            >
              <ShieldAlert className={`h-4.5 w-4.5 ${activeTab === 'incidents' ? 'text-cyan-400' : 'text-slate-500'}`} />
              Incident Management
              {incidents.filter(i => i.status !== 'Closed').length > 0 && (
                <span className="ml-auto bg-rose-500 text-dark-900 text-[10px] font-bold px-1.5 py-0.5 rounded-full shrink-0">
                  {incidents.filter(i => i.status !== 'Closed').length}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('timeline')}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded text-sm font-medium transition ${
                activeTab === 'timeline' 
                  ? 'bg-slate-900 text-white border border-slate-800' 
                  : 'text-slate-400 hover:bg-slate-900/30 hover:text-slate-200'
              }`}
            >
              <History className={`h-4.5 w-4.5 ${activeTab === 'timeline' ? 'text-cyan-400' : 'text-slate-500'}`} />
              Memory Timeline
            </button>

            <button
              onClick={() => setActiveTab('decisions')}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded text-sm font-medium transition ${
                activeTab === 'decisions' 
                  ? 'bg-slate-900 text-white border border-slate-800' 
                  : 'text-slate-400 hover:bg-slate-900/30 hover:text-slate-200'
              }`}
            >
              <BrainCircuit className={`h-4.5 w-4.5 ${activeTab === 'decisions' ? 'text-cyan-400' : 'text-slate-500'}`} />
              Agent Decisions
            </button>

            <button
              onClick={() => setActiveTab('analytics')}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded text-sm font-medium transition ${
                activeTab === 'analytics' 
                  ? 'bg-slate-900 text-white border border-slate-800' 
                  : 'text-slate-400 hover:bg-slate-900/30 hover:text-slate-200'
              }`}
            >
              <BarChart3 className={`h-4.5 w-4.5 ${activeTab === 'analytics' ? 'text-cyan-400' : 'text-slate-500'}`} />
              Analytics metrics
            </button>

            <button
              onClick={() => setActiveTab('settings')}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded text-sm font-medium transition ${
                activeTab === 'settings' 
                  ? 'bg-slate-900 text-white border border-slate-800' 
                  : 'text-slate-400 hover:bg-slate-900/30 hover:text-slate-200'
              }`}
            >
              <SettingsIcon className={`h-4.5 w-4.5 ${activeTab === 'settings' ? 'text-cyan-400' : 'text-slate-500'}`} />
              Settings
            </button>
          </nav>
        </div>

        {/* Footer info */}
        <div className="p-4 border-t border-slate-800/80 bg-slate-950 space-y-2 text-[10px] font-mono text-slate-500">
          <div className="flex justify-between">
            <span>DATABASE:</span>
            <span className="text-emerald-400 flex items-center gap-1">
              <ShieldCheck className="h-3 w-3" /> ONLINE
            </span>
          </div>
          <div className="flex justify-between">
            <span>VECTOR STORE:</span>
            <span className="text-emerald-400 flex items-center gap-1">
              <ShieldCheck className="h-3 w-3" /> QDRANT
            </span>
          </div>
        </div>
      </aside>

      {/* CONTENT CANVAS */}
      <main className="flex-1 bg-dark-900 p-6 md:p-8 overflow-y-auto min-w-0">
        
        {activeTab === 'demo' && (
          <DemoControl 
            apiUrl={API_URL} 
            refreshAllData={refreshAllData}
            setActiveTab={setActiveTab} 
          />
        )}
        
        {activeTab === 'dashboard' && (
          <Dashboard 
            services={services} 
            incidents={incidents} 
            analytics={analytics} 
            recentLogs={recentLogs}
            setActiveTab={setActiveTab}
            triggerDemo={triggerDemoFromDashboard}
          />
        )}

        {activeTab === 'services' && (
          <ServicesMonitor 
            services={services} 
            apiUrl={API_URL}
            refreshServices={fetchServices}
          />
        )}

        {activeTab === 'incidents' && (
          <IncidentManagement 
            incidents={incidents} 
            apiUrl={API_URL}
            refreshIncidents={refreshAllData}
          />
        )}

        {activeTab === 'timeline' && (
          <MemoryTimeline memories={memories} />
        )}

        {activeTab === 'decisions' && (
          <AgentDecisions incidents={incidents} />
        )}

        {activeTab === 'analytics' && (
          <Analytics 
            analytics={analytics} 
            memories={memories}
            incidents={incidents}
          />
        )}

        {activeTab === 'settings' && (
          <Settings 
            apiUrl={API_URL}
            autoSimEnabled={autoSimEnabled}
            toggleAutoSim={() => setAutoSimEnabled(!autoSimEnabled)}
          />
        )}

      </main>

    </div>
  );
}
