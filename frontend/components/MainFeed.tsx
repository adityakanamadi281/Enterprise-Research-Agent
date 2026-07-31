"use client";

import { 
  Globe, BookOpen, Database, Paperclip, ArrowRight, AlertCircle, 
  Sparkles, Download, HelpCircle, History, Search, Cpu, CheckCircle2, 
  Clock, Info 
} from "lucide-react";

type Source = { 
  id: string; 
  title: string; 
  url: string; 
  publisher?: string; 
  published_at?: string; 
  reliability_score: number 
};

type Finding = { 
  id: string; 
  claim: string; 
  evidence_span: string; 
  confidence: number; 
  classification: string;
  source_id?: string;
};

type Event = { 
  step: string; 
  status: string; 
  duration_ms: number; 
  details: Record<string, any>;
  created_at?: string;
};

type Session = { 
  id: string; 
  question: string; 
  status: string; 
  confidence: number; 
  conclusion?: string; 
  created_at?: string;
  sources?: Source[]; 
  findings?: Finding[]; 
  events?: Event[] 
};

type Metrics = {
  sessions: number;
  sources: number;
  findings: number;
  events: number;
  completed_runs: number;
  average_confidence: number;
  measured_at?: string;
};

type MainFeedProps = {
  activeTab: "search" | "library" | "knowledge" | "metrics";
  current: Session | null;
  loading: boolean;
  question: string;
  setQuestion: (q: string) => void;
  error: string;
  searchFocus: "all" | "academic" | "knowledge";
  setSearchFocus: (focus: "all" | "academic" | "knowledge") => void;
  focusDropdownOpen: boolean;
  setFocusDropdownOpen: (open: boolean) => void;
  proMode: boolean;
  setProMode: (mode: boolean) => void;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  handleSearch: (qText?: string) => void;
  handleUpload: (files: FileList | null) => void;
  uploading: boolean;
  uploadStatus: string;
  getDynamicSuggestions: () => string[];
  loadingStep: number;
  loadingMessages: string[];
  parseCitations: (conclusion: string | undefined, sources: Source[] | undefined) => React.ReactNode;
  setReportTitle: (title: string) => void;
  setReportModalOpen: (open: boolean) => void;
  handleGenerateReport: (id: string) => void;
  getDynamicFollowUps: (session: Session) => string[];
  sessions: Session[];
  loadSession: (id: string) => void;
  kbQuery: string;
  setKbQuery: (q: string) => void;
  handleKbSearch: (val: string) => void;
  kbResults: any[];
  metrics: Metrics | null;
};

