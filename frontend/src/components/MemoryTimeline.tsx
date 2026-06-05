import { MemoryEntry } from '../types';
import { History, Cpu, Database, Award, GitCommit } from 'lucide-react';

interface MemoryTimelineProps {
  memories: MemoryEntry[];
}

export default function MemoryTimeline({ memories }: MemoryTimelineProps) {
  return (
    <div className="space-y-6 animate-fade-in text-left">
      <div className="flex justify-between items-center border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <History className="text-purple-400 h-6 w-6" />
            Vector Memory Timeline
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Browse incident resolution profiles stored as high-dimensional embeddings inside Qdrant.
          </p>
        </div>
      </div>

      {memories.length === 0 ? (
        <div className="glass-panel p-16 rounded-lg text-center text-slate-400">
          <Database className="h-10 w-10 mx-auto mb-2 text-slate-600 opacity-60" />
          <p className="text-slate-400 text-sm">Vector Database Empty</p>
          <p className="text-xs text-slate-500 mt-1">
            Trigger Demo 1, let the agent fail, and input a manual resolution to seed your first memory vector.
          </p>
        </div>
      ) : (
        <div className="relative border-l border-slate-800 ml-4 md:ml-6 space-y-8 pl-6 md:pl-8">
          {memories.map((mem, index) => (
            <div key={mem.id} className="relative group">
              {/* Timeline marker */}
              <span className="absolute -left-[35px] md:-left-[43px] top-1.5 flex h-7 w-7 items-center justify-center rounded-full bg-slate-900 border border-slate-700/60 ring-4 ring-dark-900 text-purple-400 group-hover:border-purple-500 group-hover:text-purple-300 transition duration-200">
                <GitCommit className="h-4.5 w-4.5" />
              </span>

              {/* Memory Card */}
              <div className="glass-panel p-6 rounded-lg space-y-4 hover:border-slate-700/70 transition duration-300">
                <div className="flex flex-col sm:flex-row justify-between sm:items-center border-b border-slate-800/80 pb-3 gap-2">
                  <div>
                    <span className="text-[10px] text-purple-400 font-mono font-bold uppercase tracking-wider bg-purple-500/10 border border-purple-500/20 px-2 py-0.5 rounded">
                      Embedding Vector #{index + 1}
                    </span>
                    <h3 className="text-md font-bold text-white mt-1.5">{mem.title}</h3>
                  </div>
                  
                  <div className="flex items-center gap-1.5 text-xs text-slate-500 font-mono shrink-0">
                    <Database className="h-4 w-4 text-purple-400/80" />
                    <span>Qdrant UUID: {mem.vector_id ? `${mem.vector_id.substring(0, 8)}...` : 'Local-DB'}</span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div className="space-y-1 bg-slate-950/20 p-3 rounded border border-slate-800/40">
                    <span className="text-slate-500 font-bold uppercase font-mono text-[9px]">Symptoms reported</span>
                    <p className="text-slate-300 leading-relaxed font-mono">{mem.symptoms}</p>
                  </div>
                  
                  <div className="space-y-1 bg-slate-950/20 p-3 rounded border border-slate-800/40">
                    <span className="text-slate-500 font-bold uppercase font-mono text-[9px]">Isolated Microservice</span>
                    <div className="flex items-center gap-1.5 text-slate-200 font-mono mt-1">
                      <Cpu className="h-4 w-4 text-cyan-400" />
                      <span>{mem.affected_services}</span>
                    </div>
                  </div>
                </div>

                <div className="space-y-3 pt-1">
                  <div className="border-l-2 border-amber-500/40 pl-3">
                    <span className="text-slate-400 text-[10px] uppercase font-bold tracking-wider font-mono">Verified Root Cause:</span>
                    <p className="text-xs text-slate-200 mt-0.5 leading-relaxed">{mem.root_cause}</p>
                  </div>

                  <div className="border-l-2 border-emerald-500/40 pl-3">
                    <span className="text-slate-400 text-[10px] uppercase font-bold tracking-wider font-mono">Resolution Procedure:</span>
                    <p className="text-xs text-slate-200 mt-0.5 leading-relaxed">{mem.resolution}</p>
                  </div>
                </div>

                <div className="flex justify-between items-center border-t border-slate-800/50 pt-3 text-[10px] font-mono text-slate-500">
                  <div className="flex items-center gap-4">
                    <span className="flex items-center gap-1">
                      <Cpu className="h-3.5 w-3.5 text-cyan-500" />
                      Controller Action: <strong className="text-cyan-400 font-bold ml-0.5">{mem.actions_executed}</strong>
                    </span>
                    <span className="flex items-center gap-1">
                      <Award className="h-3.5 w-3.5 text-emerald-500" />
                      Historical Success Rate: <strong className="text-emerald-400 font-bold ml-0.5">{Math.round(mem.success_rate * 100)}%</strong>
                    </span>
                  </div>
                  <span>Saved: {new Date(mem.timestamp).toLocaleString()}</span>
                </div>

              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
