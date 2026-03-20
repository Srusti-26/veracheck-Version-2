import { TrendingUp, AlertTriangle, XCircle } from 'lucide-react';
import type { FeedPost } from '../pages/index';

const VERDICT_COLOR: Record<string, string> = {
  TRUE: '#00ff88', FALSE: '#ff3366', MISLEADING: '#ffcc00', UNVERIFIED: '#718096',
};

type Props = { posts: FeedPost[] };

export default function TrendingPanel({ posts }: Props) {
  const withResults = posts.filter(p => p.result);

  // Verdict counts
  const counts: Record<string, number> = { TRUE: 0, FALSE: 0, MISLEADING: 0, UNVERIFIED: 0 };
  withResults.forEach(p => {
    const v = p.result!.verdict;
    counts[v] = (counts[v] || 0) + 1;
  });
  const total = withResults.length || 1;

  // Top false/misleading claims by confidence
  const flagged = withResults
    .filter(p => p.result!.verdict === 'FALSE' || p.result!.verdict === 'MISLEADING')
    .sort((a, b) => b.result!.confidence - a.result!.confidence)
    .slice(0, 5);

  return (
    <div className="vera-panel p-4 space-y-4">
      <div className="flex items-center gap-2">
        <TrendingUp size={14} style={{ color: '#ff9500' }} />
        <span className="text-sm font-medium" style={{ color: '#a0aec0' }}>Trending Analysis</span>
        <span className="text-xs ml-auto font-mono" style={{ color: '#4a5568' }}>{withResults.length} claims</span>
      </div>

      {/* Verdict distribution bars */}
      <div className="space-y-2">
        {Object.entries(counts).map(([verdict, count]) => {
          const pct = (count / total) * 100;
          const color = VERDICT_COLOR[verdict];
          return (
            <div key={verdict}>
              <div className="flex justify-between text-xs mb-1">
                <span style={{ color }}>{verdict}</span>
                <span className="font-mono" style={{ color: '#4a5568' }}>{count} ({pct.toFixed(0)}%)</span>
              </div>
              <div className="h-1.5 rounded-full" style={{ background: '#1e2330' }}>
                <div className="h-full rounded-full transition-all duration-500"
                  style={{ width: `${pct}%`, background: color }} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Top flagged claims */}
      {flagged.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={12} style={{ color: '#ffcc00' }} />
            <span className="text-xs" style={{ color: '#718096' }}>Top Flagged Claims</span>
          </div>
          <div className="space-y-1.5">
            {flagged.map((post, i) => {
              const color = VERDICT_COLOR[post.result!.verdict];
              return (
                <div key={i} className="rounded px-2 py-1.5 flex items-start gap-2"
                  style={{ background: `${color}08`, border: `1px solid ${color}20` }}>
                  <XCircle size={10} style={{ color, marginTop: 3, flexShrink: 0 }} />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs leading-snug" style={{ color: '#cbd5e0' }}>
                      {post.text.length > 80 ? post.text.slice(0, 80) + '…' : post.text}
                    </p>
                    <div className="flex gap-2 mt-0.5">
                      <span className="text-xs font-mono" style={{ color }}>
                        {post.result!.verdict} {(post.result!.confidence * 100).toFixed(0)}%
                      </span>
                      <span className="text-xs" style={{ color: '#4a5568' }}>{post.source}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
