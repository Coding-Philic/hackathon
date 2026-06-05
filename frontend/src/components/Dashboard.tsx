import React from 'react';
import { Service, Incident, SystemHealthOverview, ServiceLog } from '../types';
import { Activity, ShieldAlert, Zap, Cpu, Clock, History, AlertTriangle, CheckCircle, ArrowRight } from 'lucide-react';

interface DashboardProps {
  services: Service[];
  incidents: Incident[];
  analytics: SystemHealthOverview;
  recentLogs: ServiceLog[];
  setActiveTab: (tab: string) => void;
  triggerDemo: (demoNum: number) => void;
}

export default function Dashboard({ services, incidents, analytics, recentLogs, setActiveTab, triggerDemo }: DashboardProps) {
  const activeIncidents = incidents.filter(i => i.status !== 'Closed');

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex justify-between items-center border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Activity className="text-cyan-400 h-6 w-6" />
            Operations Overview
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Real-time telemetry and SRE agent status for simulated hospital microservices.
          </p>
        </div>
        <div className="flex gap-2">
          {incidents.length === 0 && (
            <button
              onClick={() => triggerDemo(1)}
              className="px-3 py-1.5 bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 rounded text-xs hover:bg-cyan-500/20 transition"
            >
              Quick Start Demo 1
            </button>
          )}
        </div>
      </div>

      {/* METRICS WIDGET GRID */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="glass-panel p-4 rounded-lg relative overflow-hidden">
          <div className="absolute top-0 right-0 h-16 w-16 bg-blue-500/5 rounded-bl-full pointer-events-none" />
          <div className="flex justify-between items-start">
            <span className="text-slate-400 text-xs font-medium uppercase tracking-wider">Total incidents</span>
            <AlertTriangle className="text-blue-400 h-4 w-4" />
          </div>
          <div className="mt-2 text-2xl font-bold text-white font-mono">{analytics.total_incidents}</div>
          <div className="text-[10px] text-slate-400 mt-1">Telemetry-reported failure states</div>
        </div>

        <div className="glass-panel p-4 rounded-lg relative overflow-hidden">
          <div className="absolute top-0 right-0 h-16 w-16 bg-emerald-500/5 rounded-bl-full pointer-events-none" />
          <div className="flex justify-between items-start">
            <span className="text-slate-400 text-xs font-medium uppercase tracking-wider">Resolved</span>
            <CheckCircle className="text-emerald-400 h-4 w-4" />
          </div>
          <div className="mt-2 text-2xl font-bold text-emerald-400 font-mono">
            {analytics.resolved_incidents}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">
            {analytics.total_incidents > 0 
              ? `${Math.round((analytics.resolved_incidents / analytics.total_incidents) * 100)}% resolution rate` 
              : 'No incidents recorded'}
          </div>
        </div>

        <div className="glass-panel p-4 rounded-lg relative overflow-hidden">
          <div className="absolute top-0 right-0 h-16 w-16 bg-cyan-500/5 rounded-bl-full pointer-events-none" />
          <div className="flex justify-between items-start">
            <span className="text-slate-400 text-xs font-medium uppercase tracking-wider">Autonomous Rec.</span>
            <Zap className="text-cyan-400 h-4 w-4" />
          </div>
          <div className="mt-2 text-2xl font-bold text-cyan-400 font-mono">
            {analytics.autonomous_resolutions}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">Self-healed via Vector RAG</div>
        </div>

        <div className="glass-panel p-4 rounded-lg relative overflow-hidden">
          <div className="absolute top-0 right-0 h-16 w-16 bg-amber-500/5 rounded-bl-full pointer-events-none" />
          <div className="flex justify-between items-start">
            <span className="text-slate-400 text-xs font-medium uppercase tracking-wider">Avg MTTR</span>
            <Clock className="text-amber-400 h-4 w-4" />
          </div>
          <div className="mt-2 text-2xl font-bold text-white font-mono">
            {analytics.avg_resolution_time_sec}s
          </div>
          <div className="text-[10px] text-slate-400 mt-1">Mean Time To Resolution</div>
        </div>

        <div className="glass-panel p-4 rounded-lg relative overflow-hidden">
          <div className="absolute top-0 right-0 h-16 w-16 bg-purple-500/5 rounded-bl-full pointer-events-none" />
          <div className="flex justify-between items-start">
            <span className="text-slate-400 text-xs font-medium uppercase tracking-wider">Memory Growth</span>
            <History className="text-purple-400 h-4 w-4" />
          </div>
          <div className="mt-2 text-2xl font-bold text-purple-400 font-mono">
            {analytics.memory_growth_count}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">Knowledge blocks in Qdrant</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* SERVICES STATE MONITOR CARD */}
        <div className="glass-panel p-5 rounded-lg lg:col-span-2 space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-md font-semibold text-white flex items-center gap-2">
              <Cpu className="text-cyan-400 h-5 w-5" />
              Microservice Infrastructure
            </h3>
            <button 
              onClick={() => setActiveTab('services')}
              className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
            >
              Control Center <ArrowRight className="h-3 w-3" />
            </button>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {services.map(service => (
              <div key={service.id} className="bg-slate-900/40 p-4 rounded border border-slate-800/80 hover:border-slate-800 transition">
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="text-sm font-semibold text-slate-200">{service.service_name}</h4>
                    <p className="text-[10px] text-slate-400 font-mono mt-0.5">Uptime: {service.uptime}s</p>
                  </div>
                  <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                    service.status === 'Running' ? 'bg-emerald-500/10 text-emerald-400' :
                    service.status === 'Degraded' ? 'bg-amber-500/10 text-amber-400 animate-pulse' :
                    'bg-rose-500/10 text-rose-400 animate-pulse'
                  }`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${
                      service.status === 'Running' ? 'bg-emerald-400' :
                      service.status === 'Degraded' ? 'bg-amber-400' :
                      'bg-rose-400'
                    }`} />
                    {service.status}
                  </span>
                </div>
                
                <div className="mt-3 flex justify-between items-center text-xs">
                  <span className="text-slate-400">Health score</span>
                  <span className={`font-semibold font-mono ${
                    service.health_score >= 80 ? 'text-emerald-400' :
                    service.health_score >= 50 ? 'text-amber-400' :
                    'text-rose-400'
                  }`}>{service.health_score}%</span>
                </div>
                {/* Micro Health Bar */}
                <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden mt-1.5">
                  <div 
                    className={`h-full transition-all duration-500 ${
                      service.health_score >= 80 ? 'bg-emerald-500' :
                      service.health_score >= 50 ? 'bg-amber-500' :
                      'bg-rose-500'
                    }`}
                    style={{ width: `${service.health_score}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ACTIVE INCIDENTS FEED */}
        <div className="glass-panel p-5 rounded-lg space-y-4 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-md font-semibold text-white flex items-center gap-2">
                <ShieldAlert className="text-rose-400 h-5 w-5" />
                Active Incident Feed
              </h3>
              <span className="bg-rose-500/10 text-rose-400 font-bold px-2 py-0.5 rounded text-[10px] font-mono">
                {activeIncidents.length} ACTIVE
              </span>
            </div>
            
            <div className="space-y-3 overflow-y-auto max-h-[280px] pr-1">
              {activeIncidents.length === 0 ? (
                <div className="text-center py-10 bg-slate-900/20 rounded border border-slate-800/40">
                  <CheckCircle className="text-emerald-400 h-8 w-8 mx-auto mb-2 opacity-60" />
                  <p className="text-slate-400 text-xs">All hospital microservices nominal.</p>
                  <p className="text-[10px] text-slate-500 mt-1">Zero outages active.</p>
                </div>
              ) : (
                activeIncidents.map(inc => (
                  <div 
                    key={inc.id} 
                    onClick={() => setActiveTab('incidents')}
                    className="p-3 bg-slate-950/40 hover:bg-slate-950/70 border border-slate-800/60 rounded cursor-pointer transition text-left"
                  >
                    <div className="flex justify-between items-start">
                      <span className="text-xs font-semibold text-slate-200 truncate pr-2">{inc.title}</span>
                      <span className={`text-[9px] font-mono font-bold uppercase px-1.5 py-0.5 rounded ${
                        inc.status === 'Open' ? 'bg-rose-500/15 text-rose-400 border border-rose-500/20' :
                        inc.status === 'Investigating' ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/20' :
                        'bg-amber-500/15 text-amber-400 border border-amber-500/20'
                      }`}>
                        {inc.status}
                      </span>
                    </div>
                    <p className="text-[10px] text-slate-400 mt-1 line-clamp-2">{inc.symptoms}</p>
                    <div className="flex justify-between items-center mt-2.5 text-[9px] font-mono text-slate-500">
                      <span>Service: {inc.affected_services}</span>
                      <span>{new Date(inc.created_at).toLocaleTimeString()}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
          
          <button 
            onClick={() => setActiveTab('incidents')}
            className="w-full text-center py-2 bg-slate-950 hover:bg-slate-900 text-slate-300 hover:text-white rounded border border-slate-800 text-xs transition"
          >
            Manage Incidents
          </button>
        </div>

      </div>

      {/* RECENT TELEMETRY ALERTS */}
      <div className="glass-panel p-5 rounded-lg">
        <h3 className="text-md font-semibold text-white mb-4 flex items-center gap-2">
          <Activity className="text-cyan-400 h-5 w-5" />
          Live Telemetry Alerts
        </h3>
        <div className="bg-slate-950/80 rounded border border-slate-800/80 p-3 font-mono text-xs overflow-y-auto max-h-[160px] space-y-1.5 text-left">
          {recentLogs.length === 0 ? (
            <div className="text-slate-500 text-center py-4">Awaiting telemetry logs...</div>
          ) : (
            recentLogs.map(log => (
              <div key={log.id} className="flex gap-2 leading-relaxed">
                <span className="text-slate-500 font-mono">[{new Date(log.timestamp).toLocaleTimeString()}]</span>
                <span className={`font-bold ${
                  log.level === 'CRITICAL' ? 'text-rose-500' :
                  log.level === 'ERROR' ? 'text-rose-400' :
                  log.level === 'WARNING' ? 'text-amber-400' :
                  'text-cyan-400'
                }`}>{log.level}</span>
                <span className="text-slate-400 font-semibold">{log.service_name}:</span>
                <span className="text-slate-300">{log.message}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
