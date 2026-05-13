import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Activity, ShieldAlert, Cpu, TrendingUp, AlertTriangle, 
  ChevronRight, Filter, Download, Settings, ShieldCheck, 
  Database, Server, Layers, BrainCircuit
} from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import { cn } from '../lib/utils';
import { chartData, insightFeed, allMockTokens } from '../lib/data';

export const Badge = ({ children, variant = 'safe' }: { children: React.ReactNode, variant?: 'safe' | 'warning' | 'danger' }) => {
  const styles = {
    safe: 'bg-green/10 text-green border-green/20',
    warning: 'bg-yellow/10 text-yellow border-yellow/20',
    danger: 'bg-red/10 text-red border-red/20',
  };
  return (
    <span className={cn("px-2.5 py-1 text-[10px] uppercase font-bold tracking-wider border rounded-full flex items-center gap-1.5 w-fit", styles[variant])}>
      {variant === 'danger' && <AlertTriangle size={10} />}
      {children}
    </span>
  );
};

export const MetricCard = ({ title, value, change, icon: Icon, delay }: any) => (
  <motion.div 
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay, duration: 0.5, ease: "easeOut" }}
    className="glass-card p-5 rounded-2xl relative overflow-hidden group hover:-translate-y-1 transition-all duration-300"
  >
    <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-primary to-cyan opacity-0 group-hover:opacity-100 transition-opacity" />
    <div className="flex justify-between items-start mb-4">
      <span className="text-sm text-text-secondary uppercase tracking-[0.08em] font-semibold">{title}</span>
      <div className="p-2 rounded-lg bg-primary/10 text-primary">
        <Icon size={18} />
      </div>
    </div>
    <div className="text-[34px] font-[750] leading-none mb-2">{value}</div>
    <div className="text-sm text-green flex items-center gap-1 font-medium">
      <TrendingUp size={14} />
      {change}
    </div>
  </motion.div>
);

