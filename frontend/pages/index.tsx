import Head from 'next/head';
import { useState, useEffect, useRef, useCallback } from 'react';
import useSWR from 'swr';
import LiveFeedPanel from '../components/LiveFeedPanel';
import ResultsPanel from '../components/ResultsPanel';
import MetricsDashboard from '../components/MetricsDashboard';
import CheckerInput from '../components/CheckerInput';
import ExplainabilityPanel from '../components/ExplainabilityPanel';
import AdminPanel from '../components/AdminPanel';
import Header from '../components/Header';
import PipelineViz from '../components/PipelineViz';
import TrendingPanel from '../components/TrendingPanel';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const fetcher = (url: string) => fetch(url).then(r => r.json());

export type TranslationDetail = {
  original_text: string;
  translated_text: string;
  source_language: string;
  source_language_name: string;
  was_translated: boolean;
};

export type CheckResult = {
  claim: string;
  english_claim: string;
  detected_language: string;
  verdict: 'TRUE' | 'FALSE' | 'MISLEADING' | 'UNVERIFIED';
  confidence: number;
  confidence_tier: 'HIGH' | 'MEDIUM' | 'LOW';
  verdict_category: string;
  explanation: string;
  retrieved_facts: any[];
  best_similarity: number;
  pipeline_stage: string;
  latency_ms: number;
  timestamp: number;
  translation?: TranslationDetail;
  wikipedia_summary?: string;
};

export type FeedPost = {
  id: string;
  text: string;
  source: string;
  language: string;
  timestamp: number;
  result?: CheckResult;
};

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'checker' | 'admin'>('dashboard');
  const [feedPosts, setFeedPosts] = useState<FeedPost[]>([]);
  const [selectedResult, setSelectedResult] = useState<CheckResult | null>(null);
  const [feedRunning, setFeedRunning] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const [backendOnline, setBackendOnline] = useState(false);

  // Metrics polling
  const { data: metrics, mutate: refreshMetrics } = useSWR(
    `${API}/api/v1/metrics/snapshot`,
    fetcher,
    {
      refreshInterval: 2000,
      onSuccess: () => setBackendOnline(true),
      onError: () => setBackendOnline(false),
    }
  );

  // Load feed history on mount
  useEffect(() => {
    fetch(`${API}/api/v1/feed/history?limit=30`)
      .then(r => r.json())
      .then(data => {
        if (data.posts) setFeedPosts(data.posts);
      })
      .catch(() => {});
  }, []);

  const startFeed = useCallback(async () => {
    try {
      await fetch(`${API}/api/v1/feed/start`, { method: 'POST' });
    } catch {
      // backend not ready yet — SSE will still connect when it is
    }
    setFeedRunning(true);

    const es = new EventSource(`${API}/api/v1/feed/stream`);
    eventSourceRef.current = es;

    es.onmessage = (e) => {
      try {
        const post: FeedPost = JSON.parse(e.data);
        if (post.id) {
          setFeedPosts(prev => [post, ...prev.slice(0, 99)]);
        }
      } catch {}
    };
    es.onerror = () => setFeedRunning(false);
  }, []);

  const stopFeed = useCallback(async () => {
    try {
      await fetch(`${API}/api/v1/feed/stop`, { method: 'POST' });
    } catch {}
    eventSourceRef.current?.close();
    setFeedRunning(false);
  }, []);

  useEffect(() => {
    startFeed();
    return () => {
      eventSourceRef.current?.close();
    };
  }, [startFeed]);

  const handleManualCheck = async (text: string): Promise<CheckResult> => {
    const res = await fetch(`${API}/api/v1/claims/check`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    const result = await res.json();
    setSelectedResult(result);
    refreshMetrics();
    return result;
  };

  return (
    <>
      <Head>
        <title>VeraCheck — Real-Time Vernacular Fact-Checker</title>
        <meta name="description" content="AI-powered multilingual misinformation detection" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="min-h-screen grid-bg" style={{ background: '#0a0c10' }}>
        <Header
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          feedRunning={feedRunning}
          onStartFeed={startFeed}
          onStopFeed={stopFeed}
          metrics={metrics}
        />

        <main className="max-w-screen-2xl mx-auto px-4 pb-8">
          {/* Backend offline banner */}
          {!backendOnline && (
            <div className="mt-4 px-4 py-3 rounded-lg text-sm flex items-center gap-2"
              style={{ background: '#ff336615', border: '1px solid #ff336640', color: '#ff3366' }}>
              <span>⚠</span>
              <span>Backend not reachable at <code>{API}</code> — make sure the backend is running on port 12345.</span>
            </div>
          )}
          {activeTab === 'dashboard' && (
            <div className="space-y-4">
              {/* Top row: Checker input */}
              <CheckerInput onCheck={handleManualCheck} />

              {/* Pipeline visualization */}
              <PipelineViz metrics={metrics} />

              {/* Main content: 3 columns top, Explainability full-width below */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <LiveFeedPanel
                  posts={feedPosts}
                  onSelectPost={(post) => post.result && setSelectedResult(post.result)}
                />
                <ResultsPanel
                  result={selectedResult}
                  recentResults={feedPosts.filter(p => p.result).map(p => p.result!).slice(0, 10)}
                  onSelectResult={setSelectedResult}
                />
                <TrendingPanel posts={feedPosts} />
              </div>

              {/* Explainability — full width horizontal strip */}
              {selectedResult && (
                <ExplainabilityPanel result={selectedResult} />
              )}

              {/* Metrics at the bottom */}
              <MetricsDashboard metrics={metrics} />
            </div>
          )}

          {activeTab === 'checker' && (
            <div className="max-w-2xl mx-auto mt-8">
              <CheckerInput onCheck={handleManualCheck} expanded />
              {selectedResult && (
                <div className="mt-4 space-y-4">
                  <ResultsPanel
                    result={selectedResult}
                    recentResults={[]}
                    onSelectResult={setSelectedResult}
                  />
                  <ExplainabilityPanel result={selectedResult} />
                </div>
              )}
            </div>
          )}

          {activeTab === 'admin' && (
            <AdminPanel apiBase={API} />
          )}
        </main>
      </div>
    </>
  );
}
