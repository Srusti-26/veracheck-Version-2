import { useState } from 'react';
import { Search, Loader, ChevronRight } from 'lucide-react';
import type { CheckResult } from '../pages/index';

const EXAMPLE_CLAIMS = [
  "5G towers spread coronavirus disease",
  "Chandrayaan-3 successfully landed on moon in 2023",
  "भारत 28 राज्यों से मिलकर बना है",
  "COVID vaccines contain tracking microchips",
  "India is the most populous country in 2023",
];

type Props = {
  onCheck: (text: string) => Promise<CheckResult>;
  expanded?: boolean;
};

export default function CheckerInput({ onCheck, expanded }: Props) {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleCheck = async () => {
    if (!text.trim() || loading) return;
    setLoading(true);
    setError('');
    try {
      await onCheck(text.trim());
    } catch (e) {
      setError('Failed to connect to API. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleCheck();
    }
  };

  return (
    <div className="vera-panel p-4 mt-4" style={{ borderColor: '#1e2330' }}>
      <div className="flex items-center gap-2 mb-3">
        <Search size={14} style={{ color: '#00e5ff' }} />
        <span className="text-sm font-medium" style={{ color: '#a0aec0' }}>
          Fact Check a Claim
        </span>
        <span className="text-xs ml-auto" style={{ color: '#4a5568', fontFamily: 'monospace' }}>
          Hindi · Kannada · Tamil · English · Hinglish
        </span>
      </div>

      <div className="flex gap-2">
        <textarea
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Enter a claim in any language... (e.g. '5G towers cause COVID', 'भारत में 28 राज्य हैं')"
          rows={expanded ? 4 : 2}
          className="flex-1 rounded px-3 py-2 text-sm resize-none outline-none transition-all"
          style={{
            background: '#070809',
            border: '1px solid #1e2330',
            color: '#e2e8f0',
            fontFamily: 'IBM Plex Sans, sans-serif',
          }}
          onFocus={e => e.target.style.borderColor = '#00e5ff40'}
          onBlur={e => e.target.style.borderColor = '#1e2330'}
        />
        <button
          onClick={handleCheck}
          disabled={!text.trim() || loading}
          className="px-4 rounded flex items-center gap-2 text-sm font-medium transition-all"
          style={{
            background: text.trim() && !loading ? '#00e5ff' : '#1e2330',
            color: text.trim() && !loading ? '#0a0c10' : '#4a5568',
            minWidth: '100px',
          }}
        >
          {loading ? (
            <><Loader size={14} className="animate-spin" /> Checking</>
          ) : (
            <><ChevronRight size={14} /> Check</>
          )}
        </button>
      </div>

      {error && (
        <p className="text-xs mt-2" style={{ color: '#ff3366' }}>{error}</p>
      )}

      {/* Example claims */}
      <div className="mt-3 flex flex-wrap gap-2">
        {EXAMPLE_CLAIMS.map(claim => (
          <button
            key={claim}
            onClick={() => setText(claim)}
            className="text-xs px-2 py-1 rounded transition-all"
            style={{ background: '#1e2330', color: '#718096', border: '1px solid #2d3748' }}
          >
            {claim.length > 40 ? claim.slice(0, 40) + '…' : claim}
          </button>
        ))}
      </div>
    </div>
  );
}
