import { Shield, CheckCircle, XCircle, AlertTriangle, HelpCircle, Globe, BookOpen } from 'lucide-react';
import type { CheckResult } from '../pages/index';

const VERDICT_CONFIG = {
  TRUE:       { icon: CheckCircle,   color: '#00ff88', bg: '#00ff8810', label: 'TRUE',        glow: '0 0 20px #00ff8830', desc: 'This claim is supported by verified facts.' },
  FALSE:      { icon: XCircle,       color: '#ff3366', bg: '#ff336610', label: 'FALSE',       glow: '0 0 20px #ff336630', desc: 'This claim contradicts verified facts or is known misinformation.' },
  MISLEADING: { icon: AlertTriangle, color: '#ffcc00', bg: '#ffcc0010', label: 'MISLEADING',  glow: '0 0 20px #ffcc0030', desc: 'This claim is partially true, out of context, or exaggerated.' },
  UNVERIFIED: { icon: HelpCircle,    color: '#718096', bg: '#71809610', label: 'UNVERIFIED',  glow: 'none',               desc: 'Insufficient evidence to confirm or deny this claim.' },
};

const STAGE_LABEL: Record<string, string> = {
  STAGE1_AUTO:      'Stage 1 — Auto (Vector)',
  STAGE2_HEURISTIC: 'Stage 2 — Heuristic',
  STAGE3_LLM:       'Stage 3 — LLM',
  CACHED:           'Cached Result',
};

const STAGE_COLOR: Record<string, string> = {
  STAGE1_AUTO:      '#00ff88',
  STAGE2_HEURISTIC: '#00e5ff',
  STAGE3_LLM:       '#ff9500',
  CACHED:           '#718096',
};

const TIER_CONFIG: Record<string, { color: string; label: string }> = {
  HIGH:   { color: '#00ff88', label: '● HIGH' },
  MEDIUM: { color: '#ffcc00', label: '● MEDIUM' },
  LOW:    { color: '#ff3366', label: '● LOW' },
};

const CATEGORY_LABEL: Record<string, string> = {
  NEAR_DUPLICATE:    '≈ Near Duplicate',
  NEGATION:          '⊘ Negation Detected',
  KEYWORD_MATCH:     '⚑ Keyword Match',
  MISLEADING_KEYWORD:'⚠ Misleading Pattern',
  WEIGHTED_VOTE:     '⊕ Weighted Vote',
  LLM_INFERRED:      '🤖 LLM Inferred',
  CACHED:            '⚡ Cached',
};

type Props = {
  result: CheckResult | null;
  recentResults: CheckResult[];
  onSelectResult: (r: CheckResult) => void;
};