// --- 1. DASHBOARD VIEW (Original) ---
export const DashboardView = ({ onSelectToken }: { onSelectToken?: (token: any) => void }) => {
  return (
    <div className="space-y-8">
      {/* HERO INTELLIGENCE PANEL */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card rounded-3xl p-8 relative overflow-hidden border border-primary/20 shadow-[0_0_40px_rgba(124,92,255,0.08)]"
      >
        <div className="absolute top-0 right-0 w-1/2 h-full bg-gradient-to-l from-primary/10 to-transparent pointer-events-none" />
        <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-primary/50 to-transparent" />
        
        <div className="flex justify-between items-center relative z-10">
          <div>
            <h1 className="text-[40px] font-[700] leading-[1.1] mb-2 tracking-tight">AI Risk Intelligence</h1>
            <p className="text-text-secondary text-base max-w-lg mb-6">Scanning blockchain activity across multiple chains in realtime. Neural networks analyzing 24/7.</p>
            
            <div className="flex gap-4">
              <button className="h-11 px-6 rounded-lg bg-primary text-white font-medium hover:bg-primary/90 flex items-center gap-2 transition-all shadow-[0_0_20px_rgba(124,92,255,0.3)]">
                <Cpu size={18} /> Run Deep Scan
              </button>
            </div>
          </div>
          <div className="hidden lg:flex gap-8 items-center bg-black/20 p-4 rounded-2xl border border-white/5 backdrop-blur-md">
            <div className="flex items-center gap-4">
              {/* Neural Node Animation */}
              <div className="relative w-12 h-12 flex items-center justify-center">
                <div className="absolute inset-0 border border-primary/30 rounded-full radar-spin" />
                <div className="absolute inset-2 border border-cyan/30 rounded-full radar-spin" style={{ animationDirection: 'reverse', animationDuration: '3s' }} />
                <div className="w-4 h-4 bg-primary rounded-full shadow-[0_0_15px_#7c5cff] animate-pulse" />
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] text-primary uppercase font-bold tracking-[0.2em] mb-1">Neural Engine</span>
                <span className="text-xs font-mono text-white/70">SYNCING_DATA...</span>
              </div>
            </div>

            <div className="w-[1px] h-10 bg-white/10" />

            <div className="flex flex-col gap-1 items-start">
              <span className="text-[10px] text-text-muted uppercase font-bold tracking-widest">AI Confidence</span>
              <span className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-green to-emerald-400">98.4%</span>
            </div>

            <div className="w-[1px] h-10 bg-white/10" />

            <div className="flex flex-col gap-1 items-start">
              <span className="text-[10px] text-text-muted uppercase font-bold tracking-widest">Scanner Status</span>
              <div className="flex items-center gap-2 mt-1">
                <div className="w-2 h-2 rounded-full bg-cyan animate-pulse shadow-[0_0_8px_#22d3ee]" />
                <span className="text-sm font-semibold text-cyan tracking-wide">ACTIVE</span>
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* KPI CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard title="Tokens Scanned (24H)" value="1,284" change="+12.5%" icon={Activity} delay={0.1} />
        <MetricCard title="High Potential Found" value="42" change="+5 this hour" icon={TrendingUp} delay={0.2} />
        <MetricCard title="Scams Prevented" value="381" change="Saved ~$1.2M" icon={ShieldAlert} delay={0.3} />
        <MetricCard title="Active Collectors" value="25/25" change="100% Uptime" icon={Cpu} delay={0.4} />
      </div>

      {/* MIDDLE SECTION: CHART + FEED */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }} className="lg:col-span-2 glass-card rounded-2xl p-6">
          <h3 className="text-lg font-[650] mb-6 flex items-center justify-between">
            Market Risk Overview
            <Badge variant="safe">Realtime</Badge>
          </h3>
          <div className="h-[280px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorSafe" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="var(--green)" stopOpacity={0.3}/><stop offset="95%" stopColor="var(--green)" stopOpacity={0}/></linearGradient>
                  <linearGradient id="colorDanger" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="var(--red)" stopOpacity={0.3}/><stop offset="95%" stopColor="var(--red)" stopOpacity={0}/></linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="time" stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ backgroundColor: 'var(--bg-panel)', borderColor: 'var(--border)', borderRadius: '12px', backdropFilter: 'blur(10px)' }} itemStyle={{ fontSize: '14px' }} />
                <Area type="monotone" dataKey="safe" stroke="var(--green)" strokeWidth={2} fillOpacity={1} fill="url(#colorSafe)" />
                <Area type="monotone" dataKey="danger" stroke="var(--red)" strokeWidth={2} fillOpacity={1} fill="url(#colorDanger)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* PRO FEATURE: LIVE WHALE RADAR */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }} className="glass-card rounded-2xl p-6 flex flex-col relative overflow-hidden">
          <div className="flex justify-between items-center mb-6 z-10">
            <h3 className="text-lg font-[650] flex items-center gap-2">
              <Activity size={18} className="text-primary"/> Whale Radar
            </h3>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold tracking-widest text-primary uppercase">Live Scan</span>
              <div className="w-2 h-2 rounded-full bg-primary animate-ping" />
            </div>
          </div>

          {/* Radar Animation Background */}
          <div className="absolute top-[40%] left-1/2 -translate-x-1/2 -translate-y-1/2 w-[280px] h-[280px] border border-primary/20 rounded-full flex items-center justify-center opacity-30 pointer-events-none">
            <div className="absolute w-[180px] h-[180px] border border-primary/20 rounded-full" />
            <div className="absolute w-[80px] h-[80px] border border-primary/20 rounded-full" />
            <div className="absolute w-1/2 h-[2px] bg-gradient-to-r from-transparent to-primary origin-left radar-spin" />
            <div className="absolute w-1.5 h-1.5 rounded-full bg-primary shadow-[0_0_10px_#7c5cff] top-[30%] left-[60%]" />
            <div className="absolute w-1 h-1 rounded-full bg-cyan shadow-[0_0_8px_#22d3ee] bottom-[40%] left-[20%]" />
          </div>

          <div className="flex-1 space-y-4 z-10 relative">
            <AnimatePresence>
              {insightFeed.map((item, idx) => (
                <motion.div key={item.id} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.7 + (idx * 0.1) }} className="flex gap-4 items-start group cursor-pointer">
                  <div className={cn("mt-1 p-2 rounded-lg border flex-shrink-0", item.type === 'danger' ? "bg-red/10 text-red border-red/20" : item.type === 'warning' ? "bg-yellow/10 text-yellow border-yellow/20" : "bg-green/10 text-green border-green/20")}>
                    <item.icon size={14} />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-white group-hover:text-primary transition-colors leading-tight mb-1">{item.message}</p>
                    <span className="text-[11px] text-text-muted">{item.time}</span>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </motion.div>
      </div>

      <TokenTable onSelectToken={onSelectToken} />
    </div>
  );
};

