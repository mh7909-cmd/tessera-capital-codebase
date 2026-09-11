"use client";

import { useState, useEffect, useRef } from "react";
import { Activity, Shield, Terminal, Zap, Info, Cpu, Globe, ExternalLink } from "lucide-react";

// --- Types ---
interface LogEntry {
  id: string;
  data: string;
}

interface UiSignal {
  type: string;
  phase?: string;
  ticker?: string;
  gid?: string;
  msg?: string;
}

// --- Sheet constants (match .env) ---
const SHEET_DILIGENCE = "1HN7Fm3zoK6EsuGmzaLd4Hrj_fKJYMbZsCrmMJcrjRr8";
// Pipeline Queue + Leads are tabs on the SAME sheet — differentiated by gid only
const SHEET_PIPELINE  = "1sH3zh2R2eUWsGFZr4oLe6hV5W47ulr_5JJzhFydcjTM";
const GID_PIPELINE    = "1461012877";   // "Pipeline Queue" tab
const GID_LEADS       = "869077955";    // "Leads" tab

// Phase → { sheetId, gid, label } mapping for auto-switching
const PHASE_SHEET_MAP: Record<string, { sheetId: string; gid: string; label: string }> = {
  IDLE:             { sheetId: SHEET_DILIGENCE, gid: "0",          label: "DILIGENCE DOSSIER" },
  SYNCING:          { sheetId: SHEET_DILIGENCE, gid: "0",          label: "DILIGENCE DOSSIER" },
  DILIGENCE:        { sheetId: SHEET_DILIGENCE, gid: "0",          label: "DILIGENCE DOSSIER" },
  GRAPH_BUILD:      { sheetId: SHEET_DILIGENCE, gid: "0",          label: "DILIGENCE DOSSIER" },
  ON_CALL:          { sheetId: SHEET_DILIGENCE, gid: "0",          label: "DILIGENCE DOSSIER" },
  PROCESSING_CALL:  { sheetId: SHEET_PIPELINE,  gid: GID_PIPELINE, label: "PIPELINE QUEUE" },
  OUTREACH:         { sheetId: SHEET_PIPELINE,  gid: GID_PIPELINE, label: "PIPELINE QUEUE" },
  HANDOFF:          { sheetId: SHEET_PIPELINE,  gid: GID_PIPELINE, label: "PIPELINE QUEUE" },
  DEBATING:         { sheetId: SHEET_PIPELINE,  gid: GID_LEADS,    label: "LEADS DATABASE" },
  TRADING:          { sheetId: SHEET_PIPELINE,  gid: GID_LEADS,    label: "LEADS DATABASE" },
  DONE:             { sheetId: SHEET_PIPELINE,  gid: GID_LEADS,    label: "LEADS DATABASE" },
};

