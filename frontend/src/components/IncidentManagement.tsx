import { useEffect, useState, type FormEvent } from 'react';
import { Incident } from '../types';
import { ShieldAlert, Terminal, UserCheck, ShieldCheck, HelpCircle, Loader2 } from 'lucide-react';

interface IncidentManagementProps {
  incidents: Incident[];
  apiUrl: string;
  refreshIncidents: () => void;
}

export default function IncidentManagement({ incidents, apiUrl, refreshIncidents }: IncidentManagementProps) {
  const [selectedId, setSelectedId] = useState<number | null>(incidents[0]?.id || null);
  
  // Manual resolution state
  const [rc, setRc] = useState('');
  const [resolution, setResolution] = useState('');
  const [actionType, setActionType] = useState('Restart Service');
  const [resolving, setResolving] = useState(false);

  const selectedIncident = incidents.find(i => i.id === selectedId);

  // Reset fields on incident change
  useEffect(() => {
    if (selectedIncident) {
      // Pre-fill realistic default fields for ease of demo
      if (selectedIncident.title.includes('Lab')) {
        setRc("A file descriptor leak in the report generation queue caused the service worker to freeze.");
        setResolution("Restart the Lab Service to flush file handles and clean the cache directory.");
        setActionType("Restart Service");
      } else if (selectedIncident.title.includes('Login') || selectedIncident.title.includes('Auth')) {
        setRc("Session token synchronization buffer overflowed due to high traffic volume.");
        setResolution("Reset session controller memory cache and clear Authentication session logs.");
        setActionType("Reset Authentication");
      } else if (selectedIncident.title.includes('Billing')) {
        setRc("Database lock contention on active invoices table halted the processing thread pool.");
        setResolution("Clear active transaction queues and re-establish Database Service connection pool.");
        setActionType("Reconnect Database");
      } else if (selectedIncident.title.includes('Database') || selectedIncident.title.includes('DB')) {
        setRc("Database connection pool saturated by unindexed query spikes.");
        setResolution("Flush connection pool, clear active queries, and recycle Database Service container.");
        setActionType("Reconnect Database");
      } else {
        setRc("General buffer overflow degradation under high concurrent queue requests.");
        setResolution("Flush system queue, cycle socket ports and restart degraded microservice.");
        setActionType("Restart Service");
      }
    }
  }, [selectedId]);

  const handleResolveManual = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedIncident) return;
    
    setResolving(true);
    try {
      const response = await fetch(`${apiUrl}/api/incidents/${selectedIncident.id}/resolve-manual`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          root_cause: rc,
          resolution: resolution,
          action_type: actionType
        })
      });
      if (!response.ok) throw new Error("Failed to submit manual resolution.");
      refreshIncidents();
    } catch (err) {
      alert(err || "Submission failed");
    } finally {
      setResolving(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in text-left">
      <div className="flex justify-between items-center border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <ShieldAlert className="text-rose-500 h-6 w-6" />
            SRE Incident Desk
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Track real-time issues, observe agent diagnostic paths, and manually resolve escalated outages.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* INCIDENT LIST */}
        <div className="glass-panel rounded-lg lg:col-span-4 p-4 space-y-3">
          <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-2">Incidents Queue</h3>
          
          {incidents.length === 0 ? (
            <div className="text-center py-10 bg-slate-900/10 border border-slate-800/40 rounded">
              <ShieldCheck className="text-emerald-400 h-10 w-10 mx-auto mb-2 opacity-55" />
              <p className="text-slate-400 text-sm">System Healthy</p>
              <p className="text-xs text-slate-500 mt-0.5">No active or historic incidents.</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-[580px] overflow-y-auto pr-1">
              {incidents.map(inc => (
                <div
                  key={inc.id}
                  onClick={() => setSelectedId(inc.id)}
                  className={`p-3 rounded border text-left cursor-pointer transition ${
                    selectedId === inc.id
                      ? 'bg-slate-900 border-cyan-500/50 shadow-[0_0_10px_rgba(6,182,212,0.05)]'
                      : 'bg-slate-950/20 border-slate-800/50 hover:bg-slate-900/30'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <span className="text-xs font-semibold text-slate-200 truncate pr-2">#{inc.id} - {inc.title}</span>
                    <span className={`text-[8px] font-mono font-bold uppercase px-1.5 py-0.5 rounded ${
                      inc.status === 'Open' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                      inc.status === 'Investigating' ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 animate-pulse' :
                      inc.status === 'Closed' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                      'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    }`}>
                      {inc.status}
                    </span>
                  </div>
                  
                  <div className="flex justify-between items-center mt-3 text-[10px] font-mono text-slate-500">
                    <span>{inc.affected_services}</span>
                    <span>{new Date(inc.created_at).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* INCIDENT DETAILS */}
        <div className="lg:col-span-8 space-y-6">
          {selectedIncident ? (
            <div className="glass-panel p-6 rounded-lg space-y-6">
              
              {/* Main Info */}
              <div className="flex flex-col sm:flex-row justify-between sm:items-center border-b border-slate-800 pb-4 gap-3">
                <div>
                  <div className="text-xs text-slate-400 font-mono">INCIDENT RECORD #{selectedIncident.id}</div>
                  <h2 className="text-lg font-bold text-white mt-1">{selectedIncident.title}</h2>
                  <p className="text-xs text-slate-300 mt-1 leading-relaxed font-mono bg-slate-950/40 p-2.5 rounded border border-slate-800/60">
                    <strong>Symptoms:</strong> {selectedIncident.symptoms}
                  </p>
                </div>
                
                <div className="shrink-0 flex sm:flex-col items-end gap-2 sm:gap-1.5">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono uppercase ${
                    selectedIncident.severity === 'Critical' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' :
                    selectedIncident.severity === 'High' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                    'bg-slate-800 text-slate-300'
                  }`}>
                    {selectedIncident.severity} Severity
                  </span>
                  <div className="text-[10px] text-slate-500 font-mono">
                    Created: {new Date(selectedIncident.created_at).toLocaleTimeString()}
                  </div>
                </div>
              </div>

              {/* Agent Loop Diagnostics */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-1.5">
                  <Terminal className="text-cyan-400 h-4.5 w-4.5" />
                  SRE Autonomous Agent Decision Log
                </h3>

                {selectedIncident.decisions && selectedIncident.decisions.length > 0 ? (
                  <div className="bg-slate-950/80 p-4 rounded border border-slate-800/80 space-y-3 font-mono text-xs">
                    {selectedIncident.decisions.map(dec => (
                      <div key={dec.id} className="space-y-2">
                        <div className="flex justify-between items-center text-[10px] border-b border-slate-800 pb-1 text-slate-500">
                          <span>AGENT DECISION LOG</span>
                          <span>{new Date(dec.timestamp).toLocaleTimeString()}</span>
                        </div>
                        <p className="text-slate-300"><strong className="text-cyan-400">&gt;_ SRE Reasoning:</strong> {dec.reasoning}</p>
                        <div className="flex gap-4 pt-1">
                          <p className="text-slate-400">Confidence: <span className="text-cyan-300 font-bold">{Math.round(dec.confidence * 100)}%</span></p>
                          <p className="text-slate-400">Proposed Action: <span className="text-amber-400 font-bold">{dec.actions_proposed}</span></p>
                          <p className="text-slate-400">Action Selected: <span className="text-emerald-400 font-bold">{dec.action_selected}</span></p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-4 bg-slate-950/20 border border-slate-800/40 rounded text-center text-xs text-slate-500">
                    SRE Agent hasn't initialized diagnostics for this record.
                  </div>
                )}
              </div>

              {/* SRE Action Output Logs */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-1.5">
                  <Terminal className="text-emerald-400 h-4.5 w-4.5" />
                  SRE Executed Commands &amp; Verification logs
                </h3>
                
                {selectedIncident.actions && selectedIncident.actions.length > 0 ? (
                  <div className="bg-slate-950/80 p-4 rounded border border-slate-800/80 space-y-3 font-mono text-xs text-slate-300">
                    {selectedIncident.actions.map(act => (
                      <div key={act.id} className="space-y-1">
                        <div className="flex justify-between text-[10px] text-slate-500">
                          <span>CMD: {act.command}</span>
                          <span>{new Date(act.executed_at).toLocaleTimeString()}</span>
                        </div>
                        <div className="flex gap-2">
                          <span className={`font-bold ${
                            act.status === 'Success' ? 'text-emerald-400' :
                            act.status === 'Failed' ? 'text-rose-400' :
                            'text-cyan-400 animate-pulse'
                          }`}>[{act.status}]</span>
                          <span className="text-slate-400">{act.action_type}</span>
                        </div>
                        {act.log && (
                          <div className="pl-4 border-l border-slate-800 text-[11px] text-slate-400 py-0.5">
                            {act.log}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-4 bg-slate-950/20 border border-slate-800/40 rounded text-center text-xs text-slate-500">
                    No recovery commands executed yet.
                  </div>
                )}
              </div>

              {/* ENGINEER ESCALATION PANEL (Demo 1) */}
              {selectedIncident.status === 'Escalated' && (
                <form onSubmit={handleResolveManual} className="bg-slate-950/40 border border-rose-500/25 p-5 rounded-md space-y-4 shadow-[0_0_15px_rgba(244,63,94,0.03)] animate-pulse-slow">
                  <div className="flex items-center gap-2 text-rose-400 border-b border-slate-800 pb-2">
                    <UserCheck className="h-5 w-5" />
                    <h3 className="font-semibold text-sm">Engineer Manual Intervention Required (Demo 1)</h3>
                  </div>
                  <p className="text-slate-400 text-xs leading-relaxed">
                    The SRE agent escalated this outage because Qdrant returned 0 matching incident memory vectors. Input the resolution below. Your steps will be committed to vector memory so that the agent can autonomously solve future occurrences of this issue.
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">Isolate Root Cause</label>
                      <textarea
                        required
                        value={rc}
                        onChange={(e) => setRc(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-slate-700 h-20"
                        placeholder="e.g. Sticky log listener handler choked reports queue"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">Resolution Description</label>
                      <textarea
                        required
                        value={resolution}
                        onChange={(e) => setResolution(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-slate-700 h-20"
                        placeholder="e.g. Restart Lab Service to clear thread handles"
                      />
                    </div>
                  </div>

                  <div className="flex gap-4 items-center">
                    <div className="space-y-1 grow">
                      <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">Controller Action Type</label>
                      <select
                        value={actionType}
                        onChange={(e) => setActionType(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-slate-700"
                      >
                        <option value="Restart Service">Restart Service</option>
                        <option value="Reconnect Database">Reconnect Database</option>
                        <option value="Clear Queue">Clear Queue</option>
                        <option value="Reset Authentication">Reset Authentication</option>
                        <option value="Enable Backup Service">Enable Backup Service</option>
                      </select>
                    </div>
                    <button
                      type="submit"
                      disabled={resolving}
                      className="mt-5 px-5 py-2 bg-emerald-500 hover:bg-emerald-600 text-dark-900 font-semibold rounded text-xs transition duration-150 flex items-center gap-1.5"
                    >
                      {resolving ? (
                        <>
                          <Loader2 className="h-4.5 w-4.5 animate-spin" />
                          Verifying...
                        </>
                      ) : (
                        'Verify & Commit to Memory'
                      )}
                    </button>
                  </div>
                </form>
              )}

              {/* Resolved Closed Details */}
              {selectedIncident.status === 'Closed' && (
                <div className="bg-emerald-500/5 border border-emerald-500/20 p-4 rounded-md flex items-center justify-between text-xs font-mono">
                  <div className="flex items-center gap-2 text-emerald-400">
                    <ShieldCheck className="h-5 w-5" />
                    <span>Incident successfully resolved via {selectedIncident.resolution_type} action.</span>
                  </div>
                  <span className="text-slate-500">
                    Resolved: {selectedIncident.resolved_at ? new Date(selectedIncident.resolved_at).toLocaleTimeString() : 'N/A'}
                  </span>
                </div>
              )}

            </div>
          ) : (
            <div className="glass-panel p-16 rounded-lg text-center text-slate-400">
              <HelpCircle className="h-10 w-10 mx-auto mb-2 opacity-50 text-slate-500" />
              <p>Select an incident record from the queue to view SRE diagnostics and actions.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
