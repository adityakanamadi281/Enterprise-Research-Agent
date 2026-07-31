"use client";

import { FileBadge, X, Cpu, Download } from "lucide-react";

type ReportModalProps = {
  reportModalOpen: boolean;
  setReportModalOpen: (open: boolean) => void;
  reportTitle: string;
  reportData: any;
  setReportData: (data: any) => void;
  generatingReport: boolean;
};

export default function ReportModal({
  reportModalOpen,
  setReportModalOpen,
  reportTitle,
  reportData,
  setReportData,
  generatingReport,
}: ReportModalProps) {
  if (!reportModalOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/85 flex items-center justify-center p-4 z-50 backdrop-blur-sm transition-all duration-300">
      
      <div className="bg-[#191a1a] border border-[#2a2c2c] rounded-2xl w-full max-w-3xl max-h-[85vh] overflow-hidden flex flex-col shadow-2xl">
        
        {/* Modal Header */}
        <div className="p-4 border-b border-[#2a2c2c] flex items-center justify-between bg-[#202222]/30 select-none">
          <div className="flex items-center gap-2">
            <FileBadge className="h-4.5 w-4.5 text-[#10B981]" />
            <h3 className="font-bold text-white text-xs uppercase tracking-wider">Executive briefing compiler</h3>
          </div>
          <button 
            onClick={() => { setReportModalOpen(false); setReportData(null); }}
            className="p-1 rounded-md hover:bg-[#202222] text-zinc-400 hover:text-white"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-6 select-text">
          
          {!reportData ? (
            <div className="py-20 text-center space-y-4">
              <span className="h-8 w-8 rounded-full bg-[#10B981]/15 text-[#10B981] flex items-center justify-center animate-spin border-t-2 border-[#10B981] mx-auto shrink-0" />
              <p className="text-xs font-mono-custom text-zinc-500">Compiling SQL evidence schemas and primary references...</p>
            </div>
          ) : (
            <div className="space-y-6 text-zinc-300 print:text-black">
              
              {/* Document Header */}
              <div className="border-b-2 border-zinc-800 pb-5 text-center space-y-2">
                <p className="text-[9px] font-mono-custom text-[#10B981] uppercase tracking-widest">
                  Atlas Intelligence Document
                </p>
                <h2 className="text-xl font-bold text-white tracking-tight">
                  {reportData.title}
                </h2>
                <div className="flex items-center justify-center gap-4 text-[9px] font-mono-custom text-zinc-500">
                  <span>Generated: {new Date(reportData.generated_at).toLocaleString()}</span>
                  <span>•</span>
                  <span>Confidence score: {Math.round(reportData.confidence * 100)}%</span>
                </div>
              </div>

              {/* Research Question */}
              <div className="space-y-1">
                <h4 className="text-[10px] font-bold text-zinc-550 uppercase tracking-widest font-mono-custom">
                  Subject Matter
                </h4>
                <p className="text-xs font-bold text-white leading-normal">
                  {reportData.research_question}
                </p>
              </div>

              {/* Synthesis Conclusion */}
              <div className="space-y-1.5">
                <h4 className="text-[10px] font-bold text-zinc-550 uppercase tracking-widest font-mono-custom">
                  Executive Summary
                </h4>
                <p className="text-xs leading-relaxed text-zinc-250 bg-zinc-950 p-4 border border-[#2a2c2c] rounded-xl whitespace-pre-line">
                  {reportData.executive_summary}
                </p>
              </div>

              {/* Evidence Findings */}
              <div className="space-y-3">
                <h4 className="text-[10px] font-bold text-zinc-550 uppercase tracking-widest font-mono-custom">
                  Verified Findings & Quotes
                </h4>
                
                <div className="space-y-3.5">
                  {reportData.evidence_findings && reportData.evidence_findings.length > 0 ? (
                    reportData.evidence_findings.map((f: any, idx: number) => (
                      <div key={idx} className="p-3 bg-zinc-950/40 border border-[#2a2c2c] rounded-xl space-y-2 text-xs">
                        <div className="flex justify-between text-zinc-500 font-mono-custom text-[9px]">
                          <span>CLAIM FINDING {idx + 1}</span>
                          <span>RELIABILITY INDEX: {Math.round(f.confidence * 100)}%</span>
                        </div>
                        <p className="font-semibold text-white">{f.claim}</p>
                        <p className="text-zinc-400 italic leading-relaxed bg-[#191a1a]/60 p-2.5 rounded border border-[#2a2c2c]/40">&ldquo;{f.evidence_span}&rdquo;</p>
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-zinc-655">No claims gathered.</p>
                  )}
                </div>
              </div>

              {/* Reference lists */}
              <div className="space-y-2.5">
                <h4 className="text-[10px] font-bold text-zinc-550 uppercase tracking-widest font-mono-custom">
                  Citations references
                </h4>
                
                <div className="space-y-2">
                  {reportData.sources && reportData.sources.length > 0 ? (
                    reportData.sources.map((s: any, idx: number) => (
                      <div key={idx} className="text-xs flex gap-2">
                        <span className="font-mono-custom font-bold text-[#10B981] shrink-0">[{idx + 1}]</span>
                        <div>
                          <p className="font-medium text-white line-clamp-1">{s.title}</p>
                          <p className="text-zinc-500 font-mono-custom text-[9px]">
                            Publisher: {s.publisher || "Academic Publisher"} | DOI: <a href={s.url} target="_blank" rel="noreferrer" className="text-emerald-400 underline">{s.url}</a>
                          </p>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-zinc-655">No references loaded.</p>
                  )}
                </div>
              </div>

              {/* Footer disclaimer */}
              <div className="border-t border-zinc-800 pt-4 text-[9px] font-mono-custom text-zinc-555 italic text-center">
                {reportData.disclaimer}
              </div>

            </div>
          )}

        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-[#2a2c2c] flex items-center justify-end gap-3 bg-[#202222]/30 select-none">
          <button 
            onClick={() => { setReportModalOpen(false); setReportData(null); }}
            className="px-4 py-2 rounded-xl bg-[#191a1a] border border-[#2a2c2c] text-xs font-mono-custom text-zinc-400 hover:text-white"
          >
            Close
          </button>
          
          <button 
            onClick={() => window.print()}
            disabled={!reportData}
            className="px-4 py-2 rounded-xl bg-[#10B981] hover:bg-emerald-400 disabled:opacity-40 disabled:pointer-events-none text-[#191a1a] font-bold text-xs font-mono-custom"
          >
            Print Report
          </button>
        </div>

      </div>

    </div>
  );
}
