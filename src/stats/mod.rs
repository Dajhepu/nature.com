/// Savdo statistikasini kuzatish va chiqarish

use chrono::{DateTime, Utc};
use parking_lot::RwLock;
use std::sync::Arc;
use tracing::info;

#[derive(Debug, Default, Clone)]
pub struct TradeRecord {
    pub mint: String,
    pub source: String,
    pub sol_spent: u64,
    pub sol_received: u64,
    pub opened_at: Option<DateTime<Utc>>,
    pub closed_at: Option<DateTime<Utc>>,
    pub exit_reason: String,
    pub success: bool,
}

impl TradeRecord {
    pub fn pnl_pct(&self) -> f64 {
        if self.sol_spent == 0 {
            return 0.0;
        }
        (self.sol_received as f64 - self.sol_spent as f64) / self.sol_spent as f64 * 100.0
    }

    pub fn pnl_sol(&self) -> f64 {
        (self.sol_received as i64 - self.sol_spent as i64) as f64 / 1e9
    }

    pub fn hold_time_secs(&self) -> i64 {
        match (self.opened_at, self.closed_at) {
            (Some(o), Some(c)) => (c - o).num_seconds(),
            _ => 0,
        }
    }
}

/// Statistika agregatori
pub struct Stats {
    inner: Arc<RwLock<StatsInner>>,
}

#[derive(Debug, Default)]
struct StatsInner {
    tokens_detected: u64,
    tokens_analyzed: u64,
    tokens_rejected: u64,
    buys_attempted: u64,
    buys_succeeded: u64,
    sells_attempted: u64,
    sells_succeeded: u64,
    total_sol_spent: u64,
    total_sol_received: u64,
    trades: Vec<TradeRecord>,
    start_time: Option<DateTime<Utc>>,
}

impl Stats {
    pub fn new() -> Self {
        let mut inner = StatsInner::default();
        inner.start_time = Some(Utc::now());
        Self {
            inner: Arc::new(RwLock::new(inner)),
        }
    }

    pub fn token_detected(&self) {
        self.inner.write().tokens_detected += 1;
    }

    pub fn token_analyzed(&self) {
        self.inner.write().tokens_analyzed += 1;
    }

    pub fn token_rejected(&self) {
        self.inner.write().tokens_rejected += 1;
    }

    pub fn buy_attempted(&self) {
        self.inner.write().buys_attempted += 1;
    }

    pub fn buy_succeeded(&self, sol_spent: u64) {
        let mut s = self.inner.write();
        s.buys_succeeded += 1;
        s.total_sol_spent += sol_spent;
    }

    pub fn sell_attempted(&self) {
        self.inner.write().sells_attempted += 1;
    }

    pub fn sell_succeeded(&self, sol_received: u64) {
        let mut s = self.inner.write();
        s.sells_succeeded += 1;
        s.total_sol_received += sol_received;
    }

    pub fn record_trade(&self, record: TradeRecord) {
        self.inner.write().trades.push(record);
    }

    /// Statistikani konsol ga chiqarish
    pub fn print_summary(&self) {
        let s = self.inner.read();

        let uptime = s
            .start_time
            .map(|t| (Utc::now() - t).num_minutes())
            .unwrap_or(0);

        let total_pnl = s.total_sol_received as i64 - s.total_sol_spent as i64;
        let pnl_sol = total_pnl as f64 / 1e9;
        let win_rate = if s.sells_succeeded > 0 {
            let wins = s.trades.iter().filter(|t| t.sol_received > t.sol_spent).count();
            wins as f64 / s.sells_succeeded as f64 * 100.0
        } else {
            0.0
        };

        let avg_hold = if !s.trades.is_empty() {
            s.trades.iter().map(|t| t.hold_time_secs()).sum::<i64>() / s.trades.len() as i64
        } else {
            0
        };

        info!("");
        info!("╔══════════════════════════════════════════════════╗");
        info!("║              📊 SAVDO STATISTIKASI               ║");
        info!("╠══════════════════════════════════════════════════╣");
        info!("║  ⏱  Ishlash vaqti:    {uptime:>6} daqiqa              ║");
        info!("╠══════════════════════════════════════════════════╣");
        info!("║  🔭 Aniqlangan:       {:>6}                      ║", s.tokens_detected);
        info!("║  🔍 Tahlil qilindi:   {:>6}                      ║", s.tokens_analyzed);
        info!("║  ❌ Rad etildi:       {:>6}                      ║", s.tokens_rejected);
        info!("╠══════════════════════════════════════════════════╣");
        info!("║  🟢 BUY urinish:      {:>6}                      ║", s.buys_attempted);
        info!("║  🟢 BUY muvaffaq:     {:>6}                      ║", s.buys_succeeded);
        info!("║  🔴 SELL urinish:     {:>6}                      ║", s.sells_attempted);
        info!("║  🔴 SELL muvaffaq:    {:>6}                      ║", s.sells_succeeded);
        info!("╠══════════════════════════════════════════════════╣");
        info!("║  💰 Sarflangan SOL:   {:>8.4}                    ║", s.total_sol_spent as f64 / 1e9);
        info!("║  💰 Olingan SOL:      {:>8.4}                    ║", s.total_sol_received as f64 / 1e9);
        let pnl_sign = if pnl_sol >= 0.0 { "+" } else { "" };
        info!("║  📈 Jami PnL:         {}{:>7.4} SOL               ║", pnl_sign, pnl_sol);
        info!("║  🎯 Win Rate:         {:>6.1}%                     ║", win_rate);
        info!("║  ⏱  O'rtacha ushlab:  {:>6}s                      ║", avg_hold);
        info!("╚══════════════════════════════════════════════════╝");
        info!("");

        // Oxirgi 5 ta savdo
        if !s.trades.is_empty() {
            info!("📋 Oxirgi savdolar:");
            for trade in s.trades.iter().rev().take(5) {
                let pnl = trade.pnl_pct();
                let icon = if pnl > 0.0 { "🟢" } else { "🔴" };
                info!(
                    "  {} {} | {:+.1}% | {} | {}s",
                    icon,
                    &trade.mint[..8.min(trade.mint.len())],
                    pnl,
                    trade.exit_reason,
                    trade.hold_time_secs()
                );
            }
        }
    }
}
