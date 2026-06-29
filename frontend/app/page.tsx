"use client";

import { useEffect, useState } from "react";
import PublicResultView from "./components/PublicResultView";
import NewsroomResultView from "./components/NewsroomResultView";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

const LOADING_STEPS = [
  "Classifying input parameters (Router Agent)...",
  "Spawning targeted search queries (Scout Agent)...",
  "Collecting search results from Tavily MCP...",
  "Running cross-referencing claim analysis (Verifier Agent)...",
  "Isolating opinions and identifying contradictions...",
  "Computing trust score and generating analytical brief (Scorer)...",
];

const EXAMPLES = [
  {
    title: "Vaccine rumor fact-check",
    text: "Is it true that the new H5N1 vaccine causes immediate long-term fertility issues in young adults?",
    type: "Fact-Check",
    icon: (
      <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
  },
  {
    title: "EU AI Regulation updates",
    text: "monitoring the implementation of the European Union AI Act and its impact on open source models in 2026",
    type: "Topic Monitor",
    icon: (
      <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
      </svg>
    ),
  },
  {
    title: "Climate crop yields 2026",
    text: "climate change impact on crop yields and grain production across East Africa and Europe in 2026",
    type: "Topic Monitor",
    icon: (
      <svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.055 11H5a2 2 0 01-2 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 002 2h1.5A1.5 1.5 0 0018 10.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
];

interface SourceUsed {
  url: string;
  title: string;
}

interface PublicResult {
  input_verdict: "true" | "false" | "unverified" | "mixed";
  trust_score: number;
  explanation: string;
}

interface NewsroomResult {
  brief: string;
}

interface AnalyzeResponse {
  mode: "public" | "newsroom";
  result: PublicResult | NewsroomResult;
  sources_used: SourceUsed[];
  detected_language: string;
}

export default function Home() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [response, setResponse] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submittedInput, setSubmittedInput] = useState("");
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed) return;

    setLoading(true);
    setResponse(null);
    setError(null);
    setLoadingStep(0);
    setSubmittedInput(trimmed);

    // Rotate loading messages every 5s
    const interval = setInterval(() => {
      setLoadingStep((prev) =>
        prev < LOADING_STEPS.length - 1 ? prev + 1 : prev
      );
    }, 5000);

    try {
      const res = await fetch(`${API_URL}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ input: trimmed }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        const detail = body?.detail || `Server error (${res.status})`;
        throw new Error(detail);
      }

      const data: AnalyzeResponse = await res.json();
      setResponse(data);
    } catch (err) {
      if (err instanceof TypeError && err.message.includes("fetch")) {
        setError(
          "Could not reach the backend server. Make sure the API is running on " +
            API_URL
        );
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred.");
      }
    } finally {
      clearInterval(interval);
      setLoading(false);
    }
  }

  function handleReset() {
    setInput("");
    setResponse(null);
    setError(null);
    setSubmittedInput("");
  }

  return (
    <div className="flex flex-col min-h-screen bg-[#080c14] text-slate-100 font-sans selection:bg-blue-600/40 selection:text-white">
      {/* Top Header */}
      <header className="sticky top-0 z-50 w-full bg-[#080c14]/80 backdrop-blur-md border-b border-slate-800">
        <div className="mx-auto max-w-5xl px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl overflow-hidden border border-slate-800 shadow-lg shadow-blue-500/10 flex-shrink-0">
              <img src="/logo.jpg" alt="TrustLens Logo" className="w-full h-full object-cover" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
                TrustLens
              </h1>
              <p className="text-[10px] text-slate-400 tracking-wide font-medium uppercase">
                AI verification dashboard
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="hidden sm:flex items-center gap-2 bg-slate-900/80 px-3 py-1.5 rounded-lg border border-slate-800">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-xs text-slate-400 font-mono">ADK PIPELINE READY</span>
            </div>
            {response && (
              <button
                onClick={handleReset}
                className="inline-flex items-center gap-2 text-sm text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 font-semibold px-4 py-2 rounded-xl transition-all shadow-md shadow-blue-950/20"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                </svg>
                New Analysis
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="w-full max-w-5xl mx-auto px-6 py-10 flex-1 flex flex-col justify-start">
        
        {/* Verification Form (Initial view) */}
        {!response && !loading && (
          <div className="my-auto max-w-3xl mx-auto w-full animate-fade-in">
            <div className="text-center mb-8 flex flex-col items-center">
              <div className="w-20 h-20 rounded-2xl overflow-hidden border border-slate-800 shadow-xl shadow-blue-500/10 mb-4 hover:scale-105 transition-all duration-300">
                <img src="/logo.jpg" alt="TrustLens Icon" className="w-full h-full object-cover" />
              </div>
              <span className="px-3 py-1 text-xs font-semibold text-blue-400 bg-blue-950/50 rounded-full border border-blue-900/80 inline-block mb-3">
                SECURE SOURCE VERIFICATION
              </span>
              <h2 className="text-4xl sm:text-5xl font-extrabold text-white tracking-tight leading-none mb-3">
                Verify Information Instantly
              </h2>
              <p className="text-slate-400 text-base sm:text-lg max-w-xl mx-auto">
                Paste an article, state a claim, or specify a geopolitical topic. TrustLens chains multiple agents to cross-examine and score credibility.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="relative glass-panel rounded-2xl p-6 glow-glow transition-all duration-300">
              <div className="relative">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Paste article text / URL / claim or input monitoring query..."
                  rows={6}
                  maxLength={10000}
                  className="w-full rounded-xl border border-slate-700 bg-[#0c101c]/90 px-4 py-3.5 text-base text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-all resize-none font-sans"
                />
              </div>

              <div className="mt-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <span className="text-xs text-slate-500 font-mono">
                  {input.length.toLocaleString()} / 10,000 characters
                </span>
                
                <button
                  type="submit"
                  disabled={mounted ? !input.trim() || loading : false}
                  className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-8 py-3 text-sm font-bold text-white shadow-lg shadow-blue-500/10 hover:from-blue-500 hover:to-indigo-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-200"
                >
                  Start Pipeline Analysis
                </button>
              </div>
            </form>

            {/* Quick Examples */}
            <div className="mt-12">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider text-center mb-4">
                Or choose an analytical template
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {EXAMPLES.map((ex, idx) => (
                  <button
                    key={idx}
                    onClick={() => setInput(ex.text)}
                    className="glass-panel text-left p-4 rounded-xl hover:bg-[#1f273d]/50 hover:border-slate-600 transition-all duration-200 group flex flex-col justify-between h-full"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="p-1.5 rounded-lg bg-slate-900 border border-slate-800">
                          {ex.icon}
                        </span>
                        <span className={`text-[10px] px-2 py-0.5 rounded font-mono font-semibold ${
                          ex.type === "Fact-Check" 
                            ? "bg-emerald-950/80 text-emerald-400 border border-emerald-900" 
                            : "bg-blue-950/80 text-blue-400 border border-blue-900"
                        }`}>
                          {ex.type}
                        </span>
                      </div>
                      <h4 className="text-sm font-bold text-slate-200 mb-1 group-hover:text-blue-400 transition-colors">
                        {ex.title}
                      </h4>
                      <p className="text-xs text-slate-400 line-clamp-3 leading-relaxed">
                        &ldquo;{ex.text}&rdquo;
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Dynamic Scanning/Loading state */}
        {loading && (
          <div className="mt-12 max-w-xl w-full mx-auto animate-pulse-slow">
            <div className="glass-panel rounded-2xl p-6 border border-slate-800 shadow-2xl relative overflow-hidden shimmer-effect">
              
              <div className="flex items-center gap-3 mb-6">
                <div className="w-8 h-8 rounded-lg bg-blue-900/60 border border-blue-700/50 flex items-center justify-center flex-shrink-0">
                  <svg className="w-4.5 h-4.5 text-blue-400 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">TrustLens System Analyzer</h3>
                  <p className="text-xs text-slate-400 font-mono">Running pipeline execution</p>
                </div>
              </div>

              {/* Progress bar */}
              <div className="h-1.5 w-full bg-slate-900 rounded-full overflow-hidden mb-6 border border-slate-800">
                <div
                  className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-1000 ease-out"
                  style={{
                    width: `${((loadingStep + 1) / LOADING_STEPS.length) * 100}%`,
                  }}
                />
              </div>

              {/* Step messages */}
              <div className="space-y-3 font-mono">
                {LOADING_STEPS.map((step, i) => (
                  <div
                    key={step}
                    className={`flex items-start gap-3 text-xs transition-all duration-500 ${
                      i <= loadingStep ? "opacity-100" : "opacity-15"
                    }`}
                  >
                    <div
                      className={`w-5 h-5 rounded flex items-center justify-center flex-shrink-0 border mt-0.5 ${
                        i < loadingStep
                          ? "bg-emerald-950/80 border-emerald-900 text-emerald-400"
                          : i === loadingStep
                            ? "bg-blue-950/80 border-blue-900 text-blue-400"
                            : "bg-slate-900 border-slate-800 text-slate-600"
                      }`}
                    >
                      {i < loadingStep ? (
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                      ) : i === loadingStep ? (
                        <span className="w-1.5 h-1.5 bg-blue-400 rounded-full progress-step" />
                      ) : (
                        <span className="w-1 h-1 bg-slate-600 rounded-full" />
                      )}
                    </div>
                    <span
                      className={
                        i === loadingStep
                          ? "text-blue-300 font-bold"
                          : i < loadingStep
                            ? "text-slate-400"
                            : "text-slate-500"
                      }
                    >
                      {i === loadingStep ? "> " : ""}
                      {step}
                    </span>
                  </div>
                ))}
              </div>

              <div className="mt-8 border-t border-slate-800 pt-4 flex items-center justify-between text-[10px] text-slate-500 font-mono">
                <span>ESTIMATED TIME: 20s - 45s</span>
                <span>STATUS: RUNNING</span>
              </div>
            </div>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="mt-8 max-w-xl w-full mx-auto animate-fade-in">
            <div className="rounded-2xl border border-rose-900/60 bg-rose-950/20 p-5 glass-panel">
              <div className="flex items-start gap-3.5">
                <div className="mt-0.5 text-rose-400 flex-shrink-0 bg-rose-950/80 p-1.5 rounded-lg border border-rose-900">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-bold text-rose-300">
                    Analysis Pipeline Failed
                  </h3>
                  <p className="mt-1 text-xs text-rose-400/90 font-mono leading-relaxed">{error}</p>
                </div>
              </div>
            </div>
            <div className="text-center mt-5">
              <button
                onClick={handleReset}
                className="text-xs text-blue-400 hover:text-blue-300 font-mono font-bold uppercase tracking-wider"
              >
                &larr; Return to Dashboard
              </button>
            </div>
          </div>
        )}

        {/* Results Screen */}
        {response && (
          <div className="mt-2 animate-fade-in w-full">
            {/* Echo original input in collapsed view */}
            <div className="mb-6 rounded-2xl bg-slate-900/40 border border-slate-800 p-5 glass-panel">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest font-mono">
                  Input Parameters Verified
                </span>
                <span className="text-[10px] bg-slate-800 text-slate-300 border border-slate-700 px-2 py-0.5 rounded font-mono font-medium">
                  {response.mode === "public" ? "CLAIM ANALYSIS" : "TOPIC MONITORING"}
                </span>
              </div>
              <p className="text-sm text-slate-300 italic leading-relaxed border-l-2 border-slate-700 pl-3">
                &ldquo;{submittedInput}&rdquo;
              </p>
            </div>

            {/* Results Render */}
            {response.mode === "public" ? (
              <PublicResultView
                result={response.result as PublicResult}
                sourcesUsed={response.sources_used}
                detectedLanguage={response.detected_language}
              />
            ) : (
              <NewsroomResultView
                result={response.result as NewsroomResult}
                sourcesUsed={response.sources_used}
                detectedLanguage={response.detected_language}
              />
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="w-full border-t border-slate-900 bg-[#060a10]">
        <div className="mx-auto max-w-5xl px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-center sm:text-left text-xs text-slate-500 font-mono">
          <div>
            TrustLens — Open-source Content Integrity Network
          </div>
          <div className="flex items-center gap-4">
            <span>TRACK: AGENTS FOR GOOD</span>
            <span>CAPSTONE 2026</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
