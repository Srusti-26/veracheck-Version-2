import { Shield, Activity, Settings, Zap, Radio } from 'lucide-react';

type Props = {
  activeTab: string;
  setActiveTab: (tab: any) => void;
  feedRunning: boolean;
  onStartFeed: () => void;
  onStopFeed: () => void;
  metrics?: any;
};

export default function Header({ activeTab, setActiveTab, feedRunning, onStartFeed, onStopFeed, metrics }: Props) {
  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: Activity },
    { id: 'checker', label: 'Fact Check', icon: Shield },
    { id: 'admin', label: 'Admin', icon: Settings },
  ];

  return (
    <header className="border-b sticky top-0 z-50 backdrop-blur-sm" style={{ borderColor: '#1e2330', background: 'rgba(10,12,16,0.95)' }}>
      <div className="max-w-screen-2xl mx-auto px-4 py-3 flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded flex items-center justify-center" style={{ background: '#00e5ff15', border: '1px solid #00e5ff40' }}>
            <Shield size={16} style={{ color: '#00e5ff' }} />
          </div>
          <div>
            <div className="font-display font-bold text-lg" style={{ color: '#e2e8f0', letterSpacing: '-0.02em' }}>
              Vera<span style={{ color: '#00e5ff' }}>Check</span>
            </div>
            <div className="text-xs" style={{ color: '#4a5568', fontFamily: 'JetBrains Mono, monospace' }}>
              Vernacular Fact-Checker
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex items-center gap-1">
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className="flex items-center gap-2 px-3 py-1.5 rounded text-sm transition-all"
              style={{
                background: activeTab === id ? '#00e5ff15' : 'transparent',
                color: activeTab === id ? '#00e5ff' : '#718096',
                border: `1px solid ${activeTab === id ? '#00e5ff30' : 'transparent'}`,
              }}
            >
              <Icon size={14} />
              {label}
            </button>
          ))}
        </nav>

        {/* Status bar */}
        <div className="flex items-center gap-4">
          {metrics && (
            <div className="hidden md:flex items-center gap-4 text-xs" style={{ fontFamily: 'JetBrains Mono, monospace', color: '#4a5568' }}>
              <span style={{ color: '#00e5ff' }}>
                {metrics.throughput_rps?.toFixed(1) || '0.0'} req/s
              </span>
              <span>
                {metrics.avg_latency_ms?.toFixed(0) || '0'}ms avg
              </span>
              <span style={{ color: '#00ff88' }}>
                {metrics.llm_skip_rate?.toFixed(0) || '0'}% LLM skip
              </span>
            </div>
          )}

          {/* Feed toggle */}
          <button
            onClick={feedRunning ? onStopFeed : onStartFeed}
            className="flex items-center gap-2 px-3 py-1.5 rounded text-xs font-medium transition-all"
            style={{
              background: feedRunning ? '#00ff8815' : '#1e2330',
              color: feedRunning ? '#00ff88' : '#718096',
              border: `1px solid ${feedRunning ? '#00ff8830' : '#1e2330'}`,
            }}
          >
            {feedRunning ? (
              <><span className="live-dot" /><Radio size={12} /> LIVE</>
            ) : (
              <><Zap size={12} /> START FEED</>
            )}
          </button>
        </div>
      </div>
    </header>
  );
}