export const TokenTable = ({ onSelectToken }: { onSelectToken?: (token: any) => void }) => {
  const [timeFilter, setTimeFilter] = useState('All');
  const [tokens, setTokens] = useState<any[]>(allMockTokens);
  const [isListening] = useState(true);
  const [hoveredToken, setHoveredToken] = useState<any | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  // Connect to Realtime WebSocket
  React.useEffect(() => {
    if (!isListening) return;

    // We connect to the local FastAPI server
    // Note: in production, this should point to the correct env WS_URL
    const ws = new WebSocket('ws://localhost:8000/api/ws/stream');

    ws.onopen = () => {
      console.log('Connected to CryptoScan Realtime Feed');
    };

    ws.onmessage = (event) => {
      try {
        const newToken = JSON.parse(event.data);
        setTokens(prev => {
          // Remove the 'isNew' flag from older tokens after a few seconds
          const updated = prev.map(t => ({ ...t, isNew: false }));
          // Ensure no duplicate IDs
          if (prev.some(t => t.id === newToken.id)) return prev;
          
          return [newToken, ...updated].slice(0, 50); // Keep max 50 in view
        });
      } catch (err) {
        console.error('Failed to parse WS message', err);
      }
    };

    ws.onclose = () => {
      console.log('Disconnected from Realtime Feed');
    };

    return () => {
      ws.close();
    };
  }, [isListening]);
  
  const timeFilterOptions = [
    { label: '1m', maxMinutes: 1 },
    { label: '1h', maxMinutes: 60 },
    { label: '6h', maxMinutes: 360 },
    { label: '24h', maxMinutes: 1440 },
    { label: '1mo', maxMinutes: 43200 },
    { label: '1y', maxMinutes: 525600 },
    { label: 'All', maxMinutes: Infinity },
  ];

  const filteredTokens = tokens.filter(t => {
    const option = timeFilterOptions.find(o => o.label === timeFilter);
    return option ? t.ageMinutes <= option.maxMinutes : true;
  });

  return (
      <div className="relative">
      <div className="glass-card rounded-2xl overflow-hidden mt-6 shadow-[0_0_20px_rgba(0,0,0,0.2)]">
        <div className="p-4 border-b border-white/5 flex flex-wrap gap-2 items-center bg-black/20">
          <span className="text-xs text-text-muted px-2 uppercase font-bold tracking-wider">Coin Age:</span>
          {timeFilterOptions.map(opt => (
            <button key={opt.label} onClick={() => setTimeFilter(opt.label)} className={cn("px-3 py-1.5 text-xs font-semibold rounded-md transition-all duration-200", timeFilter === opt.label ? "bg-primary text-white shadow-[0_0_10px_rgba(124,92,255,0.4)]" : "text-text-secondary hover:text-white hover:bg-white/10")}>
              {opt.label}
            </button>
          ))}
          <div className="ml-auto flex items-center gap-2 px-3 py-1 bg-green/10 text-green rounded-full border border-green/20">
            <div className="w-2 h-2 bg-green rounded-full animate-ping" />
            <span className="text-xs font-bold uppercase tracking-wider">Web3 Live</span>
          </div>
        </div>
        
        <div className="w-full overflow-x-auto h-[600px] overflow-y-auto">
          <table className="w-full text-left border-collapse relative">
            <thead className="sticky top-0 bg-[#0f121c] z-10 shadow-[0_4px_20px_rgba(0,0,0,0.5)]">
              <tr className="border-b border-white/5 text-text-muted text-xs uppercase tracking-wider font-semibold">
                <th className="p-4 pl-6 font-medium whitespace-nowrap">Token</th>
                <th className="p-4 font-medium whitespace-nowrap">Discovered</th>
                <th className="p-4 font-medium whitespace-nowrap">Age</th>
                <th className="p-4 font-medium whitespace-nowrap">Chain</th>
                <th className="p-4 font-medium whitespace-nowrap">Price</th>
                <th className="p-4 font-medium whitespace-nowrap">Volume / Liq</th>
                <th className="p-4 font-medium whitespace-nowrap">Risk Status</th>
                <th className="p-4 font-medium whitespace-nowrap">AI Score</th>
                <th className="p-4 pr-6 text-right font-medium whitespace-nowrap">Action</th>
              </tr>
            </thead>
            <tbody>
              <AnimatePresence>
                {filteredTokens.length === 0 ? (
                  <tr><td colSpan={9} className="p-8 text-center text-text-muted">No tokens discovered within this timeframe.</td></tr>
                ) : (
                  filteredTokens.map((token) => (
                    <motion.tr 
                      onClick={() => onSelectToken && onSelectToken(token)} 
                      onMouseEnter={() => setHoveredToken(token)}
                      onMouseMove={(e: any) => setMousePos({ x: e.clientX, y: e.clientY })}
                      onMouseLeave={() => setHoveredToken(null)}
                      initial={token.isNew ? { opacity: 0, x: -20, backgroundColor: 'rgba(124, 92, 255, 0.2)' } : { opacity: 0 }} 
                      animate={{ opacity: 1, x: 0, backgroundColor: 'rgba(0,0,0,0)' }} 
                      exit={{ opacity: 0 }} 
                      transition={{ duration: 0.5 }}
                      key={token.id} 
                      className={cn("border-b border-white/5 hover:bg-white/[0.03] transition-colors group cursor-pointer", token.isNew && "relative")}
                    >
                      {token.isNew && <div className="absolute inset-0 bg-gradient-to-r from-primary/10 to-transparent pointer-events-none animate-pulse" />}
                      <td className="p-4 pl-6 relative z-10">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-[#1c2130] flex items-center justify-center font-bold text-xs border border-white/10">{token.symbol.substring(0, 2)}</div>
                          <div>
                            <div className="font-semibold text-sm group-hover:text-primary transition-colors flex items-center gap-2">
                              {token.name}
                              {token.isNew && <span className="text-[9px] bg-primary text-white px-1.5 py-0.5 rounded font-bold uppercase tracking-wider animate-pulse">New</span>}
                            </div>
                            <div className="text-xs text-text-muted">{token.symbol}</div>
                          </div>
                        </div>
                      </td>
                      <td className="p-4 text-sm text-text-secondary whitespace-nowrap">{token.timeLabel}</td>
                      <td className="p-4 text-sm text-text-secondary whitespace-nowrap text-cyan">{token.ageLabel}</td>
                      <td className="p-4 text-sm text-text-secondary">{token.chain}</td>
                      <td className="p-4 text-sm font-medium">{token.price}</td>
                      <td className="p-4"><div className="text-sm font-medium">{token.volume}</div><div className="text-xs text-text-muted mt-0.5">{token.liquidity}</div></td>
                      <td className="p-4">
                        <div className="flex flex-col gap-1.5 items-start">
                          <Badge variant={token.risk.toLowerCase() as any}>{token.risk}</Badge>
                          {token.flags?.map((flag: string) => (
                            <span key={flag} className={cn(
                              "text-[9px] px-2 py-0.5 rounded font-bold uppercase tracking-wider border",
                              flag === 'HONEYPOT' || flag === 'BLACKLIST' 
                                ? "text-red border-red bg-red/20 animate-alert-flash" 
                                : "text-yellow border-yellow/30 bg-yellow/20"
                            )}>
                              {flag}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="p-4">
                        <div className="flex items-center gap-3">
                          <span className={cn("text-sm font-bold w-6", token.score >= 80 ? 'text-green' : token.score >= 40 ? 'text-yellow' : 'text-red')}>{token.score}</span>
                          <div className="flex-1 h-1.5 bg-black/40 rounded-full overflow-hidden w-24">
                            <div className={cn("h-full rounded-full transition-all duration-1000", token.score >= 80 ? 'bg-green' : token.score >= 40 ? 'bg-yellow' : 'bg-red')} style={{ width: `${token.score}%` }} />
                          </div>
                        </div>
                      </td>
                      <td className="p-4 pr-6 text-right">
                        <button className="w-8 h-8 rounded-lg inline-flex items-center justify-center bg-white/5 hover:bg-primary hover:text-white transition-colors text-text-muted border border-white/10"><ChevronRight size={16} /></button>
                      </td>
                    </motion.tr>
                  ))
                )}
              </AnimatePresence>
            </tbody>
          </table>
        </div>
      </div>
      
      {/* Global Floating Tooltip */}
      <AnimatePresence>
        {hoveredToken && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="fixed z-[100] w-64 glass-panel rounded-xl p-3 shadow-[0_10px_40px_rgba(0,0,0,0.7)] border border-primary/30 pointer-events-none"
            style={{ left: mousePos.x + 20, top: mousePos.y + 20 }}
          >
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs font-bold text-text-muted uppercase tracking-wider">AI Quick Scan</span>
              <Badge variant={hoveredToken.risk.toLowerCase() as any}>{hoveredToken.risk}</Badge>
            </div>
            <p className="text-xs text-white leading-relaxed mb-2">
              {hoveredToken.risk === 'DANGER' ? 'High risk of rugpull. Suspicious contract code detected.' : hoveredToken.risk === 'WARNING' ? 'Owner can mint tokens. Proceed with caution.' : 'Contract looks safe. Liquidity is locked.'}
            </p>
            <div className="flex gap-2 text-[10px] text-text-muted uppercase font-bold tracking-wider">
              <span>Liq: {hoveredToken.liquidity}</span>
              <span>•</span>
              <span>Vol: {hoveredToken.volume}</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      </div>
  );
};


// --- 2. TOKEN SCANNER VIEW ---
export const ScannerView = ({ onSelectToken }: { onSelectToken: (token: any) => void }) => {
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-[700]">Token Scanner</h1>
          <p className="text-text-muted">Advanced filtering and real-time detection</p>
        </div>
        <div className="flex gap-2">
          <button className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 flex items-center gap-2 text-sm font-medium hover:bg-white/10 transition">
            <Filter size={16} /> Filters
          </button>
          <button className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 flex items-center gap-2 text-sm font-medium hover:bg-white/10 transition">
            <Download size={16} /> Export
          </button>
        </div>
      </div>

      <TokenTable onSelectToken={onSelectToken} />
    </motion.div>
  );
};


// --- 3. THREATS (ALERT HISTORY) VIEW ---
export const ThreatsView = () => {
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <h1 className="text-3xl font-[700]">Threat Signals & Alerts</h1>
      <div className="glass-card rounded-2xl p-6">
        <div className="flex flex-col gap-4">
          {[1, 2, 3, 4, 5].map((_, i) => (
            <div key={i} className="flex gap-4 p-4 rounded-xl border border-red/20 bg-red/5 hover:bg-red/10 transition-colors cursor-pointer">
              <div className="p-3 rounded-full bg-red/10 text-red h-fit">
                <ShieldAlert size={24} />
              </div>
              <div className="flex-1">
                <div className="flex justify-between mb-1">
                  <h4 className="text-lg font-bold text-red">Critical Risk Detected: Liquidity Drain</h4>
                  <span className="text-sm text-text-muted">{i * 2 + 1}h ago</span>
                </div>
                <p className="text-text-secondary text-sm">Automated system detected a massive removal of liquidity (98%) on contract 0xabc...123 within 1 block.</p>
                <div className="mt-3 flex gap-2">
                  <span className="px-2 py-1 text-xs rounded bg-white/5 text-text-secondary border border-white/10">ETH Chain</span>
                  <span className="px-2 py-1 text-xs rounded bg-white/5 text-text-secondary border border-white/10">Scam Type: Rugpull</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
};


// --- 4. ADMIN PANEL VIEW ---
export const AdminView = () => {
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <h1 className="text-3xl font-[700]">System Administration</h1>
      <p className="text-text-muted">Configure scanning engines, scoring weights, and alert thresholds.</p>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        {/* Scoring Engine Config */}
        <div className="glass-card rounded-2xl p-6">
          <h3 className="text-xl font-[650] mb-4 flex items-center gap-2"><Settings className="text-primary"/> Scoring Engine Weights</h3>
          <div className="space-y-4">
            {['Discovery Scorer', 'Market Scorer', 'Social Scorer', 'Security Scorer', 'AI Scorer'].map((scorer) => (
              <div key={scorer} className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-text-secondary">{scorer}</span>
                  <span className="text-white">20%</span>
                </div>
                <div className="h-2 bg-black/40 rounded-full overflow-hidden">
                  <div className="h-full bg-primary rounded-full" style={{ width: '20%' }} />
                </div>
              </div>
            ))}
          </div>
          <button className="mt-6 w-full py-2.5 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors font-medium">Update Weights</button>
        </div>

        {/* System Services Status */}
        <div className="glass-card rounded-2xl p-6">
          <h3 className="text-xl font-[650] mb-4 flex items-center gap-2"><Server className="text-cyan"/> Active Services</h3>
          <div className="space-y-3">
            {[
              { name: 'FastAPI Backend', status: 'Running', icon: Database, color: 'text-green' },
              { name: 'PostgreSQL/Timescale', status: 'Running', icon: Database, color: 'text-green' },
              { name: 'Redis Broker', status: 'Running', icon: Layers, color: 'text-green' },
              { name: 'Celery Workers', status: '25/25 Active', icon: Cpu, color: 'text-cyan' },
              { name: 'Telegram Bot', status: 'Online', icon: ShieldCheck, color: 'text-green' },
            ].map((svc) => (
              <div key={svc.name} className="flex justify-between items-center p-3 rounded-lg border border-white/5 bg-black/20">
                <div className="flex items-center gap-3">
                  <svc.icon size={16} className={svc.color} />
                  <span className="font-medium">{svc.name}</span>
                </div>
                <Badge variant={svc.status.includes('Running') || svc.status.includes('Active') || svc.status.includes('Online') ? 'safe' : 'warning'}>{svc.status}</Badge>
              </div>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
};


// --- 5. TOKEN DETAIL VIEW ---
export const TokenDetailView = ({ token, onBack }: { token: any, onBack: () => void }) => {
  if (!token) return null;

  return (
    <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-6">
      <button onClick={onBack} className="text-text-secondary hover:text-white flex items-center gap-2 mb-4 transition-colors">
        <ChevronRight size={16} className="rotate-180" /> Back to Scanner
      </button>

      <div className="glass-card rounded-2xl p-8 border border-primary/20 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-1/3 h-full bg-gradient-to-l from-primary/5 to-transparent pointer-events-none" />
        
        <div className="flex justify-between items-start relative z-10">
          <div className="flex items-center gap-6">
            <div className="w-20 h-20 rounded-2xl bg-[#1c2130] flex items-center justify-center font-bold text-2xl border border-white/10 shadow-[0_0_30px_rgba(124,92,255,0.15)]">
              {token.symbol.substring(0, 2)}
            </div>
            <div>
              <h1 className="text-4xl font-[700] mb-2 flex items-center gap-3">
                {token.name} <span className="text-xl text-text-muted font-medium">{token.symbol}</span>
                <Badge variant={token.risk.toLowerCase() as any}>{token.risk}</Badge>
              </h1>
              <div className="flex gap-4 text-text-secondary mt-2">
                <span className="flex items-center gap-1"><Database size={14}/> {token.chain}</span>
                <span className="flex items-center gap-1"><TrendingUp size={14}/> {token.price}</span>
                <span className="flex items-center gap-1 text-text-muted bg-white/5 px-2 rounded">Scanned: {token.timeLabel}</span>
                <span className="flex items-center gap-1 text-cyan bg-cyan/10 px-2 rounded">Age: {token.ageLabel}</span>
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm text-text-muted uppercase font-bold tracking-widest mb-1">AI Trust Score</div>
            <div className={cn("text-5xl font-[750]", token.score >= 80 ? 'text-green' : token.score >= 40 ? 'text-yellow' : 'text-red')}>
              {token.score}<span className="text-2xl text-text-muted">/100</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 glass-card rounded-2xl p-6 h-[400px]">
          <h3 className="text-lg font-[650] mb-6">AI Score History (Last 24h)</h3>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 0, left: -20, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis dataKey="time" stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} domain={[0, 100]} />
              <Tooltip contentStyle={{ backgroundColor: 'var(--bg-panel)', borderColor: 'var(--border)', borderRadius: '12px' }} />
              <Line type="monotone" dataKey="safe" stroke="var(--primary)" strokeWidth={3} dot={{ r: 4, fill: 'var(--primary)' }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="glass-card rounded-2xl p-6">
          <h3 className="text-lg font-[650] mb-4 flex items-center gap-2"><BrainCircuit className="text-primary"/> AI Security Report</h3>
          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-white/5 border border-white/10">
              <div className="text-sm font-bold mb-1 flex items-center justify-between">Smart Contract <Badge variant="safe">Secure</Badge></div>
              <p className="text-xs text-text-secondary">Source code verified. No mint function. Ownership renounced.</p>
            </div>
            <div className="p-4 rounded-xl bg-white/5 border border-white/10">
              <div className="text-sm font-bold mb-1 flex items-center justify-between">Liquidity <Badge variant="warning">Medium Risk</Badge></div>
              <p className="text-xs text-text-secondary">Liquidity is locked for 6 months. Top 10 holders own 45% of supply.</p>
            </div>
            <div className="p-4 rounded-xl bg-white/5 border border-white/10">
              <div className="text-sm font-bold mb-1 flex items-center justify-between">Social Sentiment <Badge variant="safe">Bullish</Badge></div>
              <p className="text-xs text-text-secondary">High Twitter activity. 12 notable CT accounts accumulated recently.</p>
            </div>
            <button className="w-full py-3 mt-4 rounded-lg bg-primary/20 text-primary font-bold hover:bg-primary/30 transition-colors">
              Download Full PDF Report
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
};
