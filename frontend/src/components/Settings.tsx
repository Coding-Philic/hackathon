import { Settings as SettingsIcon, Shield, Sparkles, AlertCircle, Play, Square } from 'lucide-react';

interface SettingsProps {
  apiUrl: string;
  autoSimEnabled: boolean;
  toggleAutoSim: () => void;
}

export default function Settings({ autoSimEnabled, toggleAutoSim }: SettingsProps) {

  return (
    <div className="space-y-6 animate-fade-in text-left">
      <div className="flex justify-between items-center border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <SettingsIcon className="text-cyan-400 h-6 w-6" />
            System Control Panel
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Configure SRE Agent execution parameters, API credentials, and background simulator routines.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* API STATUS / ENVIRONMENT AUDIT */}
        <div className="glass-panel p-6 rounded-lg space-y-4">
          <h3 className="text-md font-semibold text-white flex items-center gap-2">
            <Shield className="text-cyan-400 h-5 w-5" />
            Environment Keys Audit
          </h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            The SRE agent is configured to look for the following environment variables. If they are not found, the agent gracefully falls back to the **Local SRE rule-based diagnostic engine** (offline friendly).
          </p>
          
          <div className="space-y-2.5 font-mono text-xs">
            <div className="flex justify-between items-center p-2.5 bg-slate-950/40 rounded border border-slate-800/80">
              <span className="text-slate-400">LLM_PROVIDER</span>
              <span className="text-cyan-400 font-bold">mock (Rule Engine Fallback)</span>
            </div>
            
            <div className="flex justify-between items-center p-2.5 bg-slate-950/40 rounded border border-slate-800/80">
              <span className="text-slate-400">OPENAI_API_KEY</span>
              <span className="text-slate-500">Not Loaded</span>
            </div>

            <div className="flex justify-between items-center p-2.5 bg-slate-950/40 rounded border border-slate-800/80">
              <span className="text-slate-400">GEMINI_API_KEY</span>
              <span className="text-slate-500">Not Loaded</span>
            </div>
          </div>
          
          <div className="p-3 bg-cyan-500/5 rounded border border-cyan-500/25 flex gap-2 items-start text-xs text-slate-300">
            <AlertCircle className="h-4.5 w-4.5 text-cyan-400 shrink-0 mt-0.5" />
            <p>
              Note: To load API keys, add them to your <code>.env</code> file in the project root directory and run <code>docker-compose down && docker-compose up --build</code>.
            </p>
          </div>
        </div>

        {/* AUTO INCIDENT SIMULATOR CONTROL */}
        <div className="glass-panel p-6 rounded-lg space-y-4">
          <h3 className="text-md font-semibold text-white flex items-center gap-2">
            <Sparkles className="text-amber-400 h-5 w-5" />
            Outages Auto-Injection
          </h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Enable Auto-Injection to randomly trigger a microservice outage (e.g. database pool depletion, token expiration, gateway timeout) every 45 seconds. Observe the SRE dashboard responding autonomously to diagnose, action, and restore service health scores to 100%.
          </p>

          <div className="flex justify-between items-center p-4 bg-slate-950/40 rounded-lg border border-slate-850/80">
            <div>
              <div className="text-sm font-semibold text-slate-200">Auto-Incident Generator</div>
              <div className="text-[10px] text-slate-500 mt-0.5">Simulates random server flapping</div>
            </div>
            
            <button
              onClick={toggleAutoSim}
              className={`px-4 py-2 rounded font-semibold text-xs flex items-center gap-2 transition duration-200 ${
                autoSimEnabled 
                  ? 'bg-rose-500/10 border border-rose-500/40 hover:bg-rose-500/20 text-rose-400' 
                  : 'bg-emerald-500/10 border border-emerald-500/40 hover:bg-emerald-500/20 text-emerald-400'
              }`}
            >
              {autoSimEnabled ? (
                <>
                  <Square className="h-3.5 w-3.5 fill-rose-400/20" />
                  Deactivate Simulation
                </>
              ) : (
                <>
                  <Play className="h-3.5 w-3.5 fill-emerald-400/20" />
                  Activate Simulation
                </>
              )}
            </button>
          </div>

          {autoSimEnabled && (
            <div className="p-3 bg-emerald-500/5 rounded border border-emerald-500/25 flex gap-2 items-center text-xs text-emerald-400 animate-pulse">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span>Background thread active. Random outage injection scheduled...</span>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
