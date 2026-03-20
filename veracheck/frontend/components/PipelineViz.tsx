import { Zap, Brain, Cpu } from 'lucide-react';

type Props = { metrics?: any };

const stages = [
  {
    num: 1, label: 'Auto-Classify', sub: 'Vector Similarity', icon: Zap,
    color: '#00ff88', key: 'stage1_pct', desc: 'cos_sim ≥ 0.88',
  },
  {
    num: 2, label: 'Heuristic', sub: 'Rule-Based', icon: Cpu,
    color: '#00e5ff', key: 'stage2_pct', desc: 'cos_sim ≥ 0.65',
  },
  {
    num: 3, label: 'LLM Verify', sub: 'flan-t5 / Mistral', icon: Brain,
    color: '#ff9500', key: 'stage3_pct', desc: 'cos_sim < 0.65',
  },
];

export default function PipelineViz({ metrics }: Props) {
  return (
    <div className="vera-panel p-4">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-sm font-medium" style={{ color: '#a0aec0' }}>Pipeline Optimization</span>
        {metrics && (
          <span className="text-xs ml-auto font-mono" style={{ color: '#00ff88' }}>
            {metrics.llm_skip_rate?.toFixed(1) || '0'}% LLM bypass rate
          </span>
        )}
      </div>

      <div className="flex items-stretch gap-0">
        {stages.map((stage, idx) => {
          const pct = metrics?.[stage.key] ?? (idx === 0 ? 70 : idx === 1 ? 20 : 10);
          const Icon = stage.icon;
          return (
            <div key={stage.num} className="flex items-stretch flex-1">
              <div
                className="flex-1 rounded-lg p-3 relative overflow-hidden"
                style={{
                  background: `${stage.color}08`,
                  border: `1px solid ${stage.color}25`,
                }}
              >
                {/* Fill bar */}
                <div
                  className="absolute bottom-0 left-0 right-0 transition-all duration-1000"
                  style={{
                    height: `${pct}%`,
                    background: `linear-gradient(to top, ${stage.color}18, transparent)`,
                  }}
                />
                <div className="relative z-10">
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-5 h-5 rounded flex items-center justify-center"
                      style={{ background: `${stage.color}20` }}>
                      <Icon size={11} style={{ color: stage.color }} />
                    </div>
                    <span className="text-xs font-semibold" style={{ color: stage.color }}>
                      S{stage.num}
                    </span>
                    <span className="text-xs font-mono ml-auto" style={{ color: stage.color }}>
                      {pct.toFixed(1)}%
                    </span>
                  </div>
                  <p className="text-xs font-medium" style={{ color: '#e2e8f0' }}>{stage.label}</p>
                  <p className="text-xs" style={{ color: '#4a5568' }}>{stage.sub}</p>
                  <p className="text-xs mt-1 font-mono" style={{ color: '#4a5568', fontSize: '0.65rem' }}>
                    {stage.desc}
                  </p>
                </div>
              </div>
              {idx < stages.length - 1 && (
                <div className="flex items-center px-1.5" style={{ color: '#1e2330', fontSize: '1.2rem' }}>
                  →
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Cost savings bar */}
      {metrics && (
        <div className="mt-3 pt-3 border-t flex items-center gap-4 text-xs"
          style={{ borderColor: '#1e2330', color: '#4a5568', fontFamily: 'monospace' }}>
          <span>Naive GPT-4 cost: <span style={{ color: '#ff3366' }}>${metrics.naive_cost_usd?.toFixed(4) || '0.0000'}</span></span>
          <span>Actual cost: <span style={{ color: '#00ff88' }}>${metrics.actual_cost_usd?.toFixed(6) || '0.000000'}</span></span>
          <span className="ml-auto" style={{ color: '#00ff88' }}>
            Saved: ${metrics.estimated_cost_saved_usd?.toFixed(4) || '0.0000'}
          </span>
        </div>
      )}
    </div>
  );
}
