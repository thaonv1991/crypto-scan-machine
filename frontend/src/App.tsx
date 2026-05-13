import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Search, Bell, Settings, LayoutDashboard, ListFilter, BrainCircuit, 
  Wallet, Droplets, FileCode2, ShieldAlert, Zap
} from 'lucide-react';
import { cn } from './lib/utils';
import { DashboardView, ScannerView, ThreatsView, AdminView, TokenDetailView } from './pages/Views';
import { AuthModal } from './components/AuthModal';
import './index.css';

// --- MAIN APP ---

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedToken, setSelectedToken] = useState<any>(null);
  const [isAuthOpen, setIsAuthOpen] = useState(false);

  // --- ADMIN FULL SCREEN LAYOUT ---
  if (activeTab === 'admin') {
    return (
      <div className="flex h-screen w-full bg-black text-[#a1a1aa] font-mono overflow-hidden">
        {/* Terminal Style Sidebar */}
        <div className="w-[200px] border-r border-[#27272a] bg-[#09090b] flex flex-col">
          <div className="p-4 border-b border-[#27272a]">
            <span className="text-white font-bold tracking-widest text-xs">SYS_ADMIN</span>
          </div>
          <div className="p-4 space-y-2 flex-1">
            <button className="text-xs w-full text-left text-white bg-[#27272a] px-3 py-2 rounded">OVERVIEW</button>
            <button className="text-xs w-full text-left hover:text-white px-3 py-2 rounded">API_KEYS</button>
            <button className="text-xs w-full text-left hover:text-white px-3 py-2 rounded">USER_TIERS</button>
            <button className="text-xs w-full text-left text-red hover:bg-red/10 px-3 py-2 rounded mt-8">PANIC_STOP</button>
          </div>
          <div className="p-4 border-t border-[#27272a]">
            <button 
              onClick={() => setActiveTab('dashboard')}
              className="text-[10px] uppercase w-full text-center border border-[#27272a] hover:bg-[#27272a] py-2 transition-colors"
            >
              [ Return to App ]
            </button>
          </div>
        </div>
        {/* Main Content Area */}
        <div className="flex-1 overflow-auto bg-[#000000]">
          <div className="max-w-4xl mx-auto p-8">
            <h1 className="text-white text-xl mb-8 border-b border-[#27272a] pb-4">root@cryptoscan:~/admin_panel#</h1>
            <AdminView />
          </div>
        </div>
      </div>
    );
  }

  // --- MAIN APP LAYOUT ---
  return (
    <div className="flex h-screen overflow-hidden bg-main text-text-primary font-sans">
      
      {/* SIDEBAR */}
      <aside className="w-[260px] glass-panel border-r border-white/5 flex flex-col z-20 shrink-0">
        <div className="p-6 flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-cyan flex items-center justify-center shadow-[0_0_15px_rgba(124,92,255,0.4)]">
            <Zap size={18} className="text-white" />
          </div>
          <span className="font-bold text-lg tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-white to-text-secondary">
            CryptoScan AI
          </span>
        </div>

        <nav className="flex-1 px-4 space-y-1 overflow-y-auto">
          {[
            { id: 'dashboard', label: 'Command Center', icon: LayoutDashboard },
            { id: 'scanner', label: 'Token Scanner', icon: ListFilter },
            { id: 'ai', label: 'AI Reports', icon: BrainCircuit },
            { id: 'threats', label: 'Threat Signals', icon: ShieldAlert },
            { id: 'wallets', label: 'Wallet Monitor', icon: Wallet },
            { id: 'liquidity', label: 'Liquidity Watch', icon: Droplets },
            { id: 'contracts', label: 'Contract Analyzer', icon: FileCode2 },
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={cn(
                "w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200",
                activeTab === item.id 
                  ? "bg-primary/10 text-primary border border-primary/20 shadow-[inset_0_0_20px_rgba(124,92,255,0.05)]" 
                  : "text-text-secondary hover:text-white hover:bg-white/5 border border-transparent"
              )}
            >
              <item.icon size={18} className={activeTab === item.id ? "text-primary" : "text-text-muted"} />
              {item.label}
            </button>
          ))}
        </nav>

        <div className="p-4 mt-auto">
          <button onClick={() => setActiveTab('admin')} className="w-full mb-4 flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-text-secondary hover:text-white hover:bg-white/5 border border-transparent transition-all duration-200">
            <Settings size={18} className="text-text-muted" />
            Admin Panel
          </button>
          <div className="p-4 rounded-xl bg-[#0a0d14]/80 border border-white/5 text-xs font-mono text-text-muted space-y-2">
            <div className="flex justify-between">
              <span>Network:</span>
              <span className="text-green flex items-center gap-1.5"><div className="w-1.5 h-1.5 rounded-full bg-green animate-pulse" /> Online</span>
            </div>
            <div className="flex justify-between">
              <span>Collectors:</span>
              <span className="text-white">25/25</span>
            </div>
            <div className="flex justify-between">
              <span>Mode:</span>
              <span className="text-cyan">AI Sentinel</span>
            </div>
          </div>
        </div>
      </aside>

      {/* MAIN CONTENT */}
      <main className="flex-1 flex flex-col relative overflow-hidden z-10">
        
        {/* TOPBAR */}
        <header className="h-[72px] glass-panel border-b border-white/5 flex items-center justify-between px-8 z-20">
          <div className="relative group">
            <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-text-muted group-focus-within:text-primary transition-colors" />
            <input 
              type="text" 
              placeholder="Search token, wallet, contract..." 
              className="w-[320px] h-10 bg-white/[0.03] border border-white/10 rounded-full pl-11 pr-4 text-sm text-white placeholder:text-text-muted focus:outline-none focus:border-primary/50 focus:bg-white/[0.05] transition-all"
            />
            <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 opacity-50">
              <kbd className="px-1.5 py-0.5 rounded bg-black/40 border border-white/10 text-[10px] font-sans">⌘</kbd>
              <kbd className="px-1.5 py-0.5 rounded bg-black/40 border border-white/10 text-[10px] font-sans">K</kbd>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button className="w-10 h-10 rounded-full flex items-center justify-center text-text-secondary hover:text-white hover:bg-white/5 border border-transparent hover:border-white/10 transition-all">
              <Bell size={18} />
            </button>
            <button className="w-10 h-10 rounded-full flex items-center justify-center text-text-secondary hover:text-white hover:bg-white/5 border border-transparent hover:border-white/10 transition-all">
              <Settings size={18} />
            </button>
            <button 
              onClick={() => setIsAuthOpen(true)}
              className="px-4 h-9 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-sm font-medium hover:bg-white/10 transition-all"
            >
              Sign In
            </button>
          </div>
        </header>

        {/* Auth Modal */}
        <AuthModal isOpen={isAuthOpen} onClose={() => setIsAuthOpen(false)} />

        {/* SCROLLABLE AREA */}
        <div className="flex-1 overflow-y-auto p-8 pb-20">
          <div className="max-w-[1400px] mx-auto">
            <AnimatePresence mode="wait">
              {activeTab === 'dashboard' && <motion.div key="dashboard" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}}><DashboardView onSelectToken={(t: any) => { setSelectedToken(t); setActiveTab('token_detail'); }} /></motion.div>}
              {activeTab === 'scanner' && <motion.div key="scanner" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}}><ScannerView onSelectToken={(t) => { setSelectedToken(t); setActiveTab('token_detail'); }} /></motion.div>}
              {activeTab === 'token_detail' && <motion.div key="token_detail" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}}><TokenDetailView token={selectedToken} onBack={() => setActiveTab('scanner')} /></motion.div>}
              {activeTab === 'threats' && <motion.div key="threats" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}}><ThreatsView /></motion.div>}
              {(activeTab === 'ai' || activeTab === 'wallets' || activeTab === 'liquidity' || activeTab === 'contracts') && (
                <motion.div key="coming_soon" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="flex flex-col items-center justify-center h-[500px] text-center">
                  <BrainCircuit size={64} className="text-primary/50 mb-4" />
                  <h2 className="text-2xl font-bold mb-2">Module In Development</h2>
                  <p className="text-text-muted max-w-md">This advanced AI feature is scheduled for Phase 7.2 of the roadmap. Check back soon.</p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </main>
    </div>
  );
}
