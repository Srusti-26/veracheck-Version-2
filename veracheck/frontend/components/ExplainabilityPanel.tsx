import { BookOpen, ExternalLink, Globe, Wifi } from 'lucide-react';
import type { CheckResult } from '../pages/index';

const VERDICT_COLOR: Record<string, string> = {
  TRUE: '#00ff88', FALSE: '#ff3366', MISLEADING: '#ffcc00', UNVERIFIED: '#718096',
};

const VERDICT_DESC: Record<string, string> = {
  TRUE:       'Verified correct',
  FALSE:      'Confirmed false',
  MISLEADING: 'Partially true / out of context',
  UNVERIFIED: 'No strong evidence',
};

type Props = { result: CheckResult };

export default function ExplainabilityPanel({ result }: Props) {
  if (!result.retrieved_facts?.length) return null;

  return (
    <div className="vera-panel p-4">
      <div className="flex items-center gap-2 mb-4">
        <BookOpen size={14} style={{ color: '#00e5ff' }} />
        <span className="text-sm font-medium" style={{ color: '#a0aec0' }}>Evidence &amp; Explainability</span>
      </div>

      {/* Top row: Translation + Wikipedia side by side */}
      {(result.translation?.was_translated || result.wikipedia_summary) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 mb-4">
          {result.translation?.was_translated && (
            <div className="rounded-lg p-3" style={{ background: '#00e5ff08', border: '1px solid #00e5ff20' }}>
              <div className="flex items-center gap-2 mb-2">
                <Globe size={12} style={{ color: '#00e5ff' }} />
                <span className="text-xs font-medium" style={{ color: '#00e5ff' }}>
                  Translation: {result.translation.source_language_name} → English
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded p-2" style={{ background: '#0a0c10' }}>
                  <p className="text-xs mb-1" style={{ color: '#4a5568' }}>
                    Original ({result.translation.source_language.toUpperCase()})
                  </p>
                  <p className="text-sm leading-snug" style={{ color: '#e2e8f0' }}>
                    {result.translation.original_text}
                  </p>
                </div>
                <div className="rounded p-2" style={{ background: '#0a0c10' }}>
                  <p className="text-xs mb-1" style={{ color: '#4a5568' }}>English</p>
                  <p className="text-sm leading-snug" style={{ color: '#e2e8f0' }}>
                    {result.translation.translated_text}
                  </p>
                </div>
              </div>
            </div>
          )}

          {result.wikipedia_summary && (
            <div className="rounded-lg p-3" style={{ background: '#ffffff05', border: '1px solid #2d3748' }}>
              <div className="flex items-center gap-2 mb-2">
                <Wifi size={12} style={{ color: '#a0aec0' }} />
                <span className="text-xs font-medium" style={{ color: '#a0aec0' }}>Wikipedia Cross-Reference</span>
                <span className="text-xs ml-auto" style={{ color: '#4a5568' }}>free API</span>
              </div>
              <p className="text-sm leading-relaxed" style={{ color: '#cbd5e0' }}>
                {result.wikipedia_summary}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Facts row — horizontal */}
      <div>
        <p className="text-xs mb-2" style={{ color: '#4a5568' }}>
          FAISS top-{result.retrieved_facts.length} matches from fact database
        </p>
        <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${result.retrieved_facts.length}, 1fr)` }}>
          {result.retrieved_facts.map((fact: any, i: number) => {
            const vColor = VERDICT_COLOR[fact.verdict?.toUpperCase()] || '#718096';
            const simPct = (fact.similarity * 100).toFixed(1);
            return (
              <div key={i} className="rounded-lg p-3"
                style={{ background: `${vColor}06`, border: `1px solid ${vColor}20` }}>
                {/* Verdict badge + similarity */}
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs px-1.5 py-0.5 rounded font-mono"
                    style={{ background: `${vColor}20`, color: vColor }}>
                    {fact.verdict?.toUpperCase() || '?'}
                  </span>
                  <span className="text-xs font-mono" style={{ color: vColor }}>{simPct}%</span>
                </div>
                {/* Fact text */}
                <p className="text-sm leading-snug mb-2" style={{ color: '#cbd5e0' }}>
                  {fact.text}
                </p>
                {/* Verdict description */}
                <p className="text-xs mb-2" style={{ color: '#4a5568' }}>
                  {VERDICT_DESC[fact.verdict?.toUpperCase()] || ''}
                </p>
                {/* Similarity bar */}
                <div className="h-1 rounded-full mb-2" style={{ background: '#1e2330' }}>
                  <div className="h-full rounded-full"
                    style={{ width: `${fact.similarity * 100}%`, background: vColor }} />
                </div>
                {/* Source + category */}
                <div className="flex items-center gap-2 text-xs" style={{ color: '#4a5568' }}>
                  <ExternalLink size={10} />
                  <span>{fact.source || 'Unknown'}</span>
                  {fact.category && (
                    <span className="px-1 rounded" style={{ background: '#1e2330' }}>
                      {fact.category}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
