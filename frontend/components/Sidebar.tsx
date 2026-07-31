"use client";

import { BookMarked, Database, BarChart3, Search, User, History } from "lucide-react";

type Session = { 
  id: string; 
  question: string; 
  status: string; 
  confidence: number; 
  conclusion?: string; 
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

type SidebarProps = {
  activeTab: "search" | "library" | "knowledge" | "metrics";
  setActiveTab: (tab: "search" | "library" | "knowledge" | "metrics") => void;
  setCurrent: (session: any | null) => void;
  setQuestion: (question: string) => void;
  setError: (error: string) => void;
  sessions: Session[];
  loadSession: (id: string) => void;
  metrics: Metrics | null;
};

export default function Sidebar({
  activeTab,
  setActiveTab,
  setCurrent,
  setQuestion,
  setError,
  sessions,
  loadSession,
  metrics,
}: SidebarProps) {
  return (
    <aside className="w-56 border-r border-[#2a2c2c] bg-[#191a1a] flex flex-col justify-between shrink-0 z-30 select-none">
      <div className="flex flex-col flex-1 overflow-hidden">
        
        {/* Logo Brand */}
        <div className="p-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="h-6 w-6 rounded-full bg-[#10B981] flex items-center justify-center text-[#191a1a] font-bold text-sm shadow-[0_0_12px_rgba(16,185,129,0.3)]">
              ✦
            </span>
            <span className="font-black text-sm tracking-wider text-white">ATLAS</span>
          </div>
          <span className="text-[9px] font-mono-custom text-[#10B981] bg-[#10B981]/15 px-1.5 py-0.5 rounded border border-[#10B981]/25">
            PRO
          </span>
        </div>

        {/* New Thread Button */}
        <div className="px-3 py-2">
          <button 
            onClick={() => {
              setCurrent(null);
              setQuestion("");
              setActiveTab("search");
              setError("");
            }}
            className="w-full flex items-center justify-between py-2 px-3.5 rounded-full border border-[#2a2c2c] bg-[#202222] hover:bg-[#2a2c2c] text-white font-medium text-xs transition-all active:scale-[0.98] group"
          >
            <span>New Thread</span>
            <span className="h-5 w-5 rounded-full bg-[#191a1a] border border-[#2a2c2c] flex items-center justify-center text-zinc-500 group-hover:text-white text-xs">
              +
            </span>
          </button>
        </div>

        {/* Main Navigation Links */}
        <nav className="px-2 py-3 space-y-0.5">
          <button 
            onClick={() => setActiveTab("search")}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === "search" 
                ? "bg-[#202222] text-[#10B981]" 
                : "text-zinc-400 hover:text-zinc-200 hover:bg-[#202222]/50"
            }`}
          >
            <Search className="h-4 w-4 shrink-0" />
            Search & Thread
          </button>

          <button 
            onClick={() => setActiveTab("library")}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === "library" 
                ? "bg-[#202222] text-[#10B981]" 
                : "text-zinc-400 hover:text-zinc-200 hover:bg-[#202222]/50"
            }`}
          >
            <BookMarked className="h-4 w-4 shrink-0" />
            Library
          </button>
          
          <button 
            onClick={() => { 
              setActiveTab("knowledge"); 
            }}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === "knowledge" 
                ? "bg-[#202222] text-[#10B981]" 
                : "text-zinc-400 hover:text-zinc-200 hover:bg-[#202222]/50"
            }`}
          >
            <Database className="h-4 w-4 shrink-0" />
            Knowledge base
          </button>

          <button 
            onClick={() => { 
              setActiveTab("metrics"); 
            }}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === "metrics" 
                ? "bg-[#202222] text-[#10B981]" 
                : "text-zinc-400 hover:text-zinc-200 hover:bg-[#202222]/50"
            }`}
          >
            <BarChart3 className="h-4 w-4 shrink-0" />
            Operations metrics
          </button>
        </nav>

        {/* Quick sessions history outline */}
        <div className="flex-1 overflow-y-auto px-2 space-y-1 mt-4 border-t border-[#2a2c2c]/40 pt-4">
          <span className="px-3 text-[10px] font-mono-custom text-zinc-500 uppercase tracking-wider block mb-2">
            Recent Threads
          </span>
          {sessions.slice(0, 6).map((s) => (
            <button
              key={s.id}
              onClick={() => loadSession(s.id)}
              className="w-full text-left px-3 py-1.5 rounded-md text-[11px] font-medium truncate block text-zinc-400 hover:text-zinc-200 hover:bg-[#202222]/20"
            >
              {s.question}
            </button>
          ))}
        </div>

      </div>

      {/* Sidebar Footer profile section */}
      <div className="p-3 border-t border-[#2a2c2c] bg-[#191a1a]">
        <div className="flex items-center gap-2.5 p-2 rounded-xl hover:bg-[#202222] cursor-pointer group">
          <div className="h-8 w-8 rounded-full bg-[#10B981]/10 border border-[#10B981]/30 flex items-center justify-center text-[#10B981]">
            <User className="h-4 w-4" />
          </div>
          <div className="overflow-hidden">
            <p className="text-xs font-bold text-white truncate leading-none mb-1">Modus Hackathon</p>
            <p className="text-[10px] font-mono-custom text-zinc-500 leading-none">Enterprise User</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
