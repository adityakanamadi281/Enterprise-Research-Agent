"use client";

import { Layers, Database, ExternalLink } from "lucide-react";

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

type CitationsPanelProps = {
  activeTab: "search" | "library" | "knowledge" | "metrics";
  current: Session | null;
  loading: boolean;
  selectedFindingIndex: number;
  setSelectedFindingIndex: (idx: number) => void;
};

export default function CitationsPanel({
  activeTab,
  current,
  loading,
  selectedFindingIndex,
  setSelectedFindingIndex,
}: CitationsPanelProps) {
  if (activeTab !== "search" || !current || loading) return null;

  return (
    <div className="w-80 lg:w-96 border-l border-[#2a2c2c] bg-[#191a1a] flex flex-col justify-between shrink-0 overflow-y-auto hidden lg:flex select-text animate-fadeIn">
      
      <div className="p-4 flex flex-col flex-1 overflow-y-auto space-y-5">
        
        {/* Citations Grid */}
        <div className="space-y-3.5">
          <div className="flex items-center gap-2 text-xs font-bold text-zinc-400 uppercase tracking-widest font-mono-custom">
            <Layers className="h-4 w-4 text-[#10B981]" />
            <span>Cited Sources ({current.sources?.length || 0})</span>
          </div>

          {current.sources && current.sources.length > 0 ? (
            <div className="grid grid-cols-1 gap-2">
              {current.sources.map((s, idx) => (
                <a 
                  key={s.id}
                  href={s.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-start gap-2.5 p-2.5 rounded-xl border border-[#2a2c2c]/70 bg-[#202222]/30 hover:bg-[#202222]/70 hover:border-zinc-700 transition-all text-xs"
                >
                  <span className="h-5 w-5 rounded bg-[#10B981]/15 text-[#10B981] flex items-center justify-center text-[10px] font-mono-custom font-bold shrink-0">
                    {idx + 1}
                  </span>
                  <div className="overflow-hidden">
                    <p className="font-bold text-white truncate max-w-[280px]">{s.title}</p>
                    <p className="text-[10px] font-mono-custom text-zinc-500 truncate mt-0.5">
                      {s.publisher || "Academic Database"} · Reliability {Math.round(s.reliability_score * 100)}%
                    </p>
                  </div>
                </a>
              ))}
            </div>
          ) : (
            <p className="text-xs text-zinc-650 italic">No cited links loaded.</p>
          )}
        </div>

        {/* Evidence Findings Claims List */}
        <div className="space-y-3 pt-2 border-t border-[#2a2c2c]/40">
          <div className="flex items-center gap-2 text-xs font-bold text-zinc-400 uppercase tracking-widest font-mono-custom">
            <Database className="h-4 w-4 text-[#10B981]" />
            <span>Evidence Claims ({current.findings?.length || 0})</span>
          </div>

          {current.findings && current.findings.length > 0 ? (
            <div className="space-y-3.5">
              {current.findings.map((f, idx) => {
                const isSelected = selectedFindingIndex === idx;
                const source = current.sources?.find(s => s.id === f.source_id);
                const srcIdx = current.sources?.findIndex(s => s.id === f.source_id) ?? -1;

                return (
                  <div 
                    key={f.id}
                    id={`evidence-card-${idx}`}
                    onClick={() => setSelectedFindingIndex(idx)}
                    className={`p-3.5 rounded-xl border cursor-pointer transition-all duration-200 space-y-2.5 ${
                      isSelected 
                        ? "bg-[#202222] border-[#10B981] shadow-md" 
                        : "bg-[#202222]/10 border-[#2a2c2c] hover:bg-[#202222]/30 hover:border-zinc-700"
                    }`}
                  >
                    <div className="flex items-center justify-between text-[9px] font-mono-custom text-zinc-500">
                      <span>CLAIM {idx + 1} ({f.classification.replaceAll("_", " ")})</span>
                      {srcIdx !== -1 && (
                        <span className="text-[#10B981] font-bold">Badge [{srcIdx + 1}]</span>
                      )}
                    </div>

                    <p className="text-xs font-bold text-white leading-snug">
                      {f.claim}
                    </p>

                    {/* Extract Quote Span if selected */}
                    {isSelected && (
                      <div className="p-2.5 bg-zinc-950/80 rounded-lg border border-[#2a2c2c] text-[11px] text-zinc-400 italic leading-relaxed">
                        &ldquo;{f.evidence_span}&rdquo;
                      </div>
                    )}

                    {/* Progress Reliability index */}
                    <div className="flex justify-between items-center text-[9px] font-mono-custom text-zinc-450">
                      <span>Source reliability:</span>
                      <span className="text-emerald-400 font-bold">{Math.round(f.confidence * 100)}%</span>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-xs text-zinc-655 italic">No findings claims recorded.</p>
          )}
        </div>

      </div>

      {/* Panel Telemetry Footer */}
      <div className="p-3 bg-[#131415] border-t border-[#2a2c2c] text-[9px] font-mono-custom text-zinc-550 flex justify-between shrink-0 select-none">
        <span>Orchestrated events: {current.events?.length || 0} completed</span>
        <span className="text-[#10B981] font-bold">VERIFIED DB SCHEMA</span>
      </div>

    </div>
  );
}
