
import { ShieldCheck } from 'lucide-react';

export const ProPaywallOverlay = () => {
  return (
    <div className="absolute inset-0 pro-blur-overlay z-20 flex flex-col items-center justify-center p-6 text-center">
      <div className="w-16 h-16 rounded-full bg-primary/20 flex items-center justify-center mb-4 relative shadow-[0_0_30px_rgba(124,92,255,0.3)]">
        <div className="absolute inset-0 pulse-ring" />
        <ShieldCheck size={32} className="text-primary relative z-10" />
      </div>
      <h4 className="text-xl font-bold mb-2 text-white">Unlock Whale Tracker</h4>
      <p className="text-[13px] text-text-secondary mb-6 leading-relaxed max-w-[240px]">
        Realtime tracking of the Top 100 Smart Money Wallets. See what they buy before the pump.
      </p>
      <button className="w-full h-11 rounded-xl bg-gradient-to-r from-primary to-cyan text-black text-sm font-bold uppercase tracking-wider hover:opacity-90 transition-all shadow-[0_0_20px_rgba(34,211,238,0.3)]">
        Upgrade to PRO
      </button>
    </div>
  );
};
