"use client";

import { FormEvent, useEffect, useState, useRef } from "react";
import Sidebar from "../components/Sidebar";
import MainFeed from "../components/MainFeed";
import CitationsPanel from "../components/CitationsPanel";
import ReportModal from "../components/ReportModal";
import { RefreshCw, ExternalLink } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "https://enterprise-research-agent-1.onrender.com";

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

type Metrics = {
  sessions: number;
  sources: number;
  findings: number;
  events: number;
  completed_runs: number;
  average_confidence: number;
  measured_at?: string;
};

const DEFAULT_SUGGESTED_QUERIES = [
  "How is AI transforming manufacturing quality operations?",
  "What are the latest breakthroughs in solid-state battery energy density?",
  "Summarize current research on microplastic effects on human cardiovascular health.",
  "What are the primary factors contributing to recent global semiconductor supply stabilization?"
];

export default function ResearchWorkspace() {
  const [question, setQuestion] = useState("");
  const [current, setCurrent] = useState<Session | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("");
  
  // Navigation & Tabs
  const [activeTab, setActiveTab] = useState<"search" | "library" | "knowledge" | "metrics">("search");
  const [searchFocus, setSearchFocus] = useState<"all" | "academic" | "knowledge">("all");
  
  // Metrics & Stats
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  
  // Knowledge Base Search
  const [kbQuery, setKbQuery] = useState("");
  const [kbResults, setKbResults] = useState<any[]>([]);
  
  // CoPilot mode toggle
  const [proMode, setProMode] = useState(true);

  // Focus dropdown toggle
  const [focusDropdownOpen, setFocusDropdownOpen] = useState(false);
  
  // Track selected finding in inspector
  const [selectedFindingIndex, setSelectedFindingIndex] = useState<number>(0);

  // Report Modal state
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [reportTitle, setReportTitle] = useState("");
  const [reportData, setReportData] = useState<any | null>(null);
  const [generatingReport, setGeneratingReport] = useState(false);

  // Auto-grow textarea ref
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Simulated Loading Step
  const [loadingStep, setLoadingStep] = useState(0);
  const loadingMessages = [
    "Planning research subquestions...",
    "Scanning academic databases (OpenAlex API)...",
    "Parsing metadata abstracts...",
    "Extracting evidence claims...",
    "Validating reliability factors...",
    "Synthesizing consensus executive brief..."
  ];

  // Refresh history and metrics from backend
  const refreshHistory = () => {
    fetch(`${API}/v1/research`)
      .then((r) => r.json())
      .then(setSessions)
      .catch(() => setError("API disconnected. Start FastAPI backend."));
  };

  const refreshMetrics = () => {
    fetch(`${API}/v1/metrics/overview`)
      .then((r) => r.json())
      .then(setMetrics)
      .catch(() => {});
  };

  useEffect(() => {
    refreshHistory();
    refreshMetrics();
  }, []);

  // Submit search query
  async function handleSearch(qText?: string) {
    const finalQuestion = qText || question;
    if (!finalQuestion || finalQuestion.trim().length < 12) {
      setError("Please write a research query of at least 12 characters.");
      return;
    }

    setLoading(true);
    setError("");
    setActiveTab("search");

    try {
      const response = await fetch(`${API}/v1/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: finalQuestion.trim() }),
      });

      if (!response.ok) {
        throw new Error("Research query failed. Ensure question length is 12-500 characters.");
      }

      const data = await response.json();
      setCurrent(data);
      setSelectedFindingIndex(0);
      setQuestion("");
      refreshHistory();
      refreshMetrics();
    } catch (e) {
      setError(e instanceof Error ? e.message : "An error occurred.");
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload(files: FileList | null) {
    if (!files?.length) return;
    setUploading(true); setUploadStatus(""); setError("");
    try {
      const body = new FormData();
      Array.from(files).forEach((file) => body.append("files", file));
      const response = await fetch(`${API}/v1/documents/upload`, { method: "POST", body });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Upload failed");
      setUploadStatus(`${data.documents.length} document${data.documents.length === 1 ? "" : "s"} added to research memory.`);
      refreshHistory(); refreshMetrics();
    } catch (err) { setError(err instanceof Error ? err.message : "Upload failed"); }
    finally { setUploading(false); }
  }

  // Load a historic session
  const loadSession = (id: string) => {
    setLoading(true);
    setError("");
    setActiveTab("search");
    fetch(`${API}/v1/research/${id}`)
      .then((r) => r.json())
      .then((data) => {
        setCurrent(data);
        setSelectedFindingIndex(0);
      })
      .catch(() => setError("Could not retrieve session."))
      .finally(() => setLoading(false));
  };

  // Search Knowledge base
  const handleKbSearch = (val: string) => {
    setKbQuery(val);
    if (val.trim().length < 2) {
      setKbResults([]);
      return;
    }
    fetch(`${API}/v1/knowledge/search?q=${encodeURIComponent(val.trim())}`)
      .then((r) => r.json())
      .then(setKbResults)
      .catch(() => {});
  };

  // Generate Executive Report
  const handleGenerateReport = async (sessionId: string) => {
    setGeneratingReport(true);
    const finalTitle = reportTitle.trim() || `Report: ${current?.question.substring(0, 45)}...`;
    try {
      const response = await fetch(`${API}/v1/research/${sessionId}/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: finalTitle }),
      });
      if (response.ok) {
        const data = await response.json();
        setReportData(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setGeneratingReport(false);
    }
  };

  const [streamedConclusion, setStreamedConclusion] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);

  useEffect(() => {
    if (current?.conclusion) {
      const fullText = current.conclusion;
      setStreamedConclusion("");
      setIsStreaming(true);

      let currentIdx = 0;
      const stepSize = Math.max(2, Math.floor(fullText.length / 40));
      const interval = setInterval(() => {
        currentIdx += stepSize;
        if (currentIdx >= fullText.length) {
          setStreamedConclusion(fullText);
          setIsStreaming(false);
          clearInterval(interval);
        } else {
          setStreamedConclusion(fullText.slice(0, currentIdx));
        }
      }, 20);

      return () => clearInterval(interval);
    } else {
      setStreamedConclusion("");
      setIsStreaming(false);
    }
  }, [current?.id, current?.conclusion]);

  // Render clean structured explanation and key points with live streaming support
  function parseCitations(conclusion: string | undefined, sources: Source[] | undefined) {
    const textToRender = streamedConclusion || conclusion;
    if (!textToRender) return <p className="text-zinc-550 italic">No summary generated.</p>;

    const cleanedConclusion = textToRender
      .replace(/\]\s*\(\s*https?:\/\/[^\)]+\)/g, "]")
      .replace(/\(\s*https?:\/\/[^\)]+\)/g, "")
      .replace(/https?:\/\/\S+/g, "")
      .trim();

    const lines = cleanedConclusion.split("\n");

    return (
      <div className="leading-relaxed text-[#e3e3e2] text-sm md:text-[15px] space-y-3 antialiased font-normal font-sans relative">
        {lines.map((line, idx) => {
          const trimmed = line.trim();
          if (!trimmed) return <div key={idx} className="h-1" />;

          // Render ### Heading
          if (trimmed.startsWith("###") || trimmed.startsWith("##")) {
            const headingText = trimmed.replace(/^#+\s*/, "");
            return (
              <h3 key={idx} className="text-base font-bold text-[#10B981] tracking-wide mt-4 mb-2 first:mt-0 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-[#10B981]" />
                {headingText}
              </h3>
            );
          }

          // Render Bullet points (• or - or *)
          if (trimmed.startsWith("•") || trimmed.startsWith("-") || trimmed.startsWith("*")) {
            const bulletText = trimmed.replace(/^[•\-\*]\s*/, "");
            return (
              <div key={idx} className="flex items-start gap-2.5 pl-1 my-1.5">
                <span className="text-[#10B981] mt-1 text-xs">•</span>
                <span className="flex-1 text-zinc-200">
                  {renderFormattedText(bulletText)}
                  {isStreaming && idx === lines.length - 1 && (
                    <span className="inline-block w-2 h-4 bg-[#10B981] ml-1.5 align-middle animate-pulse" />
                  )}
                </span>
              </div>
            );
          }

          // Regular paragraph
          return (
            <p key={idx} className="text-zinc-200 leading-relaxed">
              {renderFormattedText(trimmed)}
              {isStreaming && idx === lines.length - 1 && (
                <span className="inline-block w-2 h-4 bg-[#10B981] ml-1.5 align-middle animate-pulse" />
              )}
            </p>
          );
        })}
      </div>
    );
  }

  function renderFormattedText(text: string) {
    const parts = text.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={i} className="font-semibold text-white">{part.slice(2, -2)}</strong>;
      }
      return part;
    });
  }

  // Dynamically assemble suggestions based on actual database session history (no hardcoding)
  const getDynamicSuggestions = () => {
    const historicalQueries = Array.from(new Set(sessions.map((s) => s.question).filter(Boolean)));
    const merged = [...historicalQueries, ...DEFAULT_SUGGESTED_QUERIES];
    return Array.from(new Set(merged)).slice(0, 4);
  };

  // Dynamically generate follow-up questions from findings details
  const getDynamicFollowUps = (session: Session) => {
    const questions = [];
    if (session.sources && session.sources.length > 0) {
      const pub = session.sources[0]?.publisher || "academic registers";
      questions.push(`What is the peer-reviewed reliability rating of findings from "${pub}"?`);
    } else {
      questions.push("Explain database fallback procedures when no citations are available.");
    }

    if (session.findings && session.findings.length > 0) {
      const snippet = session.findings[0]?.claim.substring(0, 45) || "this claim context";
      questions.push(`Provide the primary abstract evidence supporting the claim: "${snippet}..."`);
    } else {
      questions.push("How does Atlas compute the final session confidence percentage?");
    }

    const firstStep = session.events?.[0]?.step || "plan";
    questions.push(`Detail the execution trace subquestions formulated in the "${firstStep}" stage.`);

    return questions;
  };

  return (
    <div className="flex h-screen bg-[#191a1a] text-[#eff3fa] overflow-hidden antialiased">
      
      {/* 1. SIDEBAR */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        setCurrent={setCurrent}
        setQuestion={setQuestion}
        setError={setError}
        sessions={sessions}
        loadSession={loadSession}
        metrics={metrics}
      />

      {/* 2. MAIN CENTER FEED + PERMANENT RIGHT PANEL CONTAINER */}
      <main className="flex-1 bg-[#131415] flex flex-col overflow-hidden relative">
        
        {/* TOP HEADER */}
        <header className="h-12 border-b border-[#2a2c2c]/50 bg-[#131415] px-6 flex items-center justify-between select-none z-10 shrink-0">
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-[#10B981] animate-ping" />
            <span className="text-[10px] font-mono-custom text-zinc-500 uppercase tracking-widest">
              Live database channel active
            </span>
          </div>

          <div className="flex items-center gap-4">
            <button 
              onClick={() => { refreshHistory(); refreshMetrics(); }} 
              className="p-1.5 rounded-md hover:bg-[#202222] text-zinc-400 hover:text-white transition-colors"
              title="Refresh"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </button>
            <a 
              href={`${API}/docs`} 
              target="_blank" 
              rel="noreferrer"
              className="flex items-center gap-1.5 text-[10px] font-mono-custom text-zinc-400 hover:text-white"
            >
              Docs <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </header>

        {/* 3-COLUMN SPLIT PANEL */}
        <div className="flex-1 flex overflow-hidden">
          
          {/* Main Feed panel */}
          <MainFeed
            activeTab={activeTab}
            current={current}
            loading={loading}
            question={question}
            setQuestion={setQuestion}
            error={error}
            searchFocus={searchFocus}
            setSearchFocus={setSearchFocus}
            focusDropdownOpen={focusDropdownOpen}
            setFocusDropdownOpen={setFocusDropdownOpen}
            proMode={proMode}
            setProMode={setProMode}
            textareaRef={textareaRef}
            handleSearch={handleSearch}
            handleUpload={handleUpload}
            uploading={uploading}
            uploadStatus={uploadStatus}
            getDynamicSuggestions={getDynamicSuggestions}
            loadingStep={loadingStep}
            loadingMessages={loadingMessages}
            parseCitations={parseCitations}
            setReportTitle={setReportTitle}
            setReportModalOpen={setReportModalOpen}
            handleGenerateReport={handleGenerateReport}
            getDynamicFollowUps={getDynamicFollowUps}
            sessions={sessions}
            loadSession={loadSession}
            kbQuery={kbQuery}
            setKbQuery={setKbQuery}
            handleKbSearch={handleKbSearch}
            kbResults={kbResults}
            metrics={metrics}
          />

          {/* Citations & Evidence Panel */}
          <CitationsPanel
            activeTab={activeTab}
            current={current}
            loading={loading}
            selectedFindingIndex={selectedFindingIndex}
            setSelectedFindingIndex={setSelectedFindingIndex}
          />

        </div>

      </main>

      {/* REPORT MODAL */}
      <ReportModal
        reportModalOpen={reportModalOpen}
        setReportModalOpen={setReportModalOpen}
        reportTitle={reportTitle}
        reportData={reportData}
        setReportData={setReportData}
        generatingReport={generatingReport}
      />

    </div>
  );
}
