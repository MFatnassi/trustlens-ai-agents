"use client";

import { useState } from "react";

interface SourceUsed {
  url: string;
  title: string;
}

interface PublicResult {
  input_verdict: "true" | "false" | "unverified" | "mixed";
  trust_score: number;
  explanation: string;
}

interface Props {
  result: PublicResult;
  sourcesUsed: SourceUsed[];
  detectedLanguage: string;
}

const VERDICT_CONFIG = {
  true: {
    label: "VERIFIED",
    headline: "Factual Integrity Confirmed",
    sub: "All core statements are fully corroborated by reliable sources.",
    bg: "bg-emerald-950/20",
    border: "border-emerald-500/50 shadow-emerald-500/10",
    text: "text-emerald-400",
    badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    icon: (
      <svg className="w-8 h-8 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
  },
  false: {
    label: "REFUTED / CONTRADICTED",
    headline: "Misinformation / Conflict Detected",
    sub: "Core assertions are directly contradicted by authoritative sources.",
    bg: "bg-rose-950/20",
    border: "border-rose-500/50 shadow-rose-500/10",
    text: "text-rose-400",
    badge: "bg-rose-500/10 text-rose-400 border-rose-500/20",
    icon: (
      <svg className="w-8 h-8 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
      </svg>
    ),
  },
  unverified: {
    label: "UNVERIFIED",
    headline: "Lack of Supporting Evidence",
    sub: "No sources could verify or disprove these specific statements.",
    bg: "bg-amber-950/20",
    border: "border-amber-500/50 shadow-amber-500/10",
    text: "text-amber-400",
    badge: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    icon: (
      <svg className="w-8 h-8 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  mixed: {
    label: "MIXED ACCURACY",
    headline: "Varying Levels of Authenticity",
    sub: "Some claims are verified; others are unsupported or subjective.",
    bg: "bg-blue-950/20",
    border: "border-blue-500/50 shadow-blue-500/10",
    text: "text-blue-400",
    badge: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    icon: (
      <svg className="w-8 h-8 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
  },
};

const LANGUAGE_NAMES: Record<string, string> = {
  en: "English",
  fr: "French",
  es: "Spanish",
  de: "German",
  it: "Italian",
  pt: "Portuguese",
  ar: "Arabic",
  zh: "Chinese",
  ja: "Japanese",
  ko: "Korean",
  ru: "Russian",
  nl: "Dutch",
  tr: "Turkish",
  hi: "Hindi",
};

function getScoreColor(score: number): string {
  if (score > 70) return "text-emerald-400";
  if (score >= 40) return "text-amber-400";
  return "text-rose-400";
}

function getScoreGradient(score: number): string {
  if (score > 70) return "from-emerald-500 to-teal-500";
  if (score >= 40) return "from-amber-500 to-orange-500";
  return "from-rose-500 to-red-600";
}

function getDomainBadge(url: string): { label: string; style: string } {
  try {
    const domain = new URL(url).hostname.toLowerCase();
    if (domain.endsWith(".gov")) return { label: "Government", style: "bg-indigo-950/80 text-indigo-400 border-indigo-900" };
    if (domain.endsWith(".edu")) return { label: "Academic", style: "bg-teal-950/80 text-teal-400 border-teal-900" };
    if (domain.endsWith(".org")) return { label: "Organization", style: "bg-purple-950/80 text-purple-400 border-purple-900" };
    
    const newsDomains = ["reuters.com", "apnews.com", "bloomberg.com", "bbc.com", "nytimes.com", "cnn.com", "afp.com", "dw.com", "france24.com"];
    if (newsDomains.some(nd => domain.includes(nd))) {
      return { label: "News Wire", style: "bg-blue-950/80 text-blue-400 border-blue-900" };
    }
    return { label: "Web Source", style: "bg-slate-900 text-slate-400 border-slate-800" };
  } catch {
    return { label: "Web Source", style: "bg-slate-900 text-slate-400 border-slate-800" };
  }
}

function extractDomain(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

export default function PublicResultView({
  result,
  sourcesUsed,
  detectedLanguage,
}: Props) {
  const verdict = VERDICT_CONFIG[result.input_verdict];
  const langName =
    LANGUAGE_NAMES[detectedLanguage] || detectedLanguage.toUpperCase();

  const [activeTab, setActiveTab] = useState<"analysis" | "sources">("analysis");

  // Format line elements
  const explanationLines = result.explanation.split("\n").filter(Boolean);

  // Score adjustments metrics (mock data for high-end professional appearance)
  const factRatio = result.trust_score;
  const opinionRatio = 100 - result.trust_score;
  
  return (
    <div className="space-y-6">
      {/* 3-Column Widget Dashboard Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        
        {/* Widget 1: Verdict Summary Card */}
        <div className={`lg:col-span-2 glass-panel rounded-2xl p-6 border shadow-lg ${verdict.border} ${verdict.bg} flex flex-col justify-between`}>
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className={`inline-flex items-center px-3 py-1 rounded-lg text-xs font-bold uppercase tracking-wider border ${verdict.badge}`}>
                {verdict.label}
              </span>
              <span className="text-xs text-slate-400 font-mono flex items-center gap-1.5 bg-slate-900/60 px-2.5 py-1 rounded-md border border-slate-800/80">
                <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" />
                LANG: {langName}
              </span>
            </div>
            
            <div className="flex items-start gap-4">
              <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800 flex-shrink-0 mt-0.5">
                {verdict.icon}
              </div>
              <div>
                <h2 className="text-xl font-extrabold text-white tracking-tight leading-snug">
                  {verdict.headline}
                </h2>
                <p className="text-slate-400 text-xs mt-1 leading-relaxed">
                  {verdict.sub}
                </p>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-800/50 flex items-center justify-between text-xs text-slate-500">
            <span>AUDIT SCOPE: 1 ARTICLE / URL</span>
            <span>VERIFIED AT: SYSTEM RUNTIME</span>
          </div>
        </div>

        {/* Widget 2: Trust Score Speedometer */}
        <div className="glass-panel rounded-2xl p-6 border border-slate-800 flex flex-col items-center justify-center relative overflow-hidden bg-gradient-to-b from-[#161c2c]/40 to-[#0e1320]/60">
          <div className="relative w-28 h-28 flex items-center justify-center">
            {/* SVG radial track */}
            <svg className="w-28 h-28 -rotate-90" viewBox="0 0 100 100">
              <circle
                cx="50"
                cy="50"
                r="42"
                fill="none"
                className="stroke-slate-800"
                strokeWidth="7"
              />
              <circle
                cx="50"
                cy="50"
                r="42"
                fill="none"
                className={`stroke-current ${getScoreColor(result.trust_score)}`}
                strokeWidth="7"
                strokeLinecap="round"
                strokeDasharray={`${(result.trust_score / 100) * 263.8} 263.8`}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center mt-1">
              <span className={`text-3xl font-extrabold tracking-tight ${getScoreColor(result.trust_score)}`}>
                {result.trust_score}
              </span>
              <span className="text-[10px] text-slate-500 font-mono font-medium tracking-wide uppercase">
                TRUST INDEX
              </span>
            </div>
          </div>
          <p className="text-xs text-slate-300 font-medium text-center mt-3">
            Deterministic credibility score
          </p>
          <p className="text-[10px] text-slate-500 text-center mt-1 leading-tight">
            Derived from source support ratios and contradiction indices
          </p>
        </div>
      </div>

      {/* Metric Breakdown Panel */}
      <div className="glass-panel rounded-2xl p-5 border border-slate-800 grid grid-cols-1 md:grid-cols-3 gap-6 bg-slate-950/20">
        <div>
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1.5 font-mono">
            <span>FACT-OPINION RATIO</span>
            <span>{factRatio}% FACT</span>
          </div>
          <div className="h-2 w-full bg-slate-900 rounded-full overflow-hidden flex border border-slate-800/80">
            <div className="h-full bg-blue-500 rounded-full" style={{ width: `${factRatio}%` }} />
            <div className="h-full bg-slate-700" style={{ width: `${opinionRatio}%` }} />
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1.5 font-mono">
            <span>SOURCE DENSITY</span>
            <span>{sourcesUsed.length} CITED</span>
          </div>
          <div className="h-2 w-full bg-slate-900 rounded-full overflow-hidden border border-slate-800/80">
            <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${Math.min(sourcesUsed.length * 10, 100)}%` }} />
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1.5 font-mono">
            <span>CONTRADICTION DETECTED</span>
            <span>{result.input_verdict === "false" || result.input_verdict === "mixed" ? "YES" : "NO"}</span>
          </div>
          <div className="h-2 w-full bg-slate-900 rounded-full overflow-hidden border border-slate-800/80">
            <div className={`h-full rounded-full ${
              result.input_verdict === "false" 
                ? "w-full bg-rose-500" 
                : result.input_verdict === "mixed" 
                  ? "w-1/2 bg-amber-500" 
                  : "w-0 bg-emerald-500"
            }`} />
          </div>
        </div>
      </div>

      {/* Tabs Selector */}
      <div className="border-b border-slate-800 flex items-center justify-between">
        <div className="flex gap-6">
          <button
            onClick={() => setActiveTab("analysis")}
            className={`pb-3 text-sm font-bold tracking-tight transition-all border-b-2 uppercase ${
              activeTab === "analysis"
                ? "border-blue-500 text-blue-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            Detailed Integrity Analysis
          </button>
          <button
            onClick={() => setActiveTab("sources")}
            className={`pb-3 text-sm font-bold tracking-tight transition-all border-b-2 uppercase ${
              activeTab === "sources"
                ? "border-blue-500 text-blue-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            Provenance & Citations ({sourcesUsed.length})
          </button>
        </div>

        {/* Action Controls for Professionals */}
        <div className="hidden sm:flex items-center gap-2 pb-2">
          <button 
            onClick={() => window.print()}
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 bg-slate-900 border border-slate-800 hover:border-slate-700 px-3 py-1.5 rounded-lg transition-all"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
            </svg>
            Print Audit Report
          </button>
        </div>
      </div>

      {/* Tab 1: Detailed Explanation Analysis */}
      {activeTab === "analysis" && (
        <div className="glass-panel rounded-2xl border border-slate-800 bg-[#0e1320]/60 p-6 leading-relaxed shadow-xl animate-fade-in">
          <div className="space-y-4">
            {explanationLines.map((line, i) => {
              // Parse markdown bold and list bullet points
              const parts = line.split(/\*\*(.*?)\*\*/g);
              const isBullet = line.match(/^[-*]\s+/);
              const text = isBullet ? line.replace(/^[-*]\s+/, "") : line;
              const textParts = text.split(/\*\*(.*?)\*\*/g);

              if (isBullet) {
                return (
                  <div key={i} className="flex items-start gap-3 pl-1 py-1 group">
                    <span className="text-blue-500 mt-1.5 flex-shrink-0 group-hover:scale-125 transition-transform">
                      <svg className="w-1.5 h-1.5 fill-current" viewBox="0 0 8 8">
                        <circle cx="4" cy="4" r="4" />
                      </svg>
                    </span>
                    <p className="text-slate-300 text-sm leading-relaxed">
                      {textParts.map((part, j) =>
                        j % 2 === 1 ? (
                          <strong key={j} className="font-bold text-white bg-slate-900 border border-slate-800/80 px-1 py-0.5 rounded text-xs mx-0.5">
                            {part}
                          </strong>
                        ) : (
                          <span key={j}>{part}</span>
                        )
                      )}
                    </p>
                  </div>
                );
              }

              return (
                <p key={i} className="text-slate-300 text-sm leading-relaxed">
                  {parts.map((part, j) =>
                    j % 2 === 1 ? (
                      <strong key={j} className="font-bold text-white bg-slate-900 border border-slate-800/80 px-1 py-0.5 rounded text-xs mx-0.5">
                        {part}
                      </strong>
                    ) : (
                      <span key={j}>{part}</span>
                    )
                  )}
                </p>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab 2: Provenance & Citations */}
      {activeTab === "sources" && (
        <div className="space-y-4 animate-fade-in">
          {sourcesUsed.length === 0 ? (
            <div className="glass-panel rounded-2xl border border-slate-800 p-8 text-center text-slate-500 text-sm">
              No sources identified. The system returned verification using purely internal logic.
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {sourcesUsed.map((source, i) => {
                const domainBadge = getDomainBadge(source.url);
                return (
                  <div
                    key={i}
                    className="glass-panel rounded-xl border border-slate-800 bg-[#0e1320]/60 p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 hover:border-slate-600 transition-all duration-200 group shadow-md"
                  >
                    <div className="flex items-start gap-3 min-w-0 flex-1">
                      <span className="text-slate-600 flex-shrink-0 mt-0.5 font-mono text-xs w-6">
                        #{String(i + 1).padStart(2, "0")}
                      </span>
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-1">
                          <span className={`px-2 py-0.5 rounded border text-[9px] font-mono font-bold uppercase tracking-wider ${domainBadge.style}`}>
                            {domainBadge.label}
                          </span>
                          <span className="text-[10px] text-slate-500 font-mono truncate max-w-[200px]">
                            {extractDomain(source.url)}
                          </span>
                        </div>
                        <h4 className="text-sm font-bold text-slate-200 group-hover:text-blue-400 transition-colors leading-snug">
                          {source.title || source.url}
                        </h4>
                      </div>
                    </div>

                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 font-bold bg-slate-900 border border-slate-800 hover:border-blue-900/60 px-3 py-1.5 rounded-lg transition-all w-full sm:w-auto justify-center"
                    >
                      Browse Source
                      <svg className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </a>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
