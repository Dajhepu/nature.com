import React, { useState, useEffect, useRef } from 'react';
import './SmartMoney.css';

const DEXSCREENER_BASE = 'https://api.dexscreener.com';
const SCAN_APIS = {
  eth:      { url: 'https://api.etherscan.io/api',      keyParam: 'apikey', label: 'Etherscan' },
  bsc:      { url: 'https://api.bscscan.com/api',       keyParam: 'apikey', label: 'BSCScan' },
  base:     { url: 'https://api.basescan.org/api',      keyParam: 'apikey', label: 'Basescan' },
  arbitrum: { url: 'https://api.arbiscan.io/api',       keyParam: 'apikey', label: 'Arbiscan' },
  polygon:  { url: 'https://api.polygonscan.com/api',   keyParam: 'apikey', label: 'Polygonscan' },
  avalanche:{ url: 'https://api.snowtrace.io/api',      keyParam: 'apikey', label: 'Snowtrace' },
};
const AVATAR_COLORS = ['#1e3a5f','#1a3a2a','#3a1a2a','#2a1a3a','#3a2a1a','#1a2a3a'];

const SmartMoney = ({ onClose }) => {
  // --- State ---
  const [wallets, setWallets] = useState([]);
  const [trades, setTrades] = useState([]);
  const [sentSignals, setSentSignals] = useState([]);
  const [currentFilter, setCurrentFilter] = useState('all');
  const [currentChain, setCurrentChain] = useState('all');
  const [activeTab, setActiveTab] = useState('signals');
  const [stats, setStats] = useState({ totalSignals: 0, buySignals: 0, sellSignals: 0, totalVol: 0 });
  const [cfg, setCfg] = useState({
    telegramToken: '',
    telegramChatId: '',
    etherscanKey: '',
    bscscanKey: '',
    updateInterval: 30,
    minUsd: 5000,
    autoSend: true,
  });
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newWallet, setNewWallet] = useState({ addr: '', label: '', chain: 'eth', winRate: '', notes: '' });
  const [status, setStatus] = useState({
    monitor: { type: '', text: 'Monitor: Idle' },
    dex: { type: 'ok', text: 'DexScreener: Tayyor' },
    tg: { type: '', text: 'Telegram: —' },
    scan: { type: '', text: 'Explorer API: —' },
    lastUpdate: '—'
  });

  const polledHashesRef = useRef({});
  const monitorIntervalRef = useRef(null);

  // --- Load Data ---
  useEffect(() => {
    try {
      const savedCfg = localStorage.getItem('chainedge_cfg');
      if (savedCfg) setCfg(prev => ({ ...prev, ...JSON.parse(savedCfg) }));

      const savedWallets = localStorage.getItem('chainedge_wallets');
      if (savedWallets) {
        const parsedWallets = JSON.parse(savedWallets);
        setWallets(parsedWallets);
        parsedWallets.forEach(w => {
           if (!polledHashesRef.current[w.addr]) polledHashesRef.current[w.addr] = new Set();
        });
      }

      const savedSignals = localStorage.getItem('chainedge_signals');
      if (savedSignals) setSentSignals(JSON.parse(savedSignals).slice(-100));

      const savedStats = localStorage.getItem('chainedge_stats');
      if (savedStats) setStats(prev => ({ ...prev, ...JSON.parse(savedStats) }));
    } catch(e) {
      console.error("Ma'lumotlarni yuklashda xatolik:", e);
    }
  }, []);

  // --- Save Data ---
  useEffect(() => {
    localStorage.setItem('chainedge_cfg', JSON.stringify(cfg));
  }, [cfg]);

  useEffect(() => {
    localStorage.setItem('chainedge_wallets', JSON.stringify(wallets));
  }, [wallets]);

  useEffect(() => {
    localStorage.setItem('chainedge_signals', JSON.stringify(sentSignals.slice(-100)));
    localStorage.setItem('chainedge_stats', JSON.stringify(stats));
  }, [sentSignals, stats]);

  // --- Helpers ---
  const formatNum = (n) => {
    if (!n || isNaN(n)) return '0';
    if (n >= 1e9) return (n/1e9).toFixed(2)+'B';
    if (n >= 1e6) return (n/1e6).toFixed(2)+'M';
    if (n >= 1e3) return (n/1e3).toFixed(1)+'K';
    if (n >= 1) return n.toFixed(2);
    return n.toPrecision(4);
  };

  const shortAddr = (addr) => {
    if (!addr) return '—';
    if (addr.length > 20) return addr.slice(0,6)+'...'+addr.slice(-4);
    return addr;
  };

  const walletInitials = (label) => {
    return label.split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase();
  };

  const sleep = (ms) => new Promise(r => setTimeout(r, ms));

  // --- Actions ---
  const addWallet = () => {
    if (!newWallet.addr) { alert('Iltimos, hamyon manzilini kiriting'); return; }
    const wallet = {
      id: Date.now(),
      addr: newWallet.addr.trim(),
      label: newWallet.label.trim() || `Hamyon #${wallets.length+1}`,
      chain: newWallet.chain,
      winRate: (newWallet.winRate || '?') + '%',
      pnl: '—',
      trades30d: 0,
      notes: newWallet.notes.trim(),
      active: true,
      lastTx: null
    };
    setWallets(prev => [...prev, wallet]);
    polledHashesRef.current[wallet.addr] = new Set();
    setIsModalOpen(false);
    setNewWallet({ addr: '', label: '', chain: 'eth', winRate: '', notes: '' });
  };

  const removeWallet = (id) => {
    if (!window.confirm('Ushbu hamyonni kuzatishdan olib tashlaysizmi?')) return;
    setWallets(prev => prev.filter(w => w.id !== id));
  };

  const toggleWallet = (id) => {
    setWallets(prev => prev.map(w => w.id === id ? { ...w, active: !w.active } : w));
  };

  const startMonitoring = () => {
    if (!wallets.length) { alert('Kuzatish uchun kamida bitta hamyon qo\'shing'); return; }
    setIsMonitoring(true);
    setStatus(prev => ({ ...prev, monitor: { type: 'ok', text: 'Monitor: Faol' } }));
  };

  const stopMonitoring = () => {
    setIsMonitoring(false);
    if (monitorIntervalRef.current) {
      clearInterval(monitorIntervalRef.current);
      monitorIntervalRef.current = null;
    }
    setStatus(prev => ({ ...prev, monitor: { type: '', text: 'Monitor: Kutmoqda' } }));
  };

  useEffect(() => {
    if (isMonitoring) {
      pollAll();
      const interval = (parseInt(cfg.updateInterval) || 30) * 1000;
      monitorIntervalRef.current = setInterval(pollAll, interval);
    } else {
      if (monitorIntervalRef.current) {
        clearInterval(monitorIntervalRef.current);
        monitorIntervalRef.current = null;
      }
    }
    return () => {
      if (monitorIntervalRef.current) clearInterval(monitorIntervalRef.current);
    };
  }, [isMonitoring, wallets, cfg.updateInterval]);

  const pollAll = async () => {
    const now = new Date();
    setStatus(prev => ({ ...prev, lastUpdate: 'Oxirgi scan: ' + now.toTimeString().slice(0,8) }));
    const active = wallets.filter(w => w.active);
    for (const wallet of active) {
      try {
        await pollWallet(wallet);
      } catch(e) {
        console.warn('Poll error for', wallet.label, e);
      }
      await sleep(400);
    }
  };

  const pollWallet = async (wallet) => {
    const chain = wallet.chain;
    if (chain === 'solana') {
      await pollSolanaWallet(wallet);
      return;
    }
    const scan = SCAN_APIS[chain];
    if (!scan) return;
    const apiKey = chain === 'bsc' ? cfg.bscscanKey : cfg.etherscanKey;
    let url = `${scan.url}?module=account&action=tokentx&address=${wallet.addr}&sort=desc&offset=20&page=1`;
    if (apiKey) url += `&${scan.keyParam}=${apiKey}`;

    setStatus(prev => ({ ...prev, scan: { type: 'ok', text: `Explorer: ${scan.label}` } }));

    const res = await fetch(url);
    const data = await res.json();
    if (data.status !== '1' || !Array.isArray(data.result)) return;

    const known = polledHashesRef.current[wallet.addr] || new Set();
    const newTxs = data.result.filter(tx => !known.has(tx.hash));

    if (known.size === 0) {
      data.result.forEach(tx => known.add(tx.hash));
      polledHashesRef.current[wallet.addr] = known;
      return;
    }

    const byHash = {};
    for (const tx of newTxs) {
      if (!byHash[tx.hash]) byHash[tx.hash] = [];
      byHash[tx.hash].push(tx);
      known.add(tx.hash);
    }

    for (const [hash, txGroup] of Object.entries(byHash)) {
      await processTxGroup(wallet, txGroup, chain, hash);
    }
    polledHashesRef.current[wallet.addr] = known;
  };

  const processTxGroup = async (wallet, txGroup, chain, hash) => {
    const minUsdThreshold = parseFloat(cfg.minUsd);
    const stables = new Set(['usdt','usdc','dai','busd','tusd','usdp','frax','lusd','gusd','susd','cusd','usd+']);
    const wrappers = new Set(['weth','wbnb','wmatic','wavax','wftm']);

    let tradedTx = txGroup.find(tx => {
      const sym = (tx.tokenSymbol||'').toLowerCase();
      return !stables.has(sym) && !wrappers.has(sym);
    }) || txGroup[0];

    const tokenSymbol = tradedTx.tokenSymbol || 'UNKNOWN';
    const tokenAddr = tradedTx.contractAddress;
    const decimals = parseInt(tradedTx.tokenDecimal) || 18;
    const rawAmt = parseFloat(tradedTx.value) / Math.pow(10, decimals);
    const isBuy = tradedTx.to.toLowerCase() === wallet.addr.toLowerCase();
    const tradeType = isBuy ? 'buy' : 'sell';

    let tokenData = null;
    try {
      const dexRes = await fetch(`${DEXSCREENER_BASE}/latest/dex/tokens/${tokenAddr}`);
      const dexJson = await dexRes.json();
      if (dexJson.pairs && dexJson.pairs.length > 0) {
        const chainMap = { eth:'ethereum', bsc:'bsc', base:'base', arbitrum:'arbitrum', polygon:'polygon', avalanche:'avalanche' };
        const dexChain = chainMap[chain] || chain;
        const pairs = dexJson.pairs.filter(p => p.chainId === dexChain);
        const pair = pairs.length ? pairs.sort((a,b)=>(b.liquidity?.usd||0)-(a.liquidity?.usd||0))[0] : dexJson.pairs[0];
        tokenData = {
          price: parseFloat(pair.priceUsd) || 0,
          priceStr: pair.priceUsd || '—',
          mcap: pair.fdv || pair.marketCap || 0,
          vol24h: pair.volume?.h24 || 0,
          priceChange24h: pair.priceChange?.h24 || 0,
          pairAddr: pair.pairAddress,
          dex: pair.dexId,
          liquidity: pair.liquidity?.usd || 0,
        };
      }
      setStatus(prev => ({ ...prev, dex: { type: 'ok', text: 'DexScreener: OK' } }));
    } catch(e) {
      setStatus(prev => ({ ...prev, dex: { type: 'warn', text: 'DexScreener: Xato' } }));
    }

    const usdValue = tokenData ? rawAmt * tokenData.price : 0;
    if (usdValue > 0 && usdValue < minUsdThreshold) return;

    const trade = {
      id: hash + '_' + Date.now(),
      hash,
      type: tradeType,
      wallet,
      chain,
      token: tokenSymbol,
      tokenAddr,
      amount: rawAmt,
      usdValue,
      tokenData,
      timestamp: new Date(parseInt(tradedTx.timeStamp) * 1000),
      signalSent: false,
    };

    setTrades(prev => [trade, ...prev]);
    setWallets(prev => prev.map(w => w.id === wallet.id ? { ...w, trades30d: (w.trades30d || 0) + 1 } : w));

    if (cfg.autoSend && cfg.telegramToken && cfg.telegramChatId) {
      const sent = await sendTelegramSignal(trade);
      if (sent) {
        trade.signalSent = true;
        setStats(prev => ({
          ...prev,
          totalSignals: prev.totalSignals + 1,
          buySignals: tradeType === 'buy' ? prev.buySignals + 1 : prev.buySignals,
          sellSignals: tradeType === 'sell' ? prev.sellSignals + 1 : prev.sellSignals,
          totalVol: prev.totalVol + usdValue
        }));
        addSignalLog(trade);
      }
    }
  };

  const pollSolanaWallet = async (wallet) => {
    try {
      const url = `https://api.mainnet-beta.solana.com`;
      const body = { jsonrpc:'2.0', id:1, method:'getSignaturesForAddress', params:[wallet.addr,{limit:20}] };
      const res = await fetch(url, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) });
      const data = await res.json();
      if (!data.result) return;

      const known = polledHashesRef.current[wallet.addr] || new Set();
      const newSigs = data.result.filter(s => !known.has(s.signature));

      if (known.size === 0) {
        data.result.forEach(s=>known.add(s.signature));
        polledHashesRef.current[wallet.addr] = known;
        return;
      }

      newSigs.forEach(s=>known.add(s.signature));
      polledHashesRef.current[wallet.addr] = known;

      if (newSigs.length > 0) {
        const trade = {
          id: newSigs[0].signature + Date.now(),
          hash: newSigs[0].signature,
          type: 'unknown',
          wallet,
          chain: 'solana',
          token: 'SOL TX',
          amount: 0,
          usdValue: 0,
          tokenData: null,
          timestamp: new Date(),
          signalSent: false,
          solNote: `${newSigs.length} ta yangi tranzaksiya`,
        };
        setTrades(prev => [trade, ...prev]);
      }
    } catch(e) {}
  };

  const formatSignalMessage = (trade) => {
    const emoji = trade.type === 'buy' ? '🟢' : trade.type === 'sell' ? '🔴' : '⚪';
    const actionWord = trade.type === 'buy' ? 'SOTIB OLISH' : trade.type === 'sell' ? 'SOTISH' : 'ALMASHNUV';
    const usdStr = trade.usdValue > 0 ? '$' + formatNum(trade.usdValue) : '?';
    const td = trade.tokenData;
    const chainUp = (trade.chain||'').toUpperCase();
    const dexLink = td && td.pairAddr ? `https://dexscreener.com/${trade.chain}/${td.pairAddr}` : '';
    const explLink = trade.chain === 'eth' ? `https://etherscan.io/tx/${trade.hash}`
      : trade.chain === 'bsc' ? `https://bscscan.com/tx/${trade.hash}`
      : trade.chain === 'base' ? `https://basescan.org/tx/${trade.hash}`
      : trade.chain === 'arbitrum' ? `https://arbiscan.io/tx/${trade.hash}` : '';

    let msg = `${emoji} <b>${actionWord} SIGNALI</b> — chainEDGE\n\n`;
    msg += `💎 <b>Aqlli Hamyon:</b> <code>${trade.wallet.addr.slice(0,6)}...${trade.wallet.addr.slice(-4)}</code> (${trade.wallet.label})\n`;
    msg += `📊 <b>Token:</b> <b>$${trade.token}</b>\n`;
    msg += `🔗 <b>Tarmoq:</b> ${chainUp}\n`;
    msg += `💰 <b>Qiymati:</b> <b>${usdStr}</b>\n`;
    if (td) {
      msg += `📈 <b>Narxi:</b> $${td.priceStr}\n`;
      if (td.mcap > 0) msg += `💹 <b>Market Cap:</b> $${formatNum(td.mcap)}\n`;
      if (td.vol24h > 0) msg += `📊 <b>24s Hajm:</b> $${formatNum(td.vol24h)}\n`;
      if (td.liquidity > 0) msg += `🏊 <b>Likvidlik:</b> $${formatNum(td.liquidity)}\n`;
      if (td.priceChange24h) msg += `📉 <b>24s O'zgarish:</b> ${td.priceChange24h > 0 ? '+' : ''}${td.priceChange24h.toFixed(1)}%\n`;
      if (td.dex) msg += `🏦 <b>DEX:</b> ${td.dex}\n`;
    }
    msg += `\n🏦 <b>Hamyon Statistikasi:</b>\n`;
    msg += `• Win Rate: ${trade.wallet.winRate}\n`;
    msg += `• PnL: ${trade.wallet.pnl}\n`;
    msg += `• Tranzaksiyalar (30 kun): ${trade.wallet.trades30d}\n`;
    if (trade.wallet.notes) msg += `• Eslatma: ${trade.wallet.notes}\n`;
    msg += `\n`;
    if (dexLink) msg += `🔍 <a href="${dexLink}">DexScreener</a>`;
    if (explLink) msg += ` | <a href="${explLink}">TX</a>`;
    msg += `\n⏰ ${trade.timestamp.toUTCString().slice(17,25)} UTC`;
    return msg;
  };

  const sendTelegramSignal = async (trade) => {
    if (!cfg.telegramToken || !cfg.telegramChatId) return false;
    const msg = formatSignalMessage(trade);
    try {
      const res = await fetch(`https://api.telegram.org/bot${cfg.telegramToken}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chat_id: cfg.telegramChatId,
          text: msg,
          parse_mode: 'HTML',
          disable_web_page_preview: false,
        })
      });
      const data = await res.json();
      if (data.ok) {
        setStatus(prev => ({ ...prev, tg: { type: 'ok', text: 'Telegram: Yuborildi ✓' } }));
        return true;
      } else {
        setStatus(prev => ({ ...prev, tg: { type: 'err', text: 'Telegram: Xato' } }));
        return false;
      }
    } catch(e) {
      setStatus(prev => ({ ...prev, tg: { type: 'err', text: 'Telegram: Muvaffaqiyatsiz' } }));
      return false;
    }
  };

  const testTelegram = async () => {
    if (!cfg.telegramToken || !cfg.telegramChatId) {
      alert('Iltimos, avval Telegram Bot Token va Chat ID saqlang.');
      return;
    }
    const msg = `✅ <b>chainEDGE Bog'landi!</b>\n\nBot ishlamoqda. Aqlli hamyon signallari shu yerda paydo bo'ladi.\n\n🕐 ${new Date().toUTCString()}`;
    try {
      const res = await fetch(`https://api.telegram.org/bot${cfg.telegramToken}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: cfg.telegramChatId, text: msg, parse_mode: 'HTML' })
      });
      const data = await res.json();
      if (data.ok) {
        alert('✅ Sinov xabari yuborildi! Telegram botingizni tekshiring.');
        setStatus(prev => ({ ...prev, tg: { type: 'ok', text: 'Telegram: OK' } }));
      } else {
        alert('❌ Xato: ' + data.description);
      }
    } catch(e) {
      alert('❌ Tarmoq xatosi: ' + e.message);
    }
  };

  const addSignalLog = (trade) => {
    setSentSignals(prev => [{
      id: trade.id,
      type: trade.type,
      token: trade.token,
      usdValue: trade.usdValue,
      chain: trade.chain,
      wallet: trade.wallet.label,
      walletAddr: trade.wallet.addr,
      tokenData: trade.tokenData,
      time: new Date().toISOString(),
    }, ...prev]);
  };

  const filteredTrades = trades.filter(t => {
    if (currentFilter !== 'all' && t.type !== currentFilter) return false;
    if (currentChain !== 'all' && t.chain !== currentChain) return false;
    return true;
  });

  return (
    <div className="SmartMoney">
      <button className="close-btn" onClick={onClose}>&times;</button>

      {/* TOP BAR */}
      <div className="topbar">
        <div className="logo">chain<span>EDGE</span></div>
        <div className="chain-pills">
          {['all', 'eth', 'bsc', 'base', 'arbitrum', 'solana'].map(c => (
            <div
              key={c}
              className={`chain-pill ${currentChain === c ? 'active' : ''}`}
              onClick={() => setCurrentChain(c)}
            >
              {c.toUpperCase()}
            </div>
          ))}
        </div>
        <div className="spacer"></div>
        <div className="live-badge"><div className="live-dot"></div>LIVE</div>
        <div className={`tg-status ${cfg.telegramToken && cfg.telegramChatId ? 'connected' : ''}`} onClick={() => setActiveTab('config')}>
          📡 Telegram: <span id="tgStatusText">{cfg.telegramToken && cfg.telegramChatId ? 'Bog\'langan' : 'Sozlanmagan'}</span>
        </div>
        <button className="btn" onClick={() => setIsModalOpen(true)}>+ Hamyon Qo'shish</button>
        {!isMonitoring ? (
          <button className="btn" onClick={startMonitoring}>▶ Boshlash</button>
        ) : (
          <button className="btn danger" onClick={stopMonitoring}>■ To'xtatish</button>
        )}
      </div>

      {/* MAIN */}
      <div className="main-container">
        {/* SIDEBAR LEFT */}
        <div className="sidebar-left">
          <div className="panel-header">
            <div className="panel-title">Aqlli Pullar</div>
            <div className="badge-count">{wallets.length}</div>
          </div>
          <div className="wallet-list">
            {wallets.length === 0 ? (
              <div style={{padding:'20px', textAlign:'center', color:'var(--muted)', fontSize:'11px', lineHeight:'1.7'}}>
                Hali hamyonlar yo'q.<br/>Kuzatishni boshlash uchun hamyon qo'shing.
              </div>
            ) : (
              wallets.map((w, i) => (
                <div key={w.id} className={`wallet-item ${w.active ? 'active' : ''}`} onDoubleClick={() => removeWallet(w.id)}>
                   <div className="wallet-top">
                    <div className="wallet-avatar" style={{background: AVATAR_COLORS[i % AVATAR_COLORS.length]}}>{walletInitials(w.label)}</div>
                    <div style={{flex:1, overflow:'hidden'}}>
                      <div className="wallet-label" style={{opacity: w.active ? 1 : 0.4}}>{w.label}</div>
                      <div style={{display:'flex', alignItems:'center', gap:'6px', marginTop:'1px'}}>
                        <span className="chain-pill" style={{padding:'1px 6px', fontSize:'9px', cursor:'default', borderColor:'var(--border)'}}>{w.chain.toUpperCase()}</span>
                        {w.notes && <span style={{fontSize:'9px', color:'var(--muted)', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>{w.notes}</span>}
                      </div>
                    </div>
                    <div style={{display:'flex', flexDirection:'column', gap:'4px', alignItems:'flex-end'}}>
                      <div style={{fontSize:'9px', cursor:'pointer', color: w.active ? 'var(--buy)' : 'var(--muted)'}} onClick={() => toggleWallet(w.id)}>{w.active ? '●' : '○'}</div>
                    </div>
                  </div>
                  <div className="wallet-addr">{shortAddr(w.addr)}</div>
                  <div className="wallet-stats">
                    <div className="wstat"><div className="wstat-label">WIN RATE</div><div className="wstat-val blue">{w.winRate}</div></div>
                    <div className="wstat"><div className="wstat-label">PNL</div><div className={`wstat-val ${w.pnl.startsWith('+') ? 'green' : w.pnl.startsWith('-') ? 'red' : ''}`}>{w.pnl}</div></div>
                    <div className="wstat"><div className="wstat-label">TRADES(30D)</div><div className="wstat-val">{w.trades30d}</div></div>
                  </div>
                </div>
              ))
            )}
          </div>
          <button className="add-wallet-btn" onClick={() => setIsModalOpen(true)}>+ Yangi Hamyonni Kuzatish</button>
        </div>

        {/* CENTER FEED */}
        <div className="feed-area">
          <div className="feed-controls">
            <button className={`filter-btn ${currentFilter === 'all' ? 'active' : ''}`} onClick={() => setCurrentFilter('all')}>HAMMASI</button>
            <button className={`filter-btn ${currentFilter === 'buy' ? 'active' : ''}`} onClick={() => setCurrentFilter('buy')}>🟢 SOTIB OLISH</button>
            <button className={`filter-btn ${currentFilter === 'sell' ? 'sell-active' : ''}`} onClick={() => setCurrentFilter('sell')}>🔴 SOTISH</button>
            <div className="min-usd">
              <span>Min $</span>
              <input
                type="number"
                value={cfg.minUsd}
                onChange={(e) => setCfg(prev => ({ ...prev, minUsd: e.target.value }))}
                className="form-input"
                style={{width:'90px'}}
                placeholder="5000"
              />
            </div>
          </div>
          <div className="feed-scroll">
            {filteredTrades.length === 0 ? (
              <div className="empty-feed">
                <div className="empty-icon">👁</div>
                <div className="panel-title" style={{letterSpacing:'3px'}}>ALPHA OQIMI</div>
                <div style={{color:'var(--muted)', fontSize:'12px', maxWidth:'280px', lineHeight:'1.6'}}>
                  Hamyonlarni qo'shing, Sozlamalarda API kalitlarini sozlang va aqlli pullarni kuzatishni boshlash uchun <strong>▶ Boshlash</strong> tugmasini bosing.
                </div>
              </div>
            ) : (
              filteredTrades.map(trade => (
                <div key={trade.id} className={`trade-card ${trade.type}`}>
                  <div className="trade-top">
                    <div className={`trade-type-badge ${trade.type}`}>{trade.type.toUpperCase()}</div>
                    <div className={`trade-token chain-${trade.chain}`}>{trade.token}</div>
                    <span className={`trade-chain chain-${trade.chain}`}>{trade.chain.toUpperCase()}</span>
                    {trade.signalSent && <div className="signal-badge">📡 YUBORILDI</div>}
                    <div className="trade-time">{trade.timestamp.toTimeString().slice(0,8)}</div>
                  </div>
                  <div className="trade-mid">
                    <div className={`trade-usd ${trade.type}`}>{trade.usdValue > 0 ? '$' + formatNum(trade.usdValue) : '—'}</div>
                    <div className="trade-detail">{trade.amount > 0 ? formatNum(trade.amount) + ' ' + trade.token : trade.token}</div>
                    {trade.tokenData && trade.tokenData.priceChange24h !== undefined && (
                      <div className="trade-detail" style={{color: trade.tokenData.priceChange24h > 0 ? 'var(--buy)' : 'var(--sell)'}}>
                        {trade.tokenData.priceChange24h > 0 ? '▲' : '▼'}{Math.abs(trade.tokenData.priceChange24h).toFixed(1)}% 24s
                      </div>
                    )}
                  </div>
                  <div className="trade-bottom">
                    <div className="trade-meta">
                      {trade.tokenData && trade.tokenData.mcap > 0 && <div className="tmeta"><div className="tmeta-label">MCAP</div><div className="tmeta-val">${formatNum(trade.tokenData.mcap)}</div></div>}
                      {trade.tokenData && trade.tokenData.vol24h > 0 && <div className="tmeta"><div className="tmeta-label">24S HAJM</div><div className="tmeta-val">${formatNum(trade.tokenData.vol24h)}</div></div>}
                      {trade.tokenData && trade.tokenData.liquidity > 0 && <div className="tmeta"><div className="tmeta-label">LIKVIDLIK</div><div className="tmeta-val">${formatNum(trade.tokenData.liquidity)}</div></div>}
                      {trade.tokenData && trade.tokenData.dex && <div className="tmeta"><div className="tmeta-label">DEX</div><div className="tmeta-val">{trade.tokenData.dex}</div></div>}
                      {trade.solNote && <div className="tmeta"><div className="tmeta-label">INFO</div><div className="tmeta-val">{trade.solNote}</div></div>}
                    </div>
                    <div className="trade-wallet">
                      <span>{trade.wallet.label}</span>
                      <span style={{color:'var(--muted)'}}>{shortAddr(trade.wallet.addr)}</span>
                      {trade.tokenData && trade.tokenData.pairAddr && (
                        <a href={`https://dexscreener.com/${trade.chain}/${trade.tokenData.pairAddr}`} target="_blank" rel="noreferrer" style={{color:'var(--accent)', fontSize:'10px'}}>↗</a>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* SIDEBAR RIGHT */}
        <div className="sidebar-right">
          <div className="right-tabs">
            <div className={`rtab ${activeTab === 'signals' ? 'active' : ''}`} onClick={() => setActiveTab('signals')}>SIGNALLAR</div>
            <div className={`rtab ${activeTab === 'stats' ? 'active' : ''}`} onClick={() => setActiveTab('stats')}>STATISTIKA</div>
            <div className={`rtab ${activeTab === 'config' ? 'active' : ''}`} onClick={() => setActiveTab('config')}>SOZLAMALAR</div>
          </div>
          <div className="right-content">
            {activeTab === 'signals' && (
               sentSignals.length === 0 ? (
                <div style={{padding:'20px', textAlign:'center', color:'var(--muted)', fontSize:'11px', lineHeight:'1.8'}}>
                  Hali signallar yo'q.<br/>Signallarni ko'rish uchun Telegramni sozlang va kuzatishni boshlang.
                </div>
              ) : (
                sentSignals.map(s => (
                  <div key={s.id} className="signal-item">
                    <div className="signal-item-top">
                      <div className="signal-item-token">${s.token}</div>
                      <div className={`signal-item-type ${s.type}`}>{s.type.toUpperCase()}</div>
                      <div className="signal-item-time">{new Date(s.time).toTimeString().slice(0,8)}</div>
                    </div>
                    <div className="signal-item-row"><span className="signal-item-label">Qiymati</span><span className="signal-item-val">${formatNum(s.usdValue)}</span></div>
                    <div className="signal-item-row"><span className="signal-item-label">Tarmoq</span><span className="signal-item-val">{(s.chain||'').toUpperCase()}</span></div>
                    <div className="signal-item-row"><span className="signal-item-label">Hamyon</span><span className="signal-item-val">{s.wallet}</span></div>
                    {s.tokenData && s.tokenData.mcap > 0 && <div className="signal-item-row"><span className="signal-item-label">MCap</span><span className="signal-item-val">${formatNum(s.tokenData.mcap)}</span></div>}
                    <div className="signal-sent-badge">📡 Telegramga yuborildi</div>
                  </div>
                ))
              )
            )}
            {activeTab === 'stats' && (
              <>
                <div className="stat-grid">
                  <div className="stat-card">
                    <div className="stat-card-label">Jami Signallar</div>
                    <div className="stat-card-val" style={{color:'var(--accent)'}}>{stats.totalSignals}</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-card-label">Kuzatilgan Hamyonlar</div>
                    <div className="stat-card-val" style={{color:'var(--text)'}}>{wallets.length}</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-card-label">Sotib Olish</div>
                    <div className="stat-card-val" style={{color:'var(--buy)'}}>{stats.buySignals}</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-card-label">Sotish</div>
                    <div className="stat-card-val" style={{color:'var(--sell)'}}>{stats.sellSignals}</div>
                  </div>
                </div>
                <div className="stat-card" style={{marginBottom:'8px'}}>
                  <div className="stat-card-label">Jami Kuzatilgan Hajm</div>
                  <div className="stat-card-val" style={{color:'var(--warn)'}}>${formatNum(stats.totalVol)}</div>
                  <div className="stat-card-sub">barcha kuzatilgan almashinuvlar bo'yicha</div>
                </div>
                <div className="stat-card">
                  <div className="stat-card-label">Oqimdagi tranzaksiyalar</div>
                  <div className="stat-card-val" style={{color:'var(--text)'}}>{trades.length}</div>
                  <div className="stat-card-sub">ushbu sessiyada</div>
                </div>
                <div style={{marginTop:'12px'}}>
                  {wallets.slice(0,10).map(w => (
                    <div key={w.id} style={{display:'flex', alignItems:'center', gap:'8px', padding:'7px', borderRadius:'5px', border:'1px solid var(--border)', background:'var(--surface2)', marginBottom:'4px'}}>
                      <div style={{fontSize:'10px', fontWeight:'600', flex:1, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>{w.label}</div>
                      <div style={{fontFamily:'"JetBrains Mono", monospace', fontSize:'10px', color:'var(--buy)'}}>{w.winRate}</div>
                      <div style={{fontFamily:'"JetBrains Mono", monospace', fontSize:'10px', color:'var(--muted2)'}}>{w.trades30d} tx</div>
                    </div>
                  ))}
                </div>
              </>
            )}
            {activeTab === 'config' && (
              <>
                <div className="config-section">
                  <div className="config-section-title">Telegram Bot</div>
                  <div className="form-group">
                    <label className="form-label">BOT TOKEN (@BotFather dan)</label>
                    <input
                      type="password"
                      value={cfg.telegramToken}
                      onChange={(e) => setCfg(prev => ({ ...prev, telegramToken: e.target.value }))}
                      className="form-input"
                      placeholder="1234567890:AAF..."
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">ADMIN CHAT ID</label>
                    <input
                      type="text"
                      value={cfg.telegramChatId}
                      onChange={(e) => setCfg(prev => ({ ...prev, telegramChatId: e.target.value }))}
                      className="form-input"
                      placeholder="-100... yoki foydalanuvchi ID"
                    />
                  </div>
                  <div className="form-group" style={{display:'flex', alignItems:'center', gap:'8px', marginTop:'4px'}}>
                    <input
                      type="checkbox"
                      checked={cfg.autoSend}
                      onChange={(e) => setCfg(prev => ({ ...prev, autoSend: e.target.checked }))}
                      style={{accentColor:'var(--accent)'}}
                    />
                    <label className="form-label" style={{margin:0, cursor:'pointer'}}>Signallarni avtomatik yuborish</label>
                  </div>
                </div>
                <div className="config-section">
                  <div className="config-section-title">Explorer API Kalitlari (ixtiyoriy)</div>
                  <div className="form-group">
                    <label className="form-label">ETHERSCAN / BASESCAN KEY</label>
                    <input
                      type="password"
                      value={cfg.etherscanKey}
                      onChange={(e) => setCfg(prev => ({ ...prev, etherscanKey: e.target.value }))}
                      className="form-input"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">BSCSCAN API KEY</label>
                    <input
                      type="password"
                      value={cfg.bscscanKey}
                      onChange={(e) => setCfg(prev => ({ ...prev, bscscanKey: e.target.value }))}
                      className="form-input"
                    />
                  </div>
                </div>
                <div className="config-section">
                  <div className="config-section-title">Kuzatuv Sozlamalari</div>
                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-label">SCAN INTERVALI (sek)</label>
                      <input
                        type="number"
                        value={cfg.updateInterval}
                        onChange={(e) => setCfg(prev => ({ ...prev, updateInterval: e.target.value }))}
                        className="form-input"
                        min="15"
                        max="300"
                      />
                    </div>
                  </div>
                </div>
                <button className="save-btn" onClick={() => alert('✅ Sozlamalar saqlandi!')}>💾 Sozlamalarni Saqlash</button>
                <button className="test-btn" onClick={testTelegram}>📡 Telegramni Sinab Ko'rish</button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* STATUS BAR */}
      <div className="statusbar">
        <div className={`status-item ${status.monitor.type}`}>
          <div className="dot"></div>{status.monitor.text}
        </div>
        <div className={`status-item ${status.dex.type}`}>
          <div className="dot"></div>{status.dex.text}
        </div>
        <div className={`status-item ${status.tg.type}`}>
          <div className="dot"></div>{status.tg.text}
        </div>
        <div className={`status-item ${status.scan.type}`}>
          <div className="dot"></div>{status.scan.text}
        </div>
        <div className="status-right">{status.lastUpdate}</div>
      </div>

      {/* ADD WALLET MODAL */}
      {isModalOpen && (
        <div className="modal-overlay" onClick={() => setIsModalOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-title">AQLLI HAMYON QO'SHISH</div>
            <div className="form-group">
              <label className="form-label">HAMYON MANZILI</label>
              <input
                type="text"
                value={newWallet.addr}
                onChange={(e) => setNewWallet({...newWallet, addr: e.target.value})}
                className="form-input"
                placeholder="0x... yoki Solana manzili"
              />
            </div>
            <div className="form-group">
              <label className="form-label">NOMI (LABEL)</label>
              <input
                type="text"
                value={newWallet.label}
                onChange={(e) => setNewWallet({...newWallet, label: e.target.value})}
                className="form-input"
                placeholder="masalan, Alpha Kit #1"
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">TARMOQ</label>
                <select
                  value={newWallet.chain}
                  onChange={(e) => setNewWallet({...newWallet, chain: e.target.value})}
                  className="form-input"
                >
                  <option value="eth">Ethereum</option>
                  <option value="bsc">BSC</option>
                  <option value="base">Base</option>
                  <option value="arbitrum">Arbitrum</option>
                  <option value="solana">Solana</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">WIN RATE %</label>
                <input
                  type="number"
                  value={newWallet.winRate}
                  onChange={(e) => setNewWallet({...newWallet, winRate: e.target.value})}
                  className="form-input"
                  placeholder="75"
                />
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">ESLATMA (ixtiyoriy)</label>
              <input
                type="text"
                value={newWallet.notes}
                onChange={(e) => setNewWallet({...newWallet, notes: e.target.value})}
                className="form-input"
              />
            </div>
            <div className="modal-footer">
              <button className="cancel-btn" onClick={() => setIsModalOpen(false)}>Bekor Qilish</button>
              <button className="confirm-btn" onClick={addWallet}>Hamyonni Qo'shish</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SmartMoney;