export default function MainFeed({
  activeTab,
  current,
  loading,
  question,
  setQuestion,
  error,
  searchFocus,
  setSearchFocus,
  focusDropdownOpen,
  setFocusDropdownOpen,
  proMode,
  setProMode,
  textareaRef,
  handleSearch,
  handleUpload,
  uploading,
  uploadStatus,
  getDynamicSuggestions,
  loadingStep,
  loadingMessages,
  parseCitations,
  setReportTitle,
  setReportModalOpen,
  handleGenerateReport,
  getDynamicFollowUps,
  sessions,
  loadSession,
  kbQuery,
  setKbQuery,
  handleKbSearch,
  kbResults,
  metrics,
}: MainFeedProps) {
  
  const focusLabels = {
    all: "All Sources",
    academic: "Academic (OpenAlex)",
    knowledge: "Local Knowledge Base"
  };

  return (
    <div className="flex-1 overflow-y-auto px-6 py-10 md:py-16">
      <div className="max-w-2xl mx-auto space-y-12">
        
        {/* VIEW A: SEARCH / HOME TAB */}
        {activeTab === "search" && (
          <>
            
            {/* HOMEPAGE VIEW */}
            {!current && !loading && (
              <div className="py-8 space-y-10">
                
                {/* Welcoming Text */}
                <div className="text-center space-y-3 pt-6">
                  <h2 className="text-3xl md:text-4xl font-normal text-white tracking-tight">
                    Enterprise Research Agent
                  </h2>
                </div>

                {/* Perplexity Search Box Container */}
                <div className="bg-[#202222] border border-[#2a2c2c] rounded-2xl p-2 shadow-xl focus-within:border-zinc-700 transition-colors relative">
                  
                  <div className="px-3 pt-2">
                    <textarea
                      ref={textareaRef}
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      placeholder="Ask anything or run research queries..."
                      rows={2}
                      className="w-full bg-transparent border-0 outline-none text-[15px] text-[#e3e3e2] placeholder-zinc-500 resize-none min-h-[50px] max-h-[220px]"
                      aria-label="Perplexity Search input"
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          if (question.trim().length >= 12) handleSearch();
                        }
                      }}
                    />
                  </div>

                  {/* Tool Actions Row */}
                  <div className="flex items-center justify-between px-2 pb-1 pt-2 border-t border-[#2a2c2c]/40 mt-1 select-none">
                    
                    <div className="flex items-center gap-2">
                      
                      {/* Focus Button */}
                      <div className="relative">
                        <button 
                          onClick={() => setFocusDropdownOpen(!focusDropdownOpen)}
                          className="flex items-center gap-1.5 py-1 px-3.5 rounded-full border border-[#2a2c2c] bg-[#191a1a] hover:bg-[#202222] text-xs font-semibold text-zinc-300 hover:text-white transition-colors"
                        >
                          <Globe className="h-3 w-3 text-[#10B981]" />
                          <span>Focus: {focusLabels[searchFocus]}</span>
                        </button>

                        {/* Dropdown list */}
                        {focusDropdownOpen && (
                          <div className="absolute left-0 bottom-9 w-52 bg-[#191a1a] border border-[#2a2c2c] rounded-xl shadow-2xl p-1 z-40">
                            <button 
                              onClick={() => { setSearchFocus("all"); setFocusDropdownOpen(false); }}
                              className="w-full text-left px-3 py-2 rounded-lg text-xs font-semibold text-zinc-300 hover:text-white hover:bg-[#202222] flex items-center gap-2"
                            >
                              <Globe className="h-3.5 w-3.5 text-zinc-500" /> All Sources
                            </button>
                            <button 
                              onClick={() => { setSearchFocus("academic"); setFocusDropdownOpen(false); }}
                              className="w-full text-left px-3 py-2 rounded-lg text-xs font-semibold text-zinc-300 hover:text-white hover:bg-[#202222] flex items-center gap-2"
                            >
                              <BookOpen className="h-3.5 w-3.5 text-zinc-500" /> Academic (OpenAlex)
                            </button>
                            <button 
                              onClick={() => { setSearchFocus("knowledge"); setFocusDropdownOpen(false); }}
                              className="w-full text-left px-3 py-2 rounded-lg text-xs font-semibold text-zinc-300 hover:text-white hover:bg-[#202222] flex items-center gap-2"
                            >
                              <Database className="h-3.5 w-3.5 text-zinc-500" /> Local Knowledge Base
                            </button>
                          </div>
                        )}
                      </div>

                      <label className="p-1.5 rounded-full border border-[#2a2c2c] bg-[#191a1a] text-zinc-500 hover:text-zinc-300 hover:bg-[#202222] cursor-pointer" title="Upload PDF, TXT, Markdown, CSV, or JSON">
                        <input className="sr-only" type="file" multiple accept=".pdf,.txt,.md,.csv,.json,application/pdf,text/plain,text/markdown,text/csv,application/json" onChange={(event) => { handleUpload(event.target.files); event.currentTarget.value = ""; }} />
                        <Paperclip className="h-3.5 w-3.5" />
                      </label>
                    </div>

                    {/* Pro Mode & Submit button */}
                    <div className="flex items-center gap-3">
                      <label className="flex items-center gap-1.5 cursor-pointer">
                        <span className="text-[11px] font-mono-custom text-zinc-500">CoPilot</span>
                        <input 
                          type="checkbox" 
                          checked={proMode} 
                          onChange={() => setProMode(!proMode)}
                          className="sr-only peer"
                        />
                        <div className="w-8 h-4 bg-zinc-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-[#191a1a] after:border-zinc-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-[#10B981] relative"></div>
                      </label>

                      <button 
                        type="button" 
                        onClick={() => handleSearch()}
                        disabled={question.trim().length < 12}
                        className="h-8 w-8 rounded-full bg-[#10B981] disabled:bg-zinc-800 text-[#191a1a] disabled:text-zinc-650 flex items-center justify-center transition-all disabled:opacity-40 active:scale-95 shrink-0"
                      >
                        <ArrowRight className="h-4 w-4" />
                      </button>
                    </div>

                  </div>

                </div>

                {/* Quick error notification */}
                {error && (
                  <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    <span>{error}</span>
                  </div>
                )}
                {(uploading || uploadStatus) && <p className="text-xs text-[#10B981] font-mono-custom">{uploading ? "Ingesting document evidence..." : uploadStatus}</p>}

                {/* Preconfigured Suggestion prompts */}
                <div className="space-y-3 pt-4">
                  <p className="text-[10px] font-mono-custom text-zinc-500 uppercase tracking-widest text-center">
                    Prior research pathways
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {getDynamicSuggestions().map((q, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          setQuestion(q);
                          handleSearch(q);
                        }}
                        className="text-left p-3.5 rounded-xl border border-[#2a2c2c] bg-[#202222]/30 hover:bg-[#202222]/70 hover:border-[#10B981]/40 transition-all text-xs text-zinc-400 hover:text-white"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>

              </div>
            )}

            {/* SEARCH ACTIVE LOADER TIMELINE */}
            {loading && (
              <div className="py-20 space-y-8 max-w-xl mx-auto">
                
                {/* Pulsing Brain loader */}
                <div className="flex items-center gap-4 border border-[#2a2c2c] bg-[#202222]/40 rounded-xl p-4">
                  <span className="h-8 w-8 rounded-full bg-[#10B981]/15 text-[#10B981] flex items-center justify-center animate-spin border-t-2 border-[#10B981] shrink-0" />
                  <div>
                    <h4 className="text-sm font-bold text-white leading-tight">Orchestrating CoPilot Agent Run</h4>
                    <p className="text-xs font-mono-custom text-zinc-500 mt-1 animate-pulse">
                      {loadingMessages[loadingStep]}
                    </p>
                  </div>
                </div>

                {/* Timeline logs checklist */}
                <div className="border border-[#2a2c2c] bg-[#1d1f1f]/50 rounded-xl p-4 space-y-3.5 select-none">
                  {loadingMessages.map((msg, index) => {
                    const isDone = index < loadingStep;
                    const isCurrent = index === loadingStep;
                    return (
                      <div key={index} className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-3">
                          <span className={`h-4.5 w-4.5 rounded-full flex items-center justify-center text-[9px] font-bold border ${
                            isDone 
                              ? "bg-[#10B981]/20 border-[#10B981] text-[#10B981]" 
                              : isCurrent 
                                ? "bg-zinc-800 border-[#10B981] text-[#10B981] animate-pulse" 
                                : "bg-[#191a1a] border-zinc-800 text-zinc-650"
                          }`}>
                            {isDone ? "✓" : index + 1}
                          </span>
                          <span className={isDone ? "text-zinc-500 line-through" : isCurrent ? "text-white font-medium" : "text-zinc-650"}>
                            {msg}
                          </span>
                        </div>
                        {isCurrent && (
                          <span className="text-[9px] font-mono-custom text-[#10B981] bg-[#10B981]/10 px-2 py-0.5 rounded border border-[#10B981]/25">
                            running
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Skeletal pulse placeholders */}
                <div className="space-y-3.5 opacity-30 select-none">
                  <div className="h-5 bg-zinc-800 rounded w-1/3 skeleton-shimmer"></div>
                  <div className="space-y-2">
                    <div className="h-4 bg-zinc-800 rounded w-full skeleton-shimmer"></div>
                    <div className="h-4 bg-zinc-800 rounded w-4/5 skeleton-shimmer"></div>
                    <div className="h-4 bg-zinc-800 rounded w-2/3 skeleton-shimmer"></div>
                  </div>
                </div>

              </div>
            )}

            {/* COMPLETED RESEARCH THREAD RESULTS VIEW */}
            {current && !loading && (
              <div className="space-y-8 select-text">
                
                {/* Thread Question */}
                <h2 className="text-2xl font-bold text-white tracking-tight leading-tight pt-2">
                  {current.question}
                </h2>

                {/* MAIN SYNTHESIZED EXECUTIVE ANSWER */}
                <div className="space-y-4">
                  
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-semibold text-zinc-400">
                      <Sparkles className="h-4.5 w-4.5 text-[#10B981]" />
                      <span>CoPilot Synthesis Briefing</span>
                    </div>

                    <span className={`text-[10px] font-mono-custom px-2 py-0.5 rounded border ${
                      current.confidence * 100 >= 80 ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" : "text-amber-400 bg-amber-500/10 border-amber-500/20"
                    }`}>
                      Confidence {Math.round(current.confidence * 100)}%
                    </span>
                  </div>

                  {/* Summary container */}
                  <div className="bg-[#202222]/20 border border-[#2a2c2c]/40 rounded-2xl p-6 shadow-inner relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-24 h-24 bg-[#10B981]/5 rounded-full blur-2xl pointer-events-none" />
                    {parseCitations(current.conclusion, current.sources)}
                  </div>

                </div>

                {/* ACTIONS TOOLBAR */}
                <div className="flex items-center justify-between border-t border-[#2a2c2c]/40 pt-6 mt-6 select-none">
                  <div className="flex items-center gap-2 text-[10px] font-mono-custom text-zinc-500">
                    <span>Created: {current.created_at ? new Date(current.created_at).toLocaleDateString() : "Just now"}</span>
                    <span>•</span>
                    <span>Trace: {current.events?.length || 0} run steps</span>
                  </div>

                  <button
                    onClick={() => {
                      setReportTitle(`Executive Intelligence Report: ${current.question.substring(0, 30)}...`);
                      setReportModalOpen(true);
                      handleGenerateReport(current.id);
                    }}
                    className="flex items-center gap-1.5 py-1.5 px-3.5 rounded-full bg-[#10B981] hover:bg-emerald-400 text-[#191a1a] font-bold text-xs shadow-md transition-all active:scale-95"
                  >
                    <Download className="h-3.5 w-3.5" /> Compile Executive Report
                  </button>
                </div>

                {/* RELATED QUESTIONS */}
                <div className="pt-8 border-t border-[#2a2c2c]/40 space-y-3">
                  <div className="flex items-center gap-2 text-xs font-semibold text-zinc-400">
                    <HelpCircle className="h-4 w-4 text-[#10B981]" />
                    <span>Related Questions</span>
                  </div>
                  
                  <div className="space-y-2">
                    {getDynamicFollowUps(current).map((fq, index) => (
                      <button
                        key={index}
                        onClick={() => {
                          setQuestion(fq);
                          handleSearch(fq);
                        }}
                        className="w-full flex items-center justify-between text-left p-3.5 rounded-xl border border-[#2a2c2c]/60 bg-[#1d1f1f]/30 hover:bg-[#202222]/50 hover:border-zinc-700 transition-all text-xs font-medium text-zinc-300 hover:text-white"
                      >
                        <span>{fq}</span>
                        <span className="text-[#10B981] text-sm font-bold shrink-0">+</span>
                      </button>
                    ))}
                  </div>
                </div>

              </div>
            )}

          </>
        )}

        {/* VIEW B: LIBRARY LIST */}
        {activeTab === "library" && (
          <div className="space-y-6 pt-4">
            <div className="space-y-1.5">
              <h3 className="text-2xl font-normal text-white">Research Library</h3>
              <p className="text-xs text-zinc-500">
                A persistent repository of accumulated intellectual intelligence sessions. Inspect details, confidence indexes, and cited materials.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-3.5">
              {sessions.length === 0 ? (
                <div className="p-16 border border-dashed border-[#2a2c2c] rounded-2xl text-center">
                  <History className="h-8 w-8 text-zinc-700 mx-auto mb-2" />
                  <p className="text-sm text-zinc-400">Your library is currently empty.</p>
                  <p className="text-xs text-zinc-650 mt-1">Submit a new query above to record the first brief.</p>
                </div>
              ) : (
                sessions.map((s) => (
                  <div 
                    key={s.id}
                    onClick={() => loadSession(s.id)}
                    className="p-4 bg-[#202222]/25 border border-[#2a2c2c] hover:border-zinc-700 rounded-xl cursor-pointer transition-all duration-200 group flex items-start justify-between gap-4"
                  >
                    <div className="space-y-2 overflow-hidden flex-1">
                      <h4 className="text-sm font-semibold text-white group-hover:text-[#10B981] transition-colors truncate">
                        {s.question}
                      </h4>
                      <div className="flex items-center gap-3 text-[10px] font-mono-custom text-zinc-500">
                        <span className="uppercase">{s.status}</span>
                        <span>•</span>
                        <span>{s.created_at ? new Date(s.created_at).toLocaleDateString() : "Just now"}</span>
                      </div>
                    </div>

                    <div className="text-right shrink-0">
                      <span className={`text-[10px] font-mono-custom px-2 py-0.5 rounded border ${
                        s.confidence * 100 >= 80 ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" : "text-amber-400 bg-amber-500/10 border-amber-500/20"
                      }`}>
                        {Math.round(s.confidence * 100)}% Conf.
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* VIEW C: DURABLE KNOWLEDGE BASE SEARCH */}
        {activeTab === "knowledge" && (
          <div className="space-y-6 pt-4">
            
            <div className="space-y-1.5">
              <h3 className="text-2xl font-normal text-white">Durable Knowledge Base</h3>
              <p className="text-xs text-zinc-500">
                Query verified evidence records gathered from academic publishers during past research runs.
              </p>
            </div>

            {/* Input query field */}
            <div className="bg-[#202222] border border-[#2a2c2c] rounded-xl p-2.5 shadow-md flex items-center gap-3 focus-within:border-zinc-700 transition-colors">
              <Search className="h-5 w-5 text-zinc-500 shrink-0 ml-1" />
              <input
                value={kbQuery}
                onChange={(e) => handleKbSearch(e.target.value)}
                placeholder="Search keywords (e.g. manufacturing, cardiovascular)..."
                className="bg-transparent border-0 outline-none text-sm text-white placeholder-zinc-500 w-full py-1"
              />
            </div>

            {/* Search Results list */}
            <div className="space-y-4">
              {kbQuery.trim().length < 2 ? (
                <div className="p-16 border border-dashed border-[#2a2c2c] rounded-2xl text-center space-y-2 select-none">
                  <Database className="h-8 w-8 text-zinc-700 mx-auto" />
                  <p className="text-sm text-zinc-400 font-semibold">SQLite retrieval indexes ready</p>
                  <p className="text-xs text-zinc-600">Enter keywords above to execute database full-text matching.</p>
                </div>
              ) : kbResults.length === 0 ? (
                <div className="p-12 text-center border border-[#2a2c2c] rounded-xl text-zinc-500">
                  <AlertCircle className="h-5 w-5 mx-auto mb-2 text-zinc-600" />
                  No matched claims found for &ldquo;{kbQuery}&rdquo; in local memory.
                </div>
              ) : (
                kbResults.map((res) => (
                  <div 
                    key={res.id}
                    onClick={() => loadSession(res.session_id)}
                    className="p-5 bg-[#202222]/30 border border-[#2a2c2c] hover:border-[#10B981]/40 rounded-xl cursor-pointer transition-all duration-150 group space-y-3"
                  >
                    <div className="flex items-center justify-between text-[10px] font-mono-custom text-zinc-500">
                      <span>SOURCE CONFIDENCE: {Math.round(res.confidence * 100)}%</span>
                      <span className="text-[#10B981] group-hover:underline">Open Session Context →</span>
                    </div>

                    <h4 className="text-sm font-semibold text-white leading-snug group-hover:text-[#10B981] transition-colors">
                      {res.claim}
                    </h4>

                    <div className="p-3 bg-[#191a1a] border border-[#2a2c2c] rounded-lg">
                      <p className="text-xs text-zinc-400 italic leading-relaxed">
                        &ldquo;{res.evidence_span}&rdquo;
                      </p>
                    </div>
                  </div>
                ))
              )}
            </div>

          </div>
        )}

        {/* VIEW D: METRICS TELEMETRY DASHBOARD */}
        {activeTab === "metrics" && (
          <div className="space-y-6 pt-4">
            
            <div className="space-y-1.5">
              <h3 className="text-2xl font-normal text-white">Operations Dashboard</h3>
              <p className="text-xs text-zinc-500">
                System-wide analytics and performance measures parsed from database metrics schemas.
              </p>
            </div>

            {metrics ? (
              <div className="space-y-6">
                
                {/* Stat Cards Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 select-none">
                  
                  <div className="p-4 bg-[#202222]/30 border border-[#2a2c2c] rounded-xl text-center space-y-1">
                    <div className="text-zinc-500 text-[10px] font-mono-custom uppercase tracking-wider">Sessions</div>
                    <div className="text-2xl font-bold text-white">{metrics.sessions}</div>
                  </div>

                  <div className="p-4 bg-[#202222]/30 border border-[#2a2c2c] rounded-xl text-center space-y-1">
                    <div className="text-zinc-500 text-[10px] font-mono-custom uppercase tracking-wider">Cited Sources</div>
                    <div className="text-2xl font-bold text-[#10B981]">{metrics.sources}</div>
                  </div>

                  <div className="p-4 bg-[#202222]/30 border border-[#2a2c2c] rounded-xl text-center space-y-1">
                    <div className="text-zinc-500 text-[10px] font-mono-custom uppercase tracking-wider">Claims Audited</div>
                    <div className="text-2xl font-bold text-white">{metrics.findings}</div>
                  </div>

                  <div className="p-4 bg-[#202222]/30 border border-[#2a2c2c] rounded-xl text-center space-y-1">
                    <div className="text-zinc-500 text-[10px] font-mono-custom uppercase tracking-wider">Avg Confidence</div>
                    <div className="text-2xl font-bold text-emerald-400">{Math.round(metrics.average_confidence * 100)}%</div>
                  </div>

                </div>

                {/* Operational Details */}
                <div className="p-5 bg-[#202222]/30 border border-[#2a2c2c] rounded-xl space-y-4">
                  <h4 className="text-xs font-mono-custom text-zinc-400 uppercase tracking-widest border-b border-[#2a2c2c] pb-2">
                    Telemetry Schema Telemetry
                  </h4>

                  <div className="space-y-3.5 text-xs text-zinc-450 font-medium">
                    <div className="flex justify-between">
                      <span>Completed Sessions (Completed runs):</span>
                      <span className="text-white font-mono-custom">{metrics.completed_runs}</span>
                    </div>
                    
                    <div className="flex justify-between">
                      <span>Total Pipeline Logged Events:</span>
                      <span className="text-white font-mono-custom">{metrics.events}</span>
                    </div>

                    <div className="flex justify-between">
                      <span>Measurements timestamp:</span>
                      <span className="text-white font-mono-custom">
                        {metrics.measured_at ? new Date(metrics.measured_at).toLocaleString() : "Sync active"}
                      </span>
                    </div>

                    <div className="flex justify-between">
                      <span>System Host Status:</span>
                      <span className="text-[#10B981] font-semibold font-mono-custom flex items-center gap-1">
                        <span className="h-1.5 w-1.5 rounded-full bg-[#10B981]" /> ONLINE
                      </span>
                    </div>
                  </div>
                </div>

              </div>
            ) : (
              <div className="p-12 text-center border border-dashed border-[#2a2c2c] rounded-xl text-zinc-500 font-mono-custom">
                Metrics data unavailable. Ensure API service is live.
              </div>
            )}

          </div>
        )}

      </div>
    </div>
  );
}
