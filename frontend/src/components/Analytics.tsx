import { SystemHealthOverview, MemoryEntry, Incident } from '../types';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts';
import { BarChart3, TrendingUp, Zap, Clock, ThumbsUp } from 'lucide-react';

interface AnalyticsProps {
  analytics: SystemHealthOverview;
  memories: MemoryEntry[];
  incidents: Incident[];
}

export default function Analytics({ analytics, memories }: AnalyticsProps) {
  
  // 1. Process Memory Growth Data
  // Sort memories chronologically and count accumulated items
  const sortedMemories = [...memories].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  const memoryGrowthData = sortedMemories.map((mem, index) => ({
    name: new Date(mem.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    count: index + 1
  }));

  // Add a fallback point if empty
  if (memoryGrowthData.length === 0) {
    memoryGrowthData.push({ name: 'Start', count: 0 });
  }

  // 2. Process Service Outages Data
  const failuresData = analytics.most_common_failures.map(item => ({
    name: item.service.replace(' Service', ''),
    count: item.count
  }));

  const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4'];

  // 3. Automation Ratio calculation
  const totalClosed = analytics.resolved_incidents;
  const autoResolutions = analytics.autonomous_resolutions;
  
  const automationRatio = totalClosed > 0 
    ? Math.round((autoResolutions / totalClosed) * 100) 
    : 100;

  return (
    <div className="space-y-6 animate-fade-in text-left">
      <div className="flex justify-between items-center border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <BarChart3 className="text-cyan-400 h-6 w-6" />
            SRE Analytics &amp; Metrics
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Analyze incident resolution speed improvements, agent learning velocity, and system failure profiles.
          </p>
        </div>
      </div>

      {/* Analytics Widgets */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="glass-panel p-5 rounded-lg flex items-center gap-4">
          <span className="p-3 rounded bg-cyan-500/10 text-cyan-400">
            <Zap className="h-6 w-6" />
          </span>
          <div>
            <div className="text-[10px] text-slate-500 uppercase font-bold tracking-wider font-mono">Automation Ratio</div>
            <div className="text-2xl font-bold text-white mt-0.5 font-mono">{automationRatio}%</div>
            <div className="text-[10px] text-slate-400">Autonomous vs Human resolutions</div>
          </div>
        </div>

        <div className="glass-panel p-5 rounded-lg flex items-center gap-4">
          <span className="p-3 rounded bg-amber-500/10 text-amber-400">
            <Clock className="h-6 w-6" />
          </span>
          <div>
            <div className="text-[10px] text-slate-500 uppercase font-bold tracking-wider font-mono">Mean Time To Heal</div>
            <div className="text-2xl font-bold text-white mt-0.5 font-mono">{analytics.avg_resolution_time_sec}s</div>
            <div className="text-[10px] text-slate-400">Average service recovery speed</div>
          </div>
        </div>

        <div className="glass-panel p-5 rounded-lg flex items-center gap-4">
          <span className="p-3 rounded bg-purple-500/10 text-purple-400">
            <TrendingUp className="h-6 w-6" />
          </span>
          <div>
            <div className="text-[10px] text-slate-500 uppercase font-bold tracking-wider font-mono">SRE Agent Accuracy</div>
            <div className="text-2xl font-bold text-purple-400 mt-0.5 font-mono">{Math.round(analytics.recommendation_accuracy * 100)}%</div>
            <div className="text-[10px] text-slate-400">Agent recommendation confidence average</div>
          </div>
        </div>

        <div className="glass-panel p-5 rounded-lg flex items-center gap-4">
          <span className="p-3 rounded bg-emerald-500/10 text-emerald-400">
            <ThumbsUp className="h-6 w-6" />
          </span>
          <div>
            <div className="text-[10px] text-slate-500 uppercase font-bold tracking-wider font-mono">SRE Success Rate</div>
            <div className="text-2xl font-bold text-emerald-400 mt-0.5 font-mono">{Math.round(analytics.agent_success_rate * 100)}%</div>
            <div className="text-[10px] text-slate-400">Successful autonomous execution rate</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Memory Growth Chart */}
        <div className="glass-panel p-5 rounded-lg space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-white">Qdrant Memory Growth</h3>
            <p className="text-xs text-slate-400">Cumulative count of learned incident resolution vectors stored in database.</p>
          </div>
          
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={memoryGrowthData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorMemory" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                <YAxis stroke="#64748b" fontSize={10} allowDecimals={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#f8fafc', fontSize: '11px', fontFamily: 'monospace' }}
                  labelClassName="text-purple-400 font-bold"
                />
                <Area type="monotone" dataKey="count" name="Memory vectors" stroke="#8b5cf6" strokeWidth={2} fillOpacity={1} fill="url(#colorMemory)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Common Failures Bar Chart */}
        <div className="glass-panel p-5 rounded-lg space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-white">Service Outages Frequency</h3>
            <p className="text-xs text-slate-400">Cumulative count of incident failure reports per microservice module.</p>
          </div>
          
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={failuresData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                <XAxis dataKey="name" stroke="#64748b" fontSize={9} />
                <YAxis stroke="#64748b" fontSize={10} allowDecimals={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#f8fafc', fontSize: '11px', fontFamily: 'monospace' }}
                />
                <Bar dataKey="count" name="Outages count" radius={[4, 4, 0, 0]}>
                  {failuresData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
