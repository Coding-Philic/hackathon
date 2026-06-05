import React from 'react';
import { Incident } from '../types';
import { BrainCircuit, CheckCircle, ShieldAlert, Clock, Cpu } from 'lucide-react';

interface AgentDecisionsProps {
  incidents: Incident[];
}

export default function AgentDecisions({ incidents }: AgentDecisionsProps) {
  // Extract all decisions from incidents
  const decisions = incidents.flatMap(inc => 
    (inc.decisions || []).map(dec => ({
      ...dec,
      incidentTitle: inc.title,
      incidentId: inc.id
    }))
  ).sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

  return (
    <div className="space-y-6 animate-fade-in text-left">
      <div className="flex justify-between items-center border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <BrainCircuit className="text-cyan-400 h-6 w-6" />
            Agent Decision Logs
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Audit SRE diagnostic paths, LLM reasoning parameters, and vector retrieval confidence ratings.
          </p>
        </div>
      </div>

      {decisions.length === 0 ? (
        <div className="glass-panel p-16 rounded-lg text-center text-slate-400">
          <BrainCircuit className="h-10 w-10 mx-auto mb-2 text-slate-600 opacity-60" />
          <p className="text-slate-400 text-sm">No Decisions Logged</p>
          <p className="text-xs text-slate-500 mt-1">
            Trigger an incident via Demo Controller or Infrastructure panel to start the SRE Agent.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {decisions.map(dec => (
            <div key={dec.id} className="glass-panel p-5 rounded-lg space-y-3">
              <div className="flex flex-col sm:flex-row justify-between sm:items-center border-b border-slate-800 pb-2.5 gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 px-2 py-0.5 rounded">
                    DECISION #{dec.id}
                  </span>
                  <span className="text-xs text-slate-400 font-mono">
                    INCIDENT #{dec.incidentId}: <strong className="text-slate-200">{dec.incidentTitle}</strong>
                  </span>
                </div>
                
                <span className={`self-start sm:self-auto text-[9px] font-mono font-bold uppercase px-1.5 py-0.5 rounded ${
                  dec.status === 'Success' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                  dec.status === 'Failed' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                  dec.status === 'Escalated' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                  'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 animate-pulse'
                }`}>
                  {dec.status}
                </span>
              </div>

              <div className="bg-slate-950/80 p-4 rounded border border-slate-800/80 font-mono text-xs text-slate-300 space-y-2 leading-relaxed">
                <div className="text-[10px] text-slate-500 font-bold uppercase">SRE Reasoning Trace</div>
                <p className="text-slate-300">
                  <span className="text-cyan-400 font-bold">&gt;_ </span>
                  {dec.reasoning}
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1 font-mono text-xs text-slate-400">
                <div className="space-y-1">
                  <div className="text-[10px] text-slate-500 uppercase font-bold">Confidence Score</div>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="w-24 bg-slate-800 h-2 rounded-full overflow-hidden">
                      <div 
                        className={`h-full ${
                          dec.confidence >= 0.8 ? 'bg-emerald-500' :
                          dec.confidence >= 0.5 ? 'bg-amber-500' :
                          'bg-rose-500'
                        }`}
                        style={{ width: `${dec.confidence * 100}%` }}
                      />
                    </div>
                    <span className="font-bold text-slate-200">{Math.round(dec.confidence * 100)}%</span>
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="text-[10px] text-slate-500 uppercase font-bold">Proposed Action</div>
                  <div className="text-slate-200 font-bold mt-1 line-clamp-1">{dec.actions_proposed}</div>
                </div>

                <div className="space-y-1">
                  <div className="text-[10px] text-slate-500 uppercase font-bold">Action Selected</div>
                  <div className="text-emerald-400 font-bold mt-1 line-clamp-1">{dec.action_selected}</div>
                </div>
              </div>

              <div className="flex justify-between items-center border-t border-slate-800/50 pt-2.5 text-[9px] font-mono text-slate-500">
                <span className="flex items-center gap-1">
                  <Cpu className="text-slate-600 h-3.5 w-3.5" />
                  Orchestrator: LangGraph SRE Chain
                </span>
                <span className="flex items-center gap-1">
                  <Clock className="text-slate-600 h-3.5 w-3.5" />
                  Executed: {new Date(dec.timestamp).toLocaleString()}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
