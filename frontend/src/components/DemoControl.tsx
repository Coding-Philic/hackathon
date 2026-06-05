import React, { useState } from 'react';
import { Play, RotateCcw, ShieldAlert, Sparkles, Database, CheckCircle, ArrowRight } from 'lucide-react';

interface DemoControlProps {
  apiUrl: string;
  refreshAllData: () => void;
  setActiveTab: (tab: string) => void;
}

export default function DemoControl({ apiUrl, refreshAllData, setActiveTab }: DemoControlProps) {
  const [loading, setLoading] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
  const [activeStep, setActiveStep] = useState<number>(1);

  const runDemo = async (demoNum: number) => {
    setLoading(`demo${demoNum}`);
    setMessage(null);
    try {
      const response = await fetch(`${apiUrl}/api/demo/${demoNum}`, { method: 'POST' });
      if (!response.ok) throw new Error(`Demo ${demoNum} failed to start.`);
      
      const data = await response.json();
      setMessage({
        type: 'success',
        text: demoNum === 3 
          ? "Demo 3 dataset populated successfully. Check Analytics & Timeline!" 
          : `Demo ${demoNum} triggered! Active Incident ID: #${data.id || 'N/A'}.`
      });
      
      refreshAllData();
      
      // Guide navigation
      if (demoNum === 1 || demoNum === 2) {
        setTimeout(() => setActiveTab('incidents'), 1500);
      } else if (demoNum === 3) {
        setTimeout(() => setActiveTab('analytics'), 1500);
      }
      
      setActiveStep(demoNum === 1 ? 2 : demoNum === 2 ? 3 : 1);
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || "An error occurred." });
    } finally {
      setLoading(null);
    }
  };

  const resetSystem = async () => {
    setLoading('reset');
    setMessage(null);
    try {
      const response = await fetch(`${apiUrl}/api/memories/clear`, { method: 'DELETE' });
      if (!response.ok) throw new Error("Reset failed.");
      setMessage({ type: 'success', text: "Vector memory database, active incidents, and service states fully cleared." });
      refreshAllData();
      setActiveStep(1);
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || "An error occurred." });
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex justify-between items-center border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Sparkles className="text-cyan-400 h-6 w-6" />
            Hackathon Demo Controller
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Execute step-by-step incident response demo flows to demonstrate vector memory learning.
          </p>
        </div>
        <button
          onClick={resetSystem}
          disabled={loading !== null}
          className="cyber-button-red flex items-center gap-2 text-sm py-1.5"
        >
          <RotateCcw className="h-4 w-4" />
          {loading === 'reset' ? 'Resetting...' : 'Reset Memory & DB'}
        </button>
      </div>

      {message && (
        <div className={`p-4 rounded-md border text-sm flex items-center gap-3 ${
          message.type === 'success' 
            ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' 
            : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
        }`}>
          <CheckCircle className="h-5 w-5 shrink-0" />
          <span>{message.text}</span>
        </div>
      )}

      {/* Demo Cards Carousel/Steps */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* DEMO 1 */}
        <div className={`glass-card p-6 rounded-lg flex flex-col justify-between relative ${
          activeStep === 1 ? 'border-cyan-500/50 shadow-[0_0_15px_rgba(6,182,212,0.1)]' : 'opacity-70'
        }`}>
          {activeStep === 1 && (
            <span className="absolute -top-3 left-4 bg-cyan-500 text-dark-900 font-bold px-2 py-0.5 rounded text-xs uppercase tracking-wider">
              Active Step
            </span>
          )}
          <div>
            <div className="text-slate-400 text-xs font-mono mb-1">SCENARIO 1</div>
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <Database className="text-cyan-400 h-5 w-5" />
              Demo 1: Cold Start Outage
            </h3>
            
            <p className="text-slate-300 text-xs mt-3 leading-relaxed">
              Resets the database, wipes Qdrant memory, and stops the <strong>Lab Service</strong>.
            </p>
            
            <div className="bg-slate-950/40 p-3 rounded border border-slate-800/80 mt-4 space-y-2 text-[11px] font-mono text-slate-400">
              <div className="flex items-center gap-1.5 text-cyan-400">
                <ShieldAlert className="h-3 w-3" /> Expected Behavior:
              </div>
              <p>1. SRE searches memory &gt; returns 0 matches.</p>
              <p>2. Agent isolates symptoms, proposes failure list.</p>
              <p>3. Agent escalates to Engineer (requires manual resolve).</p>
              <p>4. Engineer resolves it in UI &gt; stores resolution in Qdrant.</p>
            </div>
          </div>
          
          <button
            onClick={() => runDemo(1)}
            disabled={loading !== null}
            className="w-full mt-6 bg-cyan-500 hover:bg-cyan-600 text-dark-900 font-semibold py-2 rounded flex items-center justify-center gap-2 transition-all"
          >
            <Play className="h-4 w-4 fill-dark-900" />
            {loading === 'demo1' ? 'Executing...' : 'Trigger Demo 1'}
          </button>
        </div>

        {/* DEMO 2 */}
        <div className={`glass-card p-6 rounded-lg flex flex-col justify-between relative ${
          activeStep === 2 ? 'border-emerald-500/50 shadow-[0_0_15px_rgba(16,185,129,0.1)]' : 'opacity-70'
        }`}>
          {activeStep === 2 && (
            <span className="absolute -top-3 left-4 bg-emerald-500 text-dark-900 font-bold px-2 py-0.5 rounded text-xs uppercase tracking-wider">
              Active Step
            </span>
          )}
          <div>
            <div className="text-slate-400 text-xs font-mono mb-1">SCENARIO 2</div>
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <Sparkles className="text-emerald-400 h-5 w-5" />
              Demo 2: Autonomous Recall
            </h3>
            
            <p className="text-slate-300 text-xs mt-3 leading-relaxed">
              Triggers the same <strong>Lab Service</strong> outage. The SRE agent searches Qdrant, matches the previous incident, and recovers the service.
            </p>
            
            <div className="bg-slate-950/40 p-3 rounded border border-slate-800/80 mt-4 space-y-2 text-[11px] font-mono text-slate-400">
              <div className="flex items-center gap-1.5 text-emerald-400">
                <CheckCircle className="h-3 w-3" /> Expected Behavior:
              </div>
              <p>1. SRE queries Qdrant &gt; finds 99% similar incident.</p>
              <p>2. SRE retrieves resolution: <em>"Restart Lab Service"</em>.</p>
              <p>3. SRE executes restart autonomously.</p>
              <p>4. Health verifies to 100% &gt; incident closes automatically.</p>
            </div>
          </div>
          
          <button
            onClick={() => runDemo(2)}
            disabled={loading !== null}
            className="w-full mt-6 bg-emerald-500 hover:bg-emerald-600 text-dark-900 font-semibold py-2 rounded flex items-center justify-center gap-2 transition-all"
          >
            <Play className="h-4 w-4 fill-dark-900" />
            {loading === 'demo2' ? 'Executing...' : 'Trigger Demo 2'}
          </button>
        </div>

        {/* DEMO 3 */}
        <div className={`glass-card p-6 rounded-lg flex flex-col justify-between relative ${
          activeStep === 3 ? 'border-purple-500/50 shadow-[0_0_15px_rgba(139,92,246,0.1)]' : 'opacity-70'
        }`}>
          {activeStep === 3 && (
            <span className="absolute -top-3 left-4 bg-purple-500 text-dark-900 font-bold px-2 py-0.5 rounded text-xs uppercase tracking-wider">
              Active Step
            </span>
          )}
          <div>
            <div className="text-slate-400 text-xs font-mono mb-1">SCENARIO 3</div>
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <ArrowRight className="text-purple-400 h-5 w-5" />
              Demo 3: Memory Scale
            </h3>
            
            <p className="text-slate-300 text-xs mt-3 leading-relaxed">
              Populates the database with multiple past memories (Auth, DB, Billing failures), logs, and triggers a live <strong>Pharmacy Service</strong> failure.
            </p>
            
            <div className="bg-slate-950/40 p-3 rounded border border-slate-800/80 mt-4 space-y-2 text-[11px] font-mono text-slate-400">
              <div className="flex items-center gap-1.5 text-purple-400">
                <Database className="h-3 w-3" /> Expected Behavior:
              </div>
              <p>1. Dashboard populates with historical data graphs.</p>
              <p>2. Timeline shows multiple incident categories.</p>
              <p>3. SRE starts resolving active Pharmacy incident.</p>
              <p>4. Displays SRE Agent Success Rates and MTTR drops.</p>
            </div>
          </div>
          
          <button
            onClick={() => runDemo(3)}
            disabled={loading !== null}
            className="w-full mt-6 bg-purple-500 hover:bg-purple-600 text-dark-900 font-semibold py-2 rounded flex items-center justify-center gap-2 transition-all"
          >
            <Play className="h-4 w-4 fill-dark-900" />
            {loading === 'demo3' ? 'Executing...' : 'Trigger Demo 3'}
          </button>
        </div>

      </div>

      <div className="bg-slate-950/60 rounded-lg p-5 border border-slate-800/60 mt-8">
        <h2 className="text-lg font-semibold text-white mb-3">Hackathon Pitch &amp; Flow Guide</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm text-slate-300">
          <div className="space-y-2">
            <h4 className="font-medium text-cyan-400 flex items-center gap-1.5">
              <span className="w-5 h-5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-500/30 flex items-center justify-center text-xs">1</span>
              Phase 1: Knowledge Lost
            </h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Show the empty memory timeline. Trigger <strong>Demo 1</strong>. Point out how the SRE is forced to escalate. Explain that in traditional hospitals, resolving this takes average 4 hours, and the resolution is rarely documented.
            </p>
          </div>
          <div className="space-y-2">
            <h4 className="font-medium text-emerald-400 flex items-center gap-1.5">
              <span className="w-5 h-5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-500/30 flex items-center justify-center text-xs">2</span>
              Phase 2: Self-Learning
            </h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Resolve the incident manually by typing root cause and action. Show how the SRE agent captures this resolved event and publishes it as a dense embedding payload into the Qdrant vector database.
            </p>
          </div>
          <div className="space-y-2">
            <h4 className="font-medium text-purple-400 flex items-center gap-1.5">
              <span className="w-5 h-5 rounded-full bg-purple-950 text-purple-400 border border-purple-500/30 flex items-center justify-center text-xs">3</span>
              Phase 3: Autonomous SRE
            </h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Trigger <strong>Demo 2</strong>. SRE instantly checks Qdrant, identifies matching symptoms, executes the restart, and restores health in under 5 seconds. Autonomous recovery goes from 4 hours to 5 seconds!
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
