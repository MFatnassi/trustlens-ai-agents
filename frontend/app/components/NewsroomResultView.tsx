"use client";

import { useState } from "react";

interface SourceUsed {
  url: string;
  title: string;
}

interface NewsroomResult {
  brief: string;
}

interface Props {
  result: NewsroomResult;
  sourcesUsed: SourceUsed[];
  detectedLanguage: string;
}

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

const SECTION_CONFIG: Record<
  string,
  { icon: React.ReactNode; accent: string; accentBorder: string; bg: string }
> = {
  summary: {
    icon: (
      <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    accent: "text-blue-400",
    accentBorder: "border-l-blue-500",
    bg: "bg-blue-950/10",
  },
  "reliable vs questionable sources": {
    icon: (
      <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
    accent: "text-emerald-400",
    accentBorder: "border-l-emerald-500",
    bg: "bg-emerald-950/10",
  },
  "identified contradictions": {
    icon: (
      <svg className="w-5 h-5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
      </svg>
    ),
    accent: "text-amber-400",
    accentBorder: "border-l-amber-500",
    bg: "bg-amber-950/10",
  },
  "suggested editorial angles": {
    icon: (
      <svg className="w-5 h-5 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
      </svg>
    ),
    accent: "text-purple-400",
    accentBorder: "border-l-purple-500",
    bg: "bg-purple-950/10",
  },
};

function parseBrief(brief: string): { heading: string; content: string }[] {
  const sections: { heading: string; content: string }[] = [];
  const lines = brief.split("\n");
  let currentHeading = "";
  let currentContent: string[] = [];

  for (const line of lines) {
    const headingMatch = line.match(/^##\s+(.+)/);
    if (headingMatch) {
      if (currentHeading) {
        sections.push({
          heading: currentHeading,
          content: currentContent.join("\n").trim(),
        });
      }
      currentHeading = headingMatch[1];
      currentContent = [];
    } else {
      currentContent.push(line);
    }
  }

  if (currentHeading) {
    sections.push({
      heading: currentHeading,
      content: currentContent.join("\n").trim(),
    });
  }

  if (sections.length === 0 && brief.trim()) {
    sections.push({ heading: "Brief", content: brief.trim() });
  }

  return sections;
}

function getSectionConfig(heading: string) {
  const key = heading.toLowerCase();
  for (const [sectionKey, config] of Object.entries(SECTION_CONFIG)) {
    if (key.includes(sectionKey)) return config;
  }
  return {
    icon: (
      <svg className="w-5 h-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    accent: "text-slate-400",
    accentBorder: "border-l-slate-600",
    bg: "bg-slate-900/40",
  };
}

function renderContent(heading: string, content: string) {
  const lines = content.split("\n").filter(Boolean);
  const lowerHeading = heading.toLowerCase();

  // If this is the editorial angles section, render as stylized visual cards
  if (lowerHeading.includes("editorial angles")) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
        {lines.map((line, i) => {
          const isBullet = line.match(/^[-*]\s+/);
          const cleanText = isBullet ? line.replace(/^[-*]\s+/, "") : line;
          const textParts = cleanText.split(/\*\*(.*?)\*\*/g);

          return (
            <div 
              key={i} 
              className="glass-panel p-4 rounded-xl border border-slate-800 bg-slate-950/20 hover:border-purple-500/30 hover:bg-[#1c182b]/30 transition-all duration-200 flex items-start gap-3 group"
            >
              <span className="p-1.5 rounded-lg bg-purple-950 border border-purple-900 text-purple-400 mt-0.5 flex-shrink-0 group-hover:scale-110 transition-transform">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                </svg>
              </span>
              <div>
                <p className="text-xs text-slate-300 leading-relaxed font-sans">
                  {textParts.map((part, j) =>
                    j % 2 === 1 ? (
                      <strong key={j} className="font-bold text-white">
                        {part}
                      </strong>
                    ) : (
                      <span key={j}>{part}</span>
                    )
                  )}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  // Generic content renderer
  return lines.map((line, i) => {
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
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed font-sans">
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

    const parts = line.split(/\*\*(.*?)\*\*/g);
    return (
      <p key={i} className="text-xs sm:text-sm text-slate-300 leading-relaxed mb-2 font-sans">
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
  });
}

function extractDomain(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

export default function NewsroomResultView({
  result,
  sourcesUsed,
  detectedLanguage,
}: Props) {
  const sections = parseBrief(result.brief);
  const langName =
    LANGUAGE_NAMES[detectedLanguage] || detectedLanguage.toUpperCase();

  const [activeNav, setActiveNav] = useState<string>(sections[0]?.heading || "");
  const [copied, setCopied] = useState(false);

  function copyToClipboard() {
    navigator.clipboard.writeText(result.brief);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="space-y-6">
      
      {/* Header Banner */}
      <div className="rounded-2xl border border-indigo-500/40 bg-gradient-to-r from-indigo-950/20 to-purple-950/20 p-6 glass-panel flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-lg shadow-indigo-950/10">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-indigo-900/60 border border-indigo-700/50 flex items-center justify-center flex-shrink-0 shadow-md">
            <svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-extrabold text-white tracking-tight bg-gradient-to-r from-white to-slate-200 bg-clip-text text-transparent">
              Newsroom Intelligence Briefing
            </h2>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-[10px] text-indigo-400 font-mono flex items-center gap-1 bg-indigo-950/50 px-2 py-0.5 rounded border border-indigo-900">
                LANG: {langName}
              </span>
              <span className="text-slate-700 font-mono text-[9px]">•</span>
              <span className="text-[10px] text-indigo-400 font-mono bg-indigo-950/50 px-2 py-0.5 rounded border border-indigo-900">
                SOURCES: {sourcesUsed.length} ANALYZED
              </span>
            </div>
          </div>
        </div>

        {/* Copy / Export utility */}
        <div className="flex items-center gap-2 w-full md:w-auto">
          <button
            onClick={copyToClipboard}
            className="inline-flex items-center justify-center gap-2 text-xs font-bold text-slate-300 hover:text-white bg-slate-900 border border-slate-800 hover:border-slate-700 px-4 py-2.5 rounded-xl transition-all w-full md:w-auto"
          >
            {copied ? (
              <>
                <svg className="w-3.5 h-3.5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                Copied Brief!
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                </svg>
                Copy Markdown Brief
              </>
            )}
          </button>
        </div>
      </div>

      {/* Main Layout Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
        
        {/* Navigation Sidebar */}
        <div className="lg:col-span-1 glass-panel rounded-2xl p-4 border border-slate-850 bg-slate-950/10 sticky top-24 space-y-4">
          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest font-mono pl-2">
            DOCUMENT INDEX
          </div>
          <nav className="space-y-1">
            {sections.map((section, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setActiveNav(section.heading);
                  const el = document.getElementById(`section-${idx}`);
                  if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
                }}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 border uppercase tracking-tight ${
                  activeNav === section.heading
                    ? "bg-indigo-950/40 text-indigo-400 border-indigo-900 shadow-md"
                    : "bg-transparent text-slate-400 border-transparent hover:text-slate-200"
                }`}
              >
                <span className="font-mono text-[9px] text-slate-500">
                  {String(idx + 1).padStart(2, "0")}.
                </span>
                <span className="truncate">{section.heading}</span>
              </button>
            ))}
            
            {/* Direct Ledger Link */}
            <button
              onClick={() => {
                setActiveNav("sources");
                const el = document.getElementById("section-sources");
                if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
              }}
              className={`w-full text-left px-3 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 border uppercase tracking-tight ${
                activeNav === "sources"
                  ? "bg-indigo-950/40 text-indigo-400 border-indigo-900 shadow-md"
                  : "bg-transparent text-slate-400 border-transparent hover:text-slate-200"
              }`}
            >
              <span className="font-mono text-[9px] text-slate-500">SRC.</span>
              <span className="truncate">Citations Ledger</span>
            </button>
          </nav>

          <div className="border-t border-slate-800/80 pt-4 px-2">
            <div className="text-[9px] font-bold text-slate-600 uppercase tracking-wider font-mono mb-2">
              Domain Coverage
            </div>
            <div className="flex flex-wrap gap-1.5">
              {Array.from(new Set(sourcesUsed.map(s => extractDomain(s.url)))).slice(0, 4).map((d, i) => (
                <span key={i} className="text-[9px] bg-slate-900 border border-slate-800 text-slate-400 px-2 py-0.5 rounded font-mono truncate max-w-[110px]">
                  {d}
                </span>
              ))}
              {sourcesUsed.length > 4 && (
                <span className="text-[9px] bg-slate-900 border border-slate-800 text-indigo-400 px-2 py-0.5 rounded font-mono font-bold">
                  +{sourcesUsed.length - 4} MORE
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Content Briefing Section */}
        <div className="lg:col-span-3 space-y-6">
          {sections.map((section, idx) => {
            const config = getSectionConfig(section.heading);
            return (
              <div
                id={`section-${idx}`}
                key={idx}
                className={`glass-panel rounded-2xl border border-slate-800 bg-[#0e1320]/60 p-6 border-l-4 ${config.accentBorder} shadow-lg transition-all duration-300 hover:border-slate-700/80`}
              >
                <div className="flex items-center gap-2.5 mb-4 border-b border-slate-850 pb-3">
                  <div className="p-1 rounded-lg bg-slate-900 border border-slate-800 flex-shrink-0">
                    {config.icon}
                  </div>
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest font-mono">
                    {section.heading}
                  </h3>
                </div>
                
                <div className="space-y-2">
                  {renderContent(section.heading, section.content)}
                </div>
              </div>
            );
          })}

          {/* Citations Ledger section */}
          <div
            id="section-sources"
            className="glass-panel rounded-2xl border border-slate-800 bg-[#0e1320]/60 p-6 border-l-4 border-l-slate-500 shadow-lg"
          >
            <div className="flex items-center gap-2.5 mb-4 border-b border-slate-850 pb-3">
              <div className="p-1 rounded-lg bg-slate-900 border border-slate-800 flex-shrink-0">
                <svg className="w-5 h-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest font-mono">
                Citations Ledger
              </h3>
            </div>

            {sourcesUsed.length === 0 ? (
              <div className="text-center text-slate-500 text-xs py-4 font-mono">
                NO CITATIONS ACCUMULATED
              </div>
            ) : (
              <div className="divide-y divide-slate-800/60 space-y-3 pt-1">
                {sourcesUsed.map((source, i) => (
                  <div key={i} className="flex items-start justify-between gap-4 pt-3 first:pt-0 group">
                    <div className="flex items-start gap-2.5 min-w-0">
                      <span className="text-slate-600 font-mono text-[10px] mt-0.5">
                        {String(i + 1).padStart(2, "0")}.
                      </span>
                      <div className="min-w-0">
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs sm:text-sm text-blue-400 hover:text-blue-300 hover:underline font-bold block truncate"
                        >
                          {source.title || source.url}
                        </a>
                        <span className="text-[10px] text-slate-500 font-mono block mt-0.5 truncate">
                          {source.url}
                        </span>
                      </div>
                    </div>
                    <svg className="w-4 h-4 text-slate-700 group-hover:text-blue-500 flex-shrink-0 mt-0.5 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
