import { useState, useEffect } from 'react';
import { TrendingUp, Clock, Zap, DollarSign, Database, BarChart2 } from 'lucide-react';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts';

type Props = { metrics?: any };

const COLORS = { stage1: '#00ff88', stage2: '#00e5ff', stage3: '#ff9500' };

export default function MetricsDashboard({ metrics }: Props) {
  const [history, setHistory] = useState<any[]>([]);

  // Build rolling history from polling
  useEffect(() => {
    if (!metrics) return;
    setHistory(prev => {
      const next = [...prev, {
        t: new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        rps: metrics.throughput_rps || 0,
        latency: metrics.avg_latency_ms || 0,
        p95: metrics.p95_latency_ms || 0,
        s1: metrics.stage1_pct || 0,
        s2: metrics.stage2_pct || 0,
        s3: metrics.stage3_pct || 0,
      }].slice(-30);
      return next;
    });
  }, [metrics]);

  const pieData = [
    { name: 'Stage 1', value: metrics?.stage1_pct || 0, color: COLORS.stage1 },
    { name: 'Stage 2', value: metrics?.stage2_pct || 0, color: COLORS.stage2 },
    { name: 'Stage 3', value: metrics?.stage3_pct || 0, color: COLORS.stage3 },
  ];

  const statCards = [
    { label: 'Throughput', value: `${(metrics?.throughput_rps || 0).toFixed(1)}`, unit: 'req/s', icon: TrendingUp, color: '#00e5ff' },
    { label: 'Avg Latency', value: `${(metrics?.avg_latency_ms || 0).toFixed(0)}`, unit: 'ms', icon: Clock, color: '#00ff88' },
    { label: 'LLM Skip Rate', value: `${(metrics?.llm_skip_rate || 0).toFixed(1)}`, unit: '%', icon: Zap, color: '#00ff88' },
    { label: 'Cache Hit Rate', value: `${(metrics?.cache_hit_rate || 0).toFixed(1)}`, unit: '%', icon: Database, color: '#00e5ff' },
    { label: 'Total Processed', value: `${metrics?.total_processed || 0}`, unit: 'claims', icon: BarChart2, color: '#a0aec0' },
    { label: 'Cost Saved', value: `$${(metrics?.estimated_cost_saved_usd || 0).toFixed(4)}`, unit: 'vs GPT-4', icon: DollarSign, color: '#00ff88' },
  ];

  const customTooltipStyle = {
    background: '#0f1117',
    border: '1px solid #1e2330',
    borderRadius: '6px',
    fontSize: '11px',
    color: '#e2e8f0',
  };

  return (
    <div className="space-y-4">
      {/* Stat cards */}
      <div className="grid grid-cols-3 lg:grid-cols-6 gap-3">
        {statCards.map(({ label, value, unit, icon: Icon, color }) => (
          <div key={label} className="vera-panel p-3">
            <div className="flex items-center gap-1.5 mb-2">
              <Icon size={12} style={{ color }} />
              <span className="text-xs" style={{ color: '#4a5568' }}>{label}</span>
            </div>
            <div className="counter text-xl font-bold" style={{ color }}>{value}</div>
            <div className="text-xs" style={{ color: '#4a5568' }}>{unit}</div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Throughput chart */}
        <div className="vera-panel p-4 lg:col-span-2">
          <p className="text-xs mb-3" style={{ color: '#718096' }}>Throughput & Latency (rolling 30s)</p>
          <ResponsiveContainer width="100%" height={150}>
            <AreaChart data={history} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}>
              <defs>
                <linearGradient id="rpsGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00e5ff" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#00e5ff" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="latGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00ff88" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#00ff88" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2330" />
              <XAxis dataKey="t" tick={{ fill: '#4a5568', fontSize: 9 }} interval="preserveStartEnd" />
              <YAxis tick={{ fill: '#4a5568', fontSize: 9 }} />
              <Tooltip contentStyle={customTooltipStyle} />
              <Area type="monotone" dataKey="rps" stroke="#00e5ff" fill="url(#rpsGrad)" strokeWidth={1.5} name="req/s" dot={false} />
              <Area type="monotone" dataKey="latency" stroke="#00ff88" fill="url(#latGrad)" strokeWidth={1.5} name="ms" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Pipeline stage pie */}
        <div className="vera-panel p-4">
          <p className="text-xs mb-3" style={{ color: '#718096' }}>Pipeline Stage Distribution</p>
          <ResponsiveContainer width="100%" height={150}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={40}
                outerRadius={60}
                dataKey="value"
                paddingAngle={2}
              >
                {pieData.map((entry, index) => (
                  <Cell key={index} fill={entry.color} opacity={0.85} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={customTooltipStyle}
                formatter={(v: any) => [`${v.toFixed(1)}%`]}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-3 mt-1">
            {pieData.map(p => (
              <div key={p.name} className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full" style={{ background: p.color }} />
                <span className="text-xs" style={{ color: '#4a5568' }}>{p.name}: {p.value.toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Stage breakdown bar chart */}
      <div className="vera-panel p-4">
        <p className="text-xs mb-3" style={{ color: '#718096' }}>Stage Distribution Over Time</p>
        <ResponsiveContainer width="100%" height={100}>
          <BarChart data={history.slice(-15)} margin={{ top: 0, right: 5, bottom: 0, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2330" />
            <XAxis dataKey="t" tick={{ fill: '#4a5568', fontSize: 9 }} interval="preserveStartEnd" />
            <YAxis tick={{ fill: '#4a5568', fontSize: 9 }} />
            <Tooltip contentStyle={customTooltipStyle} />
            <Bar dataKey="s1" stackId="a" fill={COLORS.stage1} name="Stage 1" opacity={0.8} />
            <Bar dataKey="s2" stackId="a" fill={COLORS.stage2} name="Stage 2" opacity={0.8} />
            <Bar dataKey="s3" stackId="a" fill={COLORS.stage3} name="Stage 3 (LLM)" opacity={0.8} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
