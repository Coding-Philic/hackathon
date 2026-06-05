import React, { useState } from 'react';
import { Service } from '../types';
import { Cpu, Play, Square, RefreshCw, AlertTriangle, CheckCircle, Sliders } from 'lucide-react';

interface ServicesMonitorProps {
  services: Service[];
  apiUrl: string;
  refreshServices: () => void;
}

export default function ServicesMonitor({ services, apiUrl, refreshServices }: ServicesMonitorProps) {
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [degradeForm, setDegradeForm] = useState<{ [key: string]: { score: number, reason: string } }>({});

  const handleAction = async (serviceName: string, action: 'start' | 'stop' | 'restart' | 'recover') => {
    const key = `${serviceName}_${action}`;
    setActionLoading(key);
    try {
      const response = await fetch(`${apiUrl}/api/services/${serviceName}/${action}`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error("Failed to execute service action.");
      refreshServices();
    } catch (err) {
      alert(err || "Action failed");
    } finally {
      setActionLoading(null);
    }
  };

  const handleDegrade = async (serviceName: string) => {
    const key = `${serviceName}_degrade`;
    setActionLoading(key);
    
    const config = degradeForm[serviceName] || { score: 40, reason: "Memory leak detected" };
    try {
      const response = await fetch(`${apiUrl}/api/services/${serviceName}/degrade`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          health_score: Number(config.score),
          reason: config.reason || "CPU spikes under load"
        })
      });
      if (!response.ok) throw new Error("Failed to degrade service.");
      refreshServices();
    } catch (err) {
      alert(err || "Degradation failed");
    } finally {
      setActionLoading(null);
    }
  };

  const updateDegradeConfig = (serviceName: string, field: 'score' | 'reason', value: any) => {
    setDegradeForm(prev => ({
      ...prev,
      [serviceName]: {
        score: field === 'score' ? Number(value) : (prev[serviceName]?.score ?? 40),
        reason: field === 'reason' ? String(value) : (prev[serviceName]?.reason ?? "Telemetry latency warnings")
      }
    }));
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex justify-between items-center border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Cpu className="text-cyan-400 h-6 w-6" />
            Infrastructure Controllers
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Simulate outages and performance degradation to test autonomous recovery responses.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {services.map(service => {
          const config = degradeForm[service.service_name] || { score: 40, reason: "Resource exhaustion" };
          
          return (
            <div key={service.id} className="glass-panel p-6 rounded-lg space-y-4">
              {/* Header */}
              <div className="flex justify-between items-start">
                <div className="space-y-1">
                  <h3 className="text-lg font-semibold text-white">{service.service_name}</h3>
                  <p className="text-xs text-slate-400 font-mono">
                    Last restarted: {new Date(service.last_restart).toLocaleTimeString()}
                  </p>
                </div>
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-bold uppercase ${
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

              {/* Stats Grid */}
              <div className="grid grid-cols-3 gap-4 bg-slate-950/30 p-3 rounded border border-slate-800/60 font-mono text-xs">
                <div>
                  <div className="text-slate-500 text-[10px] uppercase">Uptime</div>
                  <div className="text-slate-200 mt-1 font-bold">{service.uptime}s</div>
                </div>
                <div>
                  <div className="text-slate-500 text-[10px] uppercase">Error count</div>
                  <div className="text-slate-200 mt-1 font-bold">{service.error_count}</div>
                </div>
                <div>
                  <div className="text-slate-500 text-[10px] uppercase">Health Score</div>
                  <div className={`mt-1 font-bold ${
                    service.health_score >= 80 ? 'text-emerald-400' :
                    service.health_score >= 50 ? 'text-amber-400' :
                    'text-rose-400'
                  }`}>{service.health_score}%</div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap gap-2 pt-2">
                <button
                  disabled={actionLoading !== null}
                  onClick={() => handleAction(service.service_name, 'start')}
                  className="cyber-button-green flex items-center gap-1 text-xs py-1.5"
                >
                  <Play className="h-3.5 w-3.5 fill-emerald-400/20" />
                  {actionLoading === `${service.service_name}_start` ? 'Starting...' : 'Start'}
                </button>
                
                <button
                  disabled={actionLoading !== null}
                  onClick={() => handleAction(service.service_name, 'stop')}
                  className="cyber-button-red flex items-center gap-1 text-xs py-1.5"
                >
                  <Square className="h-3.5 w-3.5 fill-rose-400/20" />
                  {actionLoading === `${service.service_name}_stop` ? 'Stopping...' : 'Simulate Stop'}
                </button>
                
                <button
                  disabled={actionLoading !== null}
                  onClick={() => handleAction(service.service_name, 'restart')}
                  className="cyber-button-blue flex items-center gap-1 text-xs py-1.5"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  {actionLoading === `${service.service_name}_restart` ? 'Restarting...' : 'Restart'}
                </button>

                {service.status !== 'Running' && (
                  <button
                    disabled={actionLoading !== null}
                    onClick={() => handleAction(service.service_name, 'recover')}
                    className="cyber-button-green flex items-center gap-1 text-xs py-1.5 bg-emerald-500/10 border-emerald-500/50"
                  >
                    <CheckCircle className="h-3.5 w-3.5" />
                    Recover Normal
                  </button>
                )}
              </div>

              {/* Manual Degradation Panel */}
              <div className="bg-slate-950/20 border border-slate-800/80 p-4 rounded-md space-y-3">
                <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Sliders className="h-3.5 w-3.5 text-amber-500" />
                  Performance Degradation Simulator
                </h4>
                
                <div className="space-y-1">
                  <div className="flex justify-between text-[10px] font-mono text-slate-400">
                    <span>Target Health Score</span>
                    <span className="text-amber-400 font-bold">{config.score}%</span>
                  </div>
                  <input
                    type="range"
                    min="10"
                    max="80"
                    value={config.score}
                    onChange={(e) => updateDegradeConfig(service.service_name, 'score', e.target.value)}
                    className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-amber-500"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] font-mono text-slate-400 block">Symptom Description</label>
                  <input
                    type="text"
                    value={config.reason}
                    onChange={(e) => updateDegradeConfig(service.service_name, 'reason', e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-xs text-slate-300 focus:outline-none focus:border-slate-700 font-mono"
                    placeholder="e.g. database pool depletion"
                  />
                </div>

                <button
                  disabled={actionLoading !== null}
                  onClick={() => handleDegrade(service.service_name)}
                  className="w-full py-1.5 bg-amber-500/10 border border-amber-500/30 hover:bg-amber-500/20 text-amber-400 rounded text-xs transition duration-200"
                >
                  {actionLoading === `${service.service_name}_degrade` ? 'Injecting...' : 'Inject Degradation Outage'}
                </button>
              </div>

            </div>
          );
        })}
      </div>
    </div>
  );
}
