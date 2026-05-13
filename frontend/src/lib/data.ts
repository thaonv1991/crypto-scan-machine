import { Activity, ShieldAlert, Droplets, FileCode2 } from 'lucide-react';

export const chartData = [
  { time: '00:00', safe: 120, warning: 40, danger: 10 },
  { time: '04:00', safe: 150, warning: 50, danger: 15 },
  { time: '08:00', safe: 180, warning: 45, danger: 25 },
  { time: '12:00', safe: 220, warning: 60, danger: 30 },
  { time: '16:00', safe: 280, warning: 75, danger: 20 },
  { time: '20:00', safe: 310, warning: 65, danger: 12 },
  { time: '24:00', safe: 380, warning: 80, danger: 18 },
];

export const insightFeed = [
  { id: 1, type: 'danger', message: 'Honeypot detected on PEPE2.0 contract', time: 'Just now', icon: ShieldAlert },
  { id: 2, type: 'warning', message: 'Massive liquidity removed from DEFI pool', time: '2m ago', icon: Droplets },
  { id: 3, type: 'safe', message: 'Whale accumulation on AERO (+12%)', time: '15m ago', icon: Activity },
  { id: 4, type: 'warning', message: 'Ownership renounced but mint active', time: '1h ago', icon: FileCode2 },
];

const generateMockTokens = () => {
  const tokens = [];
  const chains = ['ETH', 'BSC', 'Base', 'Solana', 'Arbitrum'];
  const names = ['AeroSwap', 'NeuralAI', 'ZkL2Chain', 'MemeDoge', 'MoonPump', 'SafeMoon2', 'DeFiX', 'LiquidBot', 'PepeMax', 'FlokiBurn'];
  
  const timeframes = [
    { label: '30s ago', minutes: 0.5 },
    { label: '1m ago', minutes: 1 },
    { label: '5m ago', minutes: 5 },
    { label: '12m ago', minutes: 12 },
    { label: '35m ago', minutes: 35 },
    { label: '1h ago', minutes: 60 },
    { label: '2h ago', minutes: 120 },
    { label: '4h ago', minutes: 240 },
    { label: '6h ago', minutes: 360 },
    { label: '10h ago', minutes: 600 },
    { label: '24h ago', minutes: 1440 },
    { label: '2d ago', minutes: 2880 },
    { label: '5d ago', minutes: 7200 },
    { label: '15d ago', minutes: 21600 },
    { label: '1mo ago', minutes: 43200 },
    { label: '3mo ago', minutes: 129600 },
    { label: '6mo ago', minutes: 259200 },
    { label: '1y ago', minutes: 525600 },
  ];

  for (let i = 0; i < 50; i++) {
    const score = Math.floor(Math.random() * 95) + 5;
    const risk = score >= 80 ? 'SAFE' : score >= 40 ? 'WARNING' : 'DANGER';
    const disc = timeframes[Math.floor(Math.random() * 8)]; // discovered recently (up to 4h)
    const ageTf = timeframes[Math.floor(Math.random() * timeframes.length)];
    const ageMins = Math.max(disc.minutes, ageTf.minutes);
    const ageLab = timeframes.find(t => t.minutes >= ageMins)?.label || ageTf.label;

    tokens.push({
      id: String(i + 1),
      name: names[i % names.length] + (i > 9 ? ` V${Math.floor(i/10)+1}` : ''),
      symbol: (names[i % names.length].substring(0, 4) + (i > 9 ? i : '')).toUpperCase(),
      chain: chains[i % chains.length],
      price: `$${(Math.random() * 10).toFixed(4)}`,
      volume: `$${(Math.random() * 5 + 0.1).toFixed(1)}M`,
      liquidity: `$${(Math.random() * 2 + 0.05).toFixed(1)}M`,
      score,
      risk,
      timeLabel: disc.label,
      discoveredMinutes: disc.minutes,
      ageLabel: ageLab,
      ageMinutes: ageMins
    });
  }
  return tokens.sort((a, b) => a.discoveredMinutes - b.discoveredMinutes);
};

export const allMockTokens = generateMockTokens();