export default function ResultsPanel({ result, recentResults, onSelectResult }: Props) {
  if (!result) {
    return (
      <div className="vera-panel flex items-center justify-center" style={{ height: '200px' }}>
        <div className="text-center" style={{ color: '#4a5568' }}>
          <Shield size={32} strokeWidth={1} className="mx-auto mb-2" />
          <p className="text-sm">Check a claim or click a feed item</p>
        </div>
      </div>
    );
  }

  const cfg = VERDICT_CONFIG[result.verdict] || VERDICT_CONFIG.UNVERIFIED;
  const Icon = cfg.icon;
  const tier = TIER_CONFIG[result.confidence_tier] || TIER_CONFIG.MEDIUM;

  return (
    <div className="vera-panel p-4 space-y-4" style={{ boxShadow: cfg.glow }}>

      {/* Translation box — shown prominently when translated */}
      {result.translation?.was_translated && (
        <div className="rounded-lg px-3 py-2.5" style={{ background: '#00e5ff08', border: '1px solid #00e5ff25' }}>
          <div className="flex items-center gap-2 mb-1">
            <Globe size={12} style={{ color: '#00e5ff' }} />
            <span className="text-xs font-medium" style={{ color: '#00e5ff' }}>
              Translated from {result.translation.source_language_name} → English
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span style={{ color: '#4a5568' }}>Original ({result.translation.source_language.toUpperCase()})</span>
              <p className="mt-0.5 leading-snug" style={{ color: '#cbd5e0' }}>
                {result.translation.original_text.length > 100
                  ? result.translation.original_text.slice(0, 100) + '…'
                  : result.translation.original_text}
              </p>
            </div>
            <div>
              <span style={{ color: '#4a5568' }}>English</span>
              <p className="mt-0.5 leading-snug" style={{ color: '#cbd5e0' }}>
                {result.translation.translated_text.length > 100
                  ? result.translation.translated_text.slice(0, 100) + '…'
                  : result.translation.translated_text}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Verdict hero */}
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ background: cfg.bg, border: `1px solid ${cfg.color}30` }}>
          <Icon size={24} style={{ color: cfg.color }} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="text-lg font-bold font-display" style={{ color: cfg.color }}>
              {cfg.label}
            </span>
            {/* Confidence tier */}
            <span className="text-xs font-mono" style={{ color: tier.color }}>{tier.label}</span>
            {/* Pipeline stage */}
            <span className="text-xs px-2 py-0.5 rounded font-mono"
              style={{ background: '#1e2330', color: STAGE_COLOR[result.pipeline_stage] }}>
              {STAGE_LABEL[result.pipeline_stage] || result.pipeline_stage}
            </span>
            {/* Verdict category */}
            {result.verdict_category && CATEGORY_LABEL[result.verdict_category] && (
              <span className="text-xs px-2 py-0.5 rounded"
                style={{ background: `${cfg.color}15`, color: cfg.color, border: `1px solid ${cfg.color}25` }}>
                {CATEGORY_LABEL[result.verdict_category]}
              </span>
            )}
          </div>
          {/* Verdict description */}
          <p className="text-xs mb-1" style={{ color: '#718096' }}>{cfg.desc}</p>
          <p className="text-sm leading-snug" style={{ color: '#a0aec0' }}>
            {result.claim.length > 120 ? result.claim.slice(0, 120) + '…' : result.claim}
          </p>
        </div>
      </div>

      {/* Confidence bar */}
      <div>
        <div className="flex justify-between text-xs mb-1" style={{ color: '#718096' }}>
          <span>Confidence</span>
          <span className="font-mono" style={{ color: tier.color }}>
            {(result.confidence * 100).toFixed(1)}% ({result.confidence_tier})
          </span>
        </div>
        <div className="h-1.5 rounded-full" style={{ background: '#1e2330' }}>
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{ width: `${result.confidence * 100}%`, background: cfg.color }}
          />
        </div>
      </div>

      {/* Explanation */}
      <p className="text-sm leading-relaxed" style={{ color: '#a0aec0' }}>
        {result.explanation}
      </p>

      {/* Wikipedia evidence */}
      {result.wikipedia_summary && (
        <div className="rounded-lg px-3 py-2.5" style={{ background: '#ffffff06', border: '1px solid #2d3748' }}>
          <div className="flex items-center gap-2 mb-1">
            <BookOpen size={12} style={{ color: '#a0aec0' }} />
            <span className="text-xs font-medium" style={{ color: '#a0aec0' }}>Wikipedia Context</span>
          </div>
          <p className="text-xs leading-relaxed" style={{ color: '#718096' }}>
            {result.wikipedia_summary}
          </p>
        </div>
      )}

      {/* Meta row */}
      <div className="flex items-center gap-4 text-xs" style={{ color: '#4a5568', fontFamily: 'monospace' }}>
        <span>{result.latency_ms.toFixed(1)}ms</span>
        <span>sim: {(result.best_similarity * 100).toFixed(1)}%</span>
        <span style={{ color: '#4a5568' }}>{new Date(result.timestamp * 1000).toLocaleTimeString()}</span>
      </div>

      {/* Recent results strip */}
      {recentResults.length > 1 && (
        <div className="pt-3 border-t" style={{ borderColor: '#1e2330' }}>
          <p className="text-xs mb-2" style={{ color: '#4a5568' }}>Recent</p>
          <div className="flex gap-1.5 flex-wrap">
            {recentResults.slice(0, 8).map((r, i) => {
              const rc = VERDICT_CONFIG[r.verdict];
              return (
                <button
                  key={i}
                  onClick={() => onSelectResult(r)}
                  className="text-xs px-2 py-0.5 rounded transition-all"
                  style={{ background: rc.bg, color: rc.color, border: `1px solid ${rc.color}30` }}
                  title={r.claim}
                >
                  {rc.label}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
