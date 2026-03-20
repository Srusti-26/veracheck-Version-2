import { useState } from 'react';
import { Radio, MessageSquare, Globe, Clock } from 'lucide-react';
import type { FeedPost } from '../pages/index';

const LANG_FLAG: Record<string, string> = {
  hi: '🇮🇳 HI', kn: '🇮🇳 KN', ta: '🇮🇳 TA', te: '🇮🇳 TE',
  en: '🌐 EN', mr: '🇮🇳 MR', bn: '🇮🇳 BN',
};

const VERDICT_STYLE: Record<string, { bg: string; color: string; label: string }> = {
  TRUE:        { bg: '#00ff8818', color: '#00ff88', label: '✓ TRUE' },
  FALSE:       { bg: '#ff336618', color: '#ff3366', label: '✗ FALSE' },
  MISLEADING:  { bg: '#ffcc0018', color: '#ffcc00', label: '⚠ MISLEAD' },
  UNVERIFIED:  { bg: '#71809618', color: '#718096', label: '? UNVERIFIED' },
};

type Props = {
  posts: FeedPost[];
  onSelectPost: (post: FeedPost) => void;
};

export default function LiveFeedPanel({ posts, onSelectPost }: Props) {
  const [filter, setFilter] = useState<string>('ALL');
  const verdicts = ['ALL', 'FALSE', 'MISLEADING', 'TRUE', 'UNVERIFIED'];

  const filtered = filter === 'ALL'
    ? posts
    : posts.filter(p => p.result?.verdict === filter);

  return (
    <div className="vera-panel flex flex-col" style={{ height: '520px' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: '#1e2330' }}>
        <div className="flex items-center gap-2">
          <span className="live-dot" />
          <Radio size={14} style={{ color: '#00ff88' }} />
          <span className="text-sm font-medium" style={{ color: '#e2e8f0' }}>Live Feed</span>
          <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: '#1e2330', color: '#4a5568', fontFamily: 'monospace' }}>
            {posts.length}
          </span>
        </div>
        {/* Filter pills */}
        <div className="flex gap-1">
          {verdicts.map(v => (
            <button
              key={v}
              onClick={() => setFilter(v)}
              className="text-xs px-2 py-0.5 rounded transition-all"
              style={{
                background: filter === v ? (VERDICT_STYLE[v]?.bg || '#00e5ff15') : '#1e2330',
                color: filter === v ? (VERDICT_STYLE[v]?.color || '#00e5ff') : '#4a5568',
                border: `1px solid ${filter === v ? (VERDICT_STYLE[v]?.color || '#00e5ff') + '40' : 'transparent'}`,
              }}
            >
              {v}
            </button>
          ))}
        </div>
      </div>

      {/* Posts list */}
      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-3" style={{ color: '#4a5568' }}>
            <MessageSquare size={32} strokeWidth={1} />
            <p className="text-sm">Waiting for posts…</p>
          </div>
        ) : (
          filtered.map(post => (
            <FeedItem
              key={post.id}
              post={post}
              onClick={() => onSelectPost(post)}
            />
          ))
        )}
      </div>
    </div>
  );
}

function FeedItem({ post, onClick }: { post: FeedPost; onClick: () => void }) {
  const verdict = post.result?.verdict;
  const vStyle = verdict ? VERDICT_STYLE[verdict] : null;
  const age = Math.floor((Date.now() / 1000) - post.timestamp);

  return (
    <div
      onClick={onClick}
      className="px-4 py-3 border-b cursor-pointer transition-all hover:bg-opacity-50 animate-slide-in"
      style={{
        borderColor: '#1e2330',
        borderLeft: vStyle ? `2px solid ${vStyle.color}` : '2px solid transparent',
        background: onClick ? 'transparent' : undefined,
      }}
      onMouseEnter={e => (e.currentTarget.style.background = '#0f1117')}
      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm leading-snug flex-1" style={{ color: '#cbd5e0' }}>
          {post.text.length > 100 ? post.text.slice(0, 100) + '…' : post.text}
        </p>
        {vStyle && (
          <span className="text-xs px-1.5 py-0.5 rounded whitespace-nowrap flex-shrink-0 font-mono"
            style={{ background: vStyle.bg, color: vStyle.color }}>
            {vStyle.label}
          </span>
        )}
      </div>
      <div className="flex items-center gap-3 mt-1.5">
        <span className="text-xs" style={{ color: '#4a5568' }}>
          <Globe size={10} className="inline mr-0.5" />
          {LANG_FLAG[post.language] || post.language.toUpperCase()}
        </span>
        <span className="text-xs" style={{ color: '#4a5568' }}>{post.source}</span>
        {post.result && (
          <>
            <span className="text-xs" style={{ color: '#4a5568', fontFamily: 'monospace' }}>
              {post.result.latency_ms.toFixed(0)}ms
            </span>
            <span className="text-xs" style={{
              color: post.result.pipeline_stage === 'STAGE1_AUTO' ? '#00ff88'
                   : post.result.pipeline_stage === 'STAGE2_HEURISTIC' ? '#00e5ff'
                   : '#ff9500'
            }}>
              S{post.result.pipeline_stage.slice(5, 6)}
            </span>
          </>
        )}
        <span className="text-xs ml-auto" style={{ color: '#4a5568' }}>
          <Clock size={10} className="inline mr-0.5" />
          {age < 60 ? `${age}s` : `${Math.floor(age / 60)}m`}
        </span>
      </div>
    </div>
  );
}
