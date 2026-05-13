import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Mail, Lock, User, Wallet, Globe, Hash } from 'lucide-react';

export const AuthModal = ({ isOpen, onClose }: { isOpen: boolean, onClose: () => void }) => {
  const [mode, setMode] = useState<'login' | 'register'>('login');

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        {/* Backdrop */}
        <motion.div 
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          className="absolute inset-0 bg-black/60 backdrop-blur-sm"
          onClick={onClose}
        />
        
        {/* Modal */}
        <motion.div 
          initial={{ opacity: 0, scale: 0.95, y: 20 }} 
          animate={{ opacity: 1, scale: 1, y: 0 }} 
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative w-[400px] glass-panel rounded-2xl border border-white/10 p-8 shadow-[0_0_50px_rgba(124,92,255,0.15)]"
        >
          <button onClick={onClose} className="absolute top-4 right-4 text-text-muted hover:text-white transition-colors">
            <X size={20} />
          </button>

          <h2 className="text-2xl font-bold mb-2">
            {mode === 'login' ? 'Welcome Back' : 'Create Account'}
          </h2>
          <p className="text-sm text-text-secondary mb-6">
            {mode === 'login' ? 'Enter your credentials to access the scanner.' : 'Join the elite crypto intelligence network.'}
          </p>

          <form className="space-y-4" onSubmit={(e) => e.preventDefault()}>
            {mode === 'register' && (
              <div className="relative">
                <User size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                <input type="text" placeholder="Username" className="w-full bg-black/30 border border-white/10 rounded-xl h-11 pl-10 pr-4 text-sm focus:outline-none focus:border-primary/50 transition-colors" />
              </div>
            )}
            
            <div className="relative">
              <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
              <input type="email" placeholder="Email address" className="w-full bg-black/30 border border-white/10 rounded-xl h-11 pl-10 pr-4 text-sm focus:outline-none focus:border-primary/50 transition-colors" />
            </div>

            <div className="relative">
              <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
              <input type="password" placeholder="Password" className="w-full bg-black/30 border border-white/10 rounded-xl h-11 pl-10 pr-4 text-sm focus:outline-none focus:border-primary/50 transition-colors" />
            </div>

            <button className="w-full h-11 mt-2 rounded-xl bg-gradient-to-r from-primary to-cyan text-black font-bold shadow-[0_0_20px_rgba(124,92,255,0.3)] hover:opacity-90 transition-opacity">
              {mode === 'login' ? 'Sign In' : 'Register'}
            </button>

            <div className="relative flex items-center py-4">
              <div className="flex-grow border-t border-white/10"></div>
              <span className="flex-shrink-0 mx-4 text-text-muted text-[10px] uppercase font-bold tracking-widest">OR CONTINUE WITH</span>
              <div className="flex-grow border-t border-white/10"></div>
            </div>

            <div className="grid grid-cols-2 gap-3 mb-3">
              <button type="button" className="w-full h-10 rounded-xl bg-white/5 border border-white/10 text-text-secondary text-sm font-medium flex items-center justify-center gap-2 hover:bg-white/10 hover:text-white transition-colors">
                <Globe size={16} /> Google
              </button>
              <button type="button" className="w-full h-10 rounded-xl bg-[#1DA1F2]/10 border border-[#1DA1F2]/30 text-[#1DA1F2] text-sm font-medium flex items-center justify-center gap-2 hover:bg-[#1DA1F2]/20 transition-colors">
                <Hash size={16} /> Twitter (X)
              </button>
            </div>

            <button type="button" className="w-full h-11 rounded-xl bg-[#f6851b]/10 border border-[#f6851b]/30 text-[#f6851b] font-medium flex items-center justify-center gap-2 hover:bg-[#f6851b]/20 transition-colors shadow-[0_0_15px_rgba(246,133,27,0.15)]">
              <Wallet size={18} /> Connect Web3 Wallet
            </button>
          </form>

          <p className="text-center text-sm text-text-muted mt-6">
            {mode === 'login' ? "Don't have an account? " : "Already have an account? "}
            <button onClick={() => setMode(mode === 'login' ? 'register' : 'login')} className="text-primary hover:underline">
              {mode === 'login' ? 'Sign up' : 'Sign in'}
            </button>
          </p>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