export default function CommandCenter() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [currentPhase, setCurrentPhase] = useState<string>("IDLE");
  const [currentScreen, setCurrentScreen] = useState<string>("DOSSIER");
  const [activeTicker, setActiveTicker] = useState<string>("");
  const [currentGid, setCurrentGid] = useState<string>("0");
  const [currentSheetId, setCurrentSheetId] = useState<string>(SHEET_DILIGENCE);
  const [currentSheetLabel, setCurrentSheetLabel] = useState<string>("DILIGENCE DOSSIER");
  const [isLaunching, setIsLaunching] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [gidLocked, setGidLocked] = useState(false);
  const [targetInput, setTargetInput] = useState("");
  const [activeProjectId, setActiveProjectId] = useState<string>("");
  const [activeSimId, setActiveSimId] = useState<string>("");

  const terminalRef = useRef<HTMLDivElement>(null);

  // --- Live Status Bridge ---
  useEffect(() => {
    // Add a small delay to ensure bridge is up
    const timer = setTimeout(() => {
      const eventSource = new EventSource("http://localhost:8000/events");

    eventSource.onmessage = (event) => {
      const payload = JSON.parse(event.data);

      if (payload.event === "log") {
        setLogs(prev => {
          const logData = payload.data;
          
          // --- In-Place Terminal Updates for [AGENTS] ---
          // Detects if the log is a progress update (🔄) or completion (✅)
          const isAgentLog = logData.includes("[AGENTS]");
          const isProgress = logData.includes("🔄");
          const isDone = logData.includes("✅");

          if (isAgentLog && (isProgress || isDone)) {
            // Extract the identifier (e.g., "Technical Analyst [FLY]")
            const keyMatch = logData.match(/\[AGENTS\] (?:🔄|✅) ([^:]+):?|\[AGENTS\] ✅ ([^\[]+) (\[[^\]]+\])/);
            if (keyMatch) {
              const agentKey = keyMatch[1] || `${keyMatch[2].trim()} ${keyMatch[3]}`;
              // Look for the last 'in-progress' log for this agent
              const existingIndex = prev.findLastIndex(l => 
                l.data.includes("[AGENTS]") && 
                l.data.includes(agentKey) &&
                (l.data.includes("🔄") || l.data.includes("✅"))
              );

              if (existingIndex !== -1) {
                const newLogs = [...prev];
                // Replace the line with the new update
                newLogs[existingIndex] = { id: prev[existingIndex].id, data: logData };
                return newLogs;
              }
            }
          }

          return [...prev.slice(-100), { id: crypto.randomUUID(), data: logData }];
        });
      }
      else if (payload.event === "signal") {
        const signal = payload.data;

        if (signal.type === "PHASE_CHANGE") {
          const phase = signal.phase || "IDLE";
          setCurrentPhase(phase);
          // Auto-switch sheet + gid + label based on phase
          const mapped = PHASE_SHEET_MAP[phase];
          if (mapped) {
            setCurrentSheetId(mapped.sheetId);
            setCurrentGid(mapped.gid);
            setCurrentSheetLabel(mapped.label);
          // Return to DOSSIER for non-simulation phases (Stay on MiroFish if DONE to allow report viewing)
          if (!["SIMULATING", "UPLOADING", "DONE"].includes(phase)) {
            setCurrentScreen("DOSSIER");
              setIsSyncing(true);
              setTimeout(() => setIsSyncing(false), 700);
            }
          }
        }
        else if (signal.type === "LOCK_VIEW") {
          if (signal.sheet_id) setCurrentSheetId(signal.sheet_id);
          if (signal.gid) {
            setCurrentGid(signal.gid);
            // Infer label from gid if not provided
            const inferredLabel = signal.label ||
              (signal.gid === GID_LEADS ? "LEADS DATABASE" :
               signal.gid === GID_PIPELINE ? "PIPELINE QUEUE" : "DILIGENCE DOSSIER");
            setCurrentSheetLabel(inferredLabel);
          }
          setGidLocked(true);
          setActiveTicker(signal.ticker || "SCANNING");
          setCurrentScreen("DOSSIER");
          setIsSyncing(true);
          setTimeout(() => setIsSyncing(false), 800);
        }
        else if (signal.type === "UNLOCK_VIEW") {
          setGidLocked(false);
          if (signal.sheet_id) setCurrentSheetId(signal.sheet_id);
          if (signal.gid) {
            setCurrentGid(signal.gid);
            const inferredLabel = signal.label ||
              (signal.gid === GID_LEADS ? "LEADS DATABASE" :
               signal.gid === GID_PIPELINE ? "PIPELINE QUEUE" : "DILIGENCE DOSSIER");
            setCurrentSheetLabel(inferredLabel);
          }
          setCurrentScreen("DOSSIER");
          setIsSyncing(true);
          setTimeout(() => setIsSyncing(false), 800);
        }
        else if (signal.type === "TAB_FOCUS") {
          setActiveTicker(signal.ticker || "");
          if (!gidLocked) {
            setIsSyncing(true);
            if (signal.sheet_id) setCurrentSheetId(signal.sheet_id);
            if (signal.gid) {
              setCurrentGid(signal.gid);
              // Infer label from gid — TAB_FOCUS from diligence doesn't send a label
              if (!signal.label) {
                if (signal.gid === GID_LEADS) setCurrentSheetLabel("LEADS DATABASE");
                else if (signal.gid === GID_PIPELINE) setCurrentSheetLabel("PIPELINE QUEUE");
                else setCurrentSheetLabel("DILIGENCE DOSSIER");
              } else {
                setCurrentSheetLabel(signal.label);
              }
            }
            setTimeout(() => setIsSyncing(false), 800);
          }
        }
        else if (signal.type === "SCREEN_SWITCH") {
          if (signal.screen === "MIROFISH") {
            setActiveProjectId("");
            setActiveSimId("");
            setCurrentScreen("MIROFISH");
          } else if (signal.screen === "DOSSIER") {
            setCurrentScreen("DOSSIER");
          } else if (signal.screen === "PIPELINE_QUEUE") {
            setCurrentSheetId(SHEET_PIPELINE);
            setCurrentGid(GID_PIPELINE);
            setCurrentSheetLabel("PIPELINE QUEUE");
            setCurrentScreen("DOSSIER");
            setIsSyncing(true);
            setTimeout(() => setIsSyncing(false), 700);
          } else if (signal.screen === "LEADS") {
            setCurrentSheetId(SHEET_PIPELINE);
            setCurrentGid(GID_LEADS);
            setCurrentSheetLabel("LEADS DATABASE");
            setCurrentScreen("DOSSIER");
            setIsSyncing(true);
            setTimeout(() => setIsSyncing(false), 700);
          }
        }
        else if (signal.type === "MIROFISH_LIVE") {
          // Stage 3: graph ready — load the iframe. Never include simId in src
          // (changing src causes a full reload and double-tweet problem).
          if (signal.project_id) setActiveProjectId(signal.project_id);
          // Pass maxRounds=10 to the initial load
          setCurrentScreen("MIROFISH");
        }
        else if (signal.type === "MIROFISH_SIM_READY") {
          // Stage 4: simulation prepared — pass simId into the already-loaded iframe
          // via postMessage so src stays frozen and Vue app never remounts.
          if (signal.simulation_id) {
            setActiveSimId(signal.simulation_id);
            const iframe = document.querySelector('iframe[title="MiroFish Live Simulation"]') as HTMLIFrameElement;
            if (iframe?.contentWindow) {
              iframe.contentWindow.postMessage(
                { 
                  type: "MIROFISH_SIM_READY", 
                  simId: signal.simulation_id,
                  maxRounds: signal.max_rounds || 10 
                },
                "http://localhost:3001"
              );
            }
          }
        }
        else if (signal.type === "SHEET_SWITCH") {
          setIsSyncing(true);
          if (signal.sheet_id) setCurrentSheetId(signal.sheet_id);
          if (signal.gid) setCurrentGid(signal.gid);
          if (signal.label) setCurrentSheetLabel(signal.label);
          setTimeout(() => setIsSyncing(false), 800);
        }
        else if (signal.type === "PIPELINE_UPDATE") {
          // No auto-Gmail — user shows it manually during demo
        }
        else if (signal.type === "BROWSER_OPEN") {
          if (signal.url) window.open(signal.url, "_blank");
        }
      }
    };

      eventSource.onerror = (err) => {
        console.error("EventSource failed connecting to bridge:", err);
      };

      return () => {
        eventSource.close();
      };
    }, 500);

    return () => clearTimeout(timer);
  }, []);

  // Auto-scroll terminal
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

  const launchWorkflow = async () => {
    setIsLaunching(true);
    const tickerToLaunch = targetInput.trim().toUpperCase();
    setLogs([]);
    
    // Dynamic Log Utility
    const addInstitutionalLog = (msg: string) => {
      setLogs(prev => [...prev, { id: crypto.randomUUID(), data: `[SYSTEM] ${msg}` }]);
    };

    setTargetInput(""); // Clear input immediately for a clean UX

    addInstitutionalLog("Connecting to Strategic Audit Pipeline...");

    try {
      await fetch("http://localhost:8000/launch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker: tickerToLaunch || null })
      });
    } catch (err) {
      console.error("Launch failed:", err);
      addInstitutionalLog("CRITICAL: Failed to establish secure uplink.");
    }
    setIsLaunching(false);
  };

  return (
    <main className="flex h-screen w-full flex-col overflow-hidden bg-[#131313] text-[#e5e2e1] selection:bg-[#b90040]/30 selection:text-white">

      {/* Institutional Top Bar (Professional & High-Fidelity) */}
      <nav className="flex items-center justify-between bg-[#0A0A0B] px-12 h-[90px] relative z-50 border-b border-[#b90040]/10 shadow-2xl">
        <div className="flex items-center gap-12">
          {/* Brand Monolith - Tessera Capital Logo */}
          <div className="flex items-center gap-6">
            <div className="grid grid-cols-2 gap-1 w-8 h-8">
               <div className="w-full h-full bg-[#b90040]" />
               <div className="w-full h-full bg-[#d67b97]" />
               <div className="w-full h-full bg-[#d67b97]" />
               <div className="w-full h-full bg-[#b90040]" />
            </div>
            <div className="flex flex-col">
              <span className="font-display font-black text-2xl tracking-[-0.02em] text-[#b90040] leading-none">TESSERA CAPITAL</span>
              <span className="text-[10px] font-display font-bold tracking-[0.4em] text-slate-600 uppercase mt-1">Strategic Audit Terminal</span>
            </div>
          </div>

          {/* Real Contextual Metadata */}
          <div className="hidden xl:flex items-center gap-8 px-8 h-12 bg-black border border-[#b90040]/10">
            <div className="flex flex-col">
              <span className="text-[7px] font-display font-bold text-slate-700 tracking-[0.3em] uppercase mb-0.5">ACTIVE TICKER</span>
              <span className={`text-[13px] font-mono font-bold tracking-widest ${activeTicker ? 'text-[#b90040]' : 'text-slate-800'}`}>
                {activeTicker || "NONE"}
              </span>
            </div>
            <div className="h-6 w-[1px] bg-[#b90040]/10" />
            <div className="flex flex-col">
              <span className="text-[7px] font-display font-bold text-slate-700 tracking-[0.3em] uppercase mb-0.5">PIPELINE PHASE</span>
              <span className="text-[13px] font-mono font-bold text-slate-500 tracking-widest uppercase">{currentPhase}</span>
            </div>
          </div>
        </div>

        {/* Master Action Group */}
        <div className="flex items-center gap-6">
          <input
            type="text"
            placeholder="ENTER TICKER"
            value={targetInput}
            onChange={(e) => setTargetInput(e.target.value)}
            disabled={isLaunching || (currentPhase !== "IDLE" && currentPhase !== "DONE")}
            style={{
              paddingLeft: '16px',
              paddingRight: '16px',
              height: '44px',
              width: '256px',
              backgroundColor: '#000000',
              border: '1px solid rgba(185, 0, 64, 0.3)',
              color: '#ffffff',
              fontFamily: 'monospace',
              fontSize: '12px',
              fontWeight: 'bold',
              borderRadius: '2px',
              letterSpacing: '0.15em',
              outline: 'none',
              textTransform: 'uppercase',
            }}
            className="hover:border-[#b90040]/70 focus:border-[#b90040] focus:shadow-[0_0_15px_rgba(185,0,64,0.1)] transition-all placeholder:text-slate-700 disabled:opacity-50"
          />
          <button
            onClick={launchWorkflow}
            disabled={isLaunching || (currentPhase !== "IDLE" && currentPhase !== "DONE")}
            className="px-8 h-[44px] bg-[#b90040] hover:bg-[#d6004a] text-white text-[12px] font-black tracking-[0.1em] rounded-sm transition-all shadow-[0_0_25px_rgba(185,0,64,0.15)] disabled:bg-[#1A1A1C] disabled:text-slate-800 uppercase"
          >
            {isLaunching ? "EXECUTING..." : "Initiate Swarm"}
          </button>
        </div>
      </nav>

      {/* Primary Layout Area */}
      <div className="flex flex-1 overflow-hidden px-8 pt-4 pb-12 gap-8 bg-[#050505]">

        {/* LEFT (75%): DYNAMIC SHEET PANEL */}
        <section className="flex-[3] flex flex-col bg-black relative overflow-hidden group rounded-sm border border-[#b90040]/10 shadow-2xl">
          {/* Section Header — dynamically labelled */}
          <div className="px-8 py-5 flex items-center justify-between border-b border-[#b90040]/5">
            <div className="flex items-center gap-4">
              {/* View indicator dot — color-coded by sheet */}
              <div className={`w-1.5 h-1.5 rounded-full ${
                currentSheetLabel === "PIPELINE QUEUE" ? "bg-amber-500" :
                currentSheetLabel === "LEADS DATABASE" ? "bg-emerald-600" :
                "bg-[#b90040]"
              } ${isSyncing ? "animate-ping" : ""}`} />
              <span className={`text-[10px] font-display font-black tracking-[0.3em] uppercase ${
                currentSheetLabel === "PIPELINE QUEUE" ? "text-amber-700" :
                currentSheetLabel === "LEADS DATABASE" ? "text-emerald-800" :
                "text-slate-700"
              }`}>
                {currentSheetLabel}
              </span>
              <div className={`h-[1px] w-12 ${
                currentSheetLabel === "PIPELINE QUEUE" ? "bg-amber-500/20" :
                currentSheetLabel === "LEADS DATABASE" ? "bg-emerald-600/20" :
                "bg-[#b90040]/10"
              }`} />
            </div>

            {/* Right-side status badge */}
            {activeTicker && currentScreen === "DOSSIER" && (
              <div className={`flex items-center gap-3 py-1 px-3 rounded-sm border ${
                currentSheetLabel === "PIPELINE QUEUE"
                  ? "bg-amber-500/5 border-amber-500/20"
                  : currentSheetLabel === "LEADS DATABASE"
                  ? "bg-emerald-600/5 border-emerald-600/20"
                  : "bg-[#b90040]/5 border-[#b90040]/10"
              }`}>
                <div className={`w-1.5 h-1.5 rounded-full animate-pulse ${
                  currentSheetLabel === "PIPELINE QUEUE" ? "bg-amber-500" :
                  currentSheetLabel === "LEADS DATABASE" ? "bg-emerald-500" :
                  "bg-[#b90040]"
                }`} />
                <span className={`text-[9px] font-display font-bold tracking-[0.2em] uppercase ${
                  currentSheetLabel === "PIPELINE QUEUE" ? "text-amber-600/80" :
                  currentSheetLabel === "LEADS DATABASE" ? "text-emerald-600/80" :
                  "text-[#b90040]/80"
                }`}>
                  {currentSheetLabel === "PIPELINE QUEUE" ? "OUTREACH ACTIVE" :
                   currentSheetLabel === "LEADS DATABASE"  ? "CONVICTION SIGNAL" :
                   "ACTIVE RESEARCH FLOW"}
                </span>
              </div>
            )}
          </div>

          {/* Google Sheet Container */}
          <div className="flex-1 m-6 mt-0 relative overflow-hidden bg-black rounded-sm border border-[#b90040]/5 shadow-inner">
            {currentScreen === "DOSSIER" ? (
              (activeTicker || gidLocked) ? (
                <div className="absolute top-0 left-0 w-[142.85%] h-[142%] origin-top-left scale-[0.68] transition-all duration-1000 ease-out p-0 m-0">
                  <iframe
                    src={`https://docs.google.com/spreadsheets/d/${currentSheetId}/edit?gid=${currentGid}&rm=demo&rm=minimal&headers=false&chrome=false&widget=true`}
                    className="h-full border-0"
                    style={{ width: '2200px' }}
                    title="Dossier Viewer"
                  />
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full w-full bg-black">
                  <Activity size={32} className="text-[#b90040]/10 mb-6" />
                  <span className="font-display font-bold text-[10px] tracking-[1em] text-slate-900 uppercase">
                    Awaiting Targeting Matrix
                  </span>
                </div>
              )
            ) : currentScreen === "MIROFISH" ? (
              <div className="flex-1 relative overflow-hidden bg-black flex flex-col h-full">
                <div className="h-10 border-b border-[#b90040]/5 flex items-center justify-between px-6 bg-black">
                  <div className="flex items-center gap-2">
                    <Zap size={14} className="text-[#b90040]/40" />
                    <span className="text-[9px] font-display font-black text-slate-700 tracking-[0.2em] uppercase">LIVE SIMULATION TELEMETRY</span>
                  </div>
                </div>
                <iframe
                  src={activeProjectId
                    ? `http://localhost:3001/process/${activeProjectId}?maxRounds=10`
                    : `http://localhost:3001`}
                  className="w-full h-full border-0"
                  title="MiroFish Live Simulation"
                />
              </div>
            ) : (
                <div className="flex h-full w-full bg-black flex-col relative overflow-hidden">
                   <div className="h-12 border-b border-[#b90040]/5 flex items-center justify-between px-6 bg-black">
                      <div className="flex items-center gap-3">
                         <div className="w-1.5 h-1.5 rounded-full bg-[#b90040]/20" />
                         <span className="text-[9px] font-display font-black text-slate-700 tracking-[0.2em] uppercase">OUTBOX MONITOR</span>
                      </div>
                      <div className="flex items-center gap-4">
                        <button 
                          onClick={() => window.open("https://mail.google.com/mail/u/0/#sent", "_blank")}
                          className="flex items-center gap-2 px-3 py-1 bg-[#b90040]/5 border border-[#b90040]/10 rounded-sm text-[8px] font-display font-bold text-[#b90040]/60 hover:text-[#b90040] transition-all uppercase tracking-widest"
                        >
                          <ExternalLink size={10} /> View Gmail Sent
                        </button>
                      </div>
                   </div>

                   <div className="flex-1 relative flex">
                      <div className="flex-[2] relative overflow-hidden border-r border-[#b90040]/5">
                        {currentPhase === "IDLE" ? (
                          <div className="absolute inset-0 z-50 bg-black flex flex-col items-center justify-center gap-4">
                            <span className="text-[8px] font-mono text-[#b90040]/20 tracking-[0.3em] uppercase">Monitor Offline</span>
                          </div>
                        ) : null}
                         <div className="absolute top-0 left-0 w-[142.85%] h-[142%] origin-top-left scale-[0.68] p-0 m-0">
                            <iframe
                              src={`https://docs.google.com/spreadsheets/d/1mBVNvsg6xnB4hV8Uc0YoAHX76gnrJTcBXmGNLe6bLZQ/edit?gid=${currentGid}&rm=minimal`}
                              className="w-full h-full border-0"
                              title="Outreach Monitor"
                            />
                         </div>
                      </div>

                      <div className="flex-1 bg-black p-6 flex flex-col gap-8">
                        <div className="space-y-3">
                           <h3 className="text-[10px] font-black text-[#b90040]/40 uppercase tracking-widest">Swarm Status</h3>
                           <div className="p-3 bg-black border border-[#b90040]/10 rounded-sm">
                              <div className="flex items-center justify-between text-[9px] uppercase font-bold text-slate-800">
                                 <span>Threads Active</span>
                                 <span className="text-[#b90040]/60">6/6</span>
                              </div>
                              <div className="w-full h-[1px] bg-[#b90040]/5 mt-2">
                                 <div className="w-full h-full bg-[#b90040]/20" />
                              </div>
                           </div>
                        </div>

                        <div className="flex-1 flex flex-col min-h-0">
                           <h3 className="text-[10px] font-black text-[#b90040]/40 uppercase tracking-widest mb-4">Activity Feed</h3>
                           <div className="flex-1 bg-black p-4 rounded-sm border border-[#b90040]/10 font-mono text-[9px] text-[#b90040]/30 overflow-y-auto space-y-2">
                              <div className="text-[#b90040]/40">[SYSTEM] Outreach swarm synchronized...</div>
                              <div className="text-[#b90040]/30 animate-pulse">[OUTBOUND] Dispatching expert inquiries...</div>
                              {logs.slice(-12).map((log, i) => (
                                <div key={i} className="truncate border-l border-[#b90040]/10 pl-2">{log.data}</div>
                              ))}
                           </div>
                        </div>
                      </div>

                      <button 
                        onClick={() => setCurrentScreen("DOSSIER")}
                        className="absolute bottom-6 left-6 z-50 px-3 py-1.5 bg-black border border-[#b90040]/20 rounded-sm text-[8px] font-display font-bold text-[#b90040]/40 tracking-[0.2em] hover:text-[#b90040] transition-all uppercase"
                      >
                        Return to Dossier
                      </button>
                   </div>
                </div>
            )}
          </div>
        </section>

        {/* RIGHT (25%): REASONING STREAM */}
        <aside className="flex-1 flex flex-col bg-black relative overflow-hidden rounded-sm border border-[#b90040]/10 shadow-2xl">
          {/* Header */}
          <div className="px-8 py-5 flex items-center justify-between border-b border-[#b90040]/5">
            <div className="flex items-center gap-3">
              <Terminal size={14} className="text-[#b90040]/40" />
              <span className="text-[10px] font-display font-black text-slate-700 tracking-[0.25em] uppercase">Reasoning Audit</span>
            </div>
          </div>

          {/* Terminal Area */}
          <div
            ref={terminalRef}
            className="flex-1 mx-6 mb-6 mt-3 p-4 overflow-y-auto text-[11px] leading-relaxed font-mono text-slate-800 selection:bg-[#b90040]/20"
            style={{ scrollbarWidth: 'thin', scrollbarColor: '#b9004010 #000' }}
          >
            {logs.length === 0 && (
              <div className="opacity-40 text-slate-900 tracking-widest mt-2 space-y-4">
                <div className="flex gap-4 items-center">
                  <span className="text-slate-950">_</span>
                  <span className="uppercase text-[9px]">Awaiting system initialization...</span>
                </div>
              </div>
            )}

            {logs.map((log) => {
              const isError    = log.data.includes("Failed") || log.data.includes("ERROR") || log.data.includes("Hit (429)");
              const isSuccess  = log.data.includes("SUCCESS") || log.data.includes("Done") || log.data.includes("✅");
              const isSystem   = log.data.includes("[SYSTEM]");
              const isTrading  = log.data.includes("[TRADING]");
              const isReport   = log.data.includes("[REPORT]");
              // Detects [AGENT 1/20], [AGENT 16/20], etc.
              const isAgentHeader = /\[AGENT \d+\/\d+\]/.test(log.data);

              let displayData = log.data;
              const asciiArtChars = (displayData.match(/[|/\\_\[\]]/g) || []).length;
              // Relaxed threshold for institutional logs that use brackets/separators
              if (asciiArtChars > displayData.length * 0.85 && displayData.length > 30) return null;
              if (displayData.includes('File "/') || displayData.includes('line ')) return null;

              const textColor =
                isError       ? 'text-rose-500 font-bold' :
                isAgentHeader ? 'text-amber-400 font-black tracking-wide' :
                isTrading     ? 'text-cyan-400 font-bold' :
                isReport      ? 'text-sky-400 font-bold' :
                isSuccess     ? 'text-emerald-400' :
                isSystem      ? 'text-slate-100 font-bold' :
                                'text-slate-300';

              const borderColor = isAgentHeader ? 'border-amber-400/40' : 'border-[#b90040]/10';

              return (
                <div key={log.id} className={`mb-3 pl-4 border-l ${borderColor} hover:border-[#b90040]/40 transition-colors`}>
                  <div className={`break-words whitespace-pre-wrap tracking-tight ${textColor}`}>
                    {displayData}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Footer Status (Real Connection Indicator) */}
          <div className="p-6 bg-black flex flex-col gap-2">
            <div className="flex justify-between items-center text-[7px] font-display font-bold text-slate-900 tracking-[0.3em] uppercase">
              <span>SYSTEM TELEMETRY</span>
              <span className="text-[#b90040]/40">SYNCHRONIZED</span>
            </div>
            <div className="w-full h-[1px] bg-[#b90040]/5">
               <div className="w-full h-full bg-[#b90040]/10" />
            </div>
          </div>
        </aside>

      </div>
    </main>
  );
}
