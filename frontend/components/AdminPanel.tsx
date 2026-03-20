import { useState, useEffect } from 'react';
import { Plus, Trash2, Download, RefreshCw, Settings } from 'lucide-react';
import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then(r => r.json());

type Props = { apiBase: string };

export default function AdminPanel({ apiBase }: Props) {
  const { data: factsData, mutate } = useSWR(`${apiBase}/api/v1/facts/`, fetcher);
  const { data: configData } = useSWR(`${apiBase}/api/v1/admin/config`, fetcher);

  const [newFact, setNewFact] = useState({ text: '', verdict: 'TRUE', source: '', category: '' });
  const [adding, setAdding] = useState(false);
  const [msg, setMsg] = useState('');

  const addFact = async () => {
    if (!newFact.text || !newFact.source) return;
    setAdding(true);
    try {
      await fetch(`${apiBase}/api/v1/facts/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newFact),
      });
      setMsg('Fact added and index rebuilt!');
      setNewFact({ text: '', verdict: 'TRUE', source: '', category: '' });
      mutate();
    } catch (e) {
      setMsg('Error adding fact.');
    }
    setAdding(false);
    setTimeout(() => setMsg(''), 3000);
  };

  const deleteFact = async (id: string) => {
    await fetch(`${apiBase}/api/v1/facts/${id}`, { method: 'DELETE' });
    mutate();
  };

  const exportCSV = () => {
    window.open(`${apiBase}/api/v1/admin/export/csv`, '_blank');
  };

  const verdictColors: Record<string, string> = {
    TRUE: '#00ff88', FALSE: '#ff3366', MISLEADING: '#ffcc00', UNVERIFIED: '#718096',
  };

  return (
    <div className="mt-4 space-y-4">
      <div className="flex items-center gap-3">
        <Settings size={16} style={{ color: '#00e5ff' }} />
        <h2 className="text-lg font-semibold" style={{ color: '#e2e8f0' }}>Admin Panel</h2>
        <button onClick={exportCSV} className="ml-auto flex items-center gap-1.5 text-xs px-3 py-1.5 rounded"
          style={{ background: '#1e2330', color: '#a0aec0', border: '1px solid #2d3748' }}>
          <Download size={12} /> Export CSV
        </button>
      </div>

      {/* Config display */}
      {configData && (
        <div className="vera-panel p-4">
          <p className="text-sm font-medium mb-3" style={{ color: '#a0aec0' }}>Pipeline Configuration</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(configData).map(([k, v]) => (
              <div key={k} className="p-2 rounded" style={{ background: '#070809', border: '1px solid #1e2330' }}>
                <p className="text-xs" style={{ color: '#4a5568' }}>{k.replace(/_/g, ' ')}</p>
                <p className="text-xs font-mono mt-0.5" style={{ color: '#00e5ff' }}>{String(v)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Add fact */}
      <div className="vera-panel p-4">
        <p className="text-sm font-medium mb-3" style={{ color: '#a0aec0' }}>Add Verified Fact</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <textarea
            value={newFact.text}
            onChange={e => setNewFact({ ...newFact, text: e.target.value })}
            placeholder="Fact text..."
            rows={3}
            className="px-3 py-2 rounded text-sm resize-none outline-none"
            style={{ background: '#070809', border: '1px solid #1e2330', color: '#e2e8f0' }}
          />
          <div className="space-y-2">
            <select
              value={newFact.verdict}
              onChange={e => setNewFact({ ...newFact, verdict: e.target.value })}
              className="w-full px-3 py-2 rounded text-sm outline-none"
              style={{ background: '#070809', border: '1px solid #1e2330', color: '#e2e8f0' }}
            >
              {['TRUE', 'FALSE', 'MISLEADING', 'UNVERIFIED'].map(v => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
            <input
              value={newFact.source}
              onChange={e => setNewFact({ ...newFact, source: e.target.value })}
              placeholder="Source (e.g. WHO, ISRO)"
              className="w-full px-3 py-2 rounded text-sm outline-none"
              style={{ background: '#070809', border: '1px solid #1e2330', color: '#e2e8f0' }}
            />
            <input
              value={newFact.category}
              onChange={e => setNewFact({ ...newFact, category: e.target.value })}
              placeholder="Category (optional)"
              className="w-full px-3 py-2 rounded text-sm outline-none"
              style={{ background: '#070809', border: '1px solid #1e2330', color: '#e2e8f0' }}
            />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={addFact}
            disabled={adding || !newFact.text || !newFact.source}
            className="flex items-center gap-2 px-4 py-2 rounded text-sm font-medium"
            style={{ background: '#00e5ff', color: '#0a0c10', opacity: adding ? 0.6 : 1 }}
          >
            <Plus size={14} /> {adding ? 'Adding…' : 'Add Fact'}
          </button>
          {msg && <span className="text-xs" style={{ color: '#00ff88' }}>{msg}</span>}
        </div>
      </div>

      {/* Facts list */}
      <div className="vera-panel">
        <div className="px-4 py-3 border-b flex items-center justify-between" style={{ borderColor: '#1e2330' }}>
          <p className="text-sm font-medium" style={{ color: '#a0aec0' }}>
            Fact Database ({factsData?.total || 0} facts)
          </p>
          <button onClick={() => mutate()}>
            <RefreshCw size={14} style={{ color: '#4a5568' }} />
          </button>
        </div>
        <div className="overflow-auto" style={{ maxHeight: '400px' }}>
          {(factsData?.facts || []).map((fact: any) => (
            <div key={fact.id} className="flex items-start gap-3 px-4 py-3 border-b"
              style={{ borderColor: '#1e2330' }}>
              <span className="text-xs px-1.5 py-0.5 rounded font-mono flex-shrink-0 mt-0.5"
                style={{ background: `${verdictColors[fact.verdict]}15`, color: verdictColors[fact.verdict] }}>
                {fact.verdict}
              </span>
              <p className="text-sm flex-1" style={{ color: '#a0aec0' }}>{fact.text}</p>
              <span className="text-xs flex-shrink-0" style={{ color: '#4a5568' }}>{fact.source}</span>
              <button onClick={() => deleteFact(fact.id)} className="flex-shrink-0 p-1 rounded hover:bg-red-900/20">
                <Trash2 size={12} style={{ color: '#4a5568' }} />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
