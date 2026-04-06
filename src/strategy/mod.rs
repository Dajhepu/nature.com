pub mod position;

use crate::analyzer::AnalysisResult;
use crate::config::Config;
use crate::monitor::TokenEvent;
use chrono::{DateTime, Utc};
use dashmap::DashMap;
use solana_sdk::pubkey::Pubkey;
use std::sync::Arc;
use tracing::{info, warn};

pub use position::{Position, PositionStatus};

/// Strategiya menejeri - pozitsiyalarni boshqaradi
pub struct Strategy {
    config: Config,
    /// Faol pozitsiyalar: mint → Position
    positions: Arc<DashMap<Pubkey, Position>>,
}

impl Strategy {
    pub fn new(config: Config) -> Self {
        Self {
            config,
            positions: Arc::new(DashMap::new()),
        }
    }

    pub fn positions(&self) -> Arc<DashMap<Pubkey, Position>> {
        self.positions.clone()
    }

    /// BUY amalga oshirilsinmi?
    pub fn should_buy(&self, event: &TokenEvent, analysis: &AnalysisResult) -> bool {
        if !analysis.approved {
            return false;
        }

        // Maksimal pozitsiyalar sonini tekshirish
        if self.positions.len() >= self.config.max_concurrent_positions {
            warn!(
                "⛔ Maksimal pozitsiyalar ({}) to'ldi, BUY o'tkazib yuborildi",
                self.config.max_concurrent_positions
            );
            return false;
        }

        // Allaqachon pozitsiya bormi?
        if self.positions.contains_key(&event.mint) {
            return false;
        }

        true
    }

    /// Pozitsiya ochish (BUY bajarilgandan keyin)
    pub fn open_position(
        &self,
        mint: Pubkey,
        entry_price_lamports: u64,
        amount_tokens: u64,
        sol_spent: u64,
    ) {
        let position = Position::new(
            mint,
            entry_price_lamports,
            amount_tokens,
            sol_spent,
            self.config.take_profit_pct,
            self.config.stop_loss_pct,
            self.config.max_hold_time_secs,
        );
        self.positions.insert(mint, position);
        info!(
            "📂 Pozitsiya ochildi: {} | {:.4} SOL sarflandi",
            mint,
            sol_spent as f64 / 1e9
        );
    }

    /// Pozitsiya yopish (SELL bajarilgandan keyin)
    pub fn close_position(&self, mint: &Pubkey, exit_price: u64) {
        if let Some((_, pos)) = self.positions.remove(mint) {
            let pnl = pos.calculate_pnl(exit_price);
            info!(
                "📊 Pozitsiya yopildi: {} | PnL: {:.2}%",
                mint,
                pnl
            );
        }
    }

    /// Har bir faol pozitsiyani tekshirish - SELL kerakmi?
    pub fn check_exit_signals(&self, mint: &Pubkey, current_price: u64) -> Option<ExitReason> {
        let position = self.positions.get(mint)?;
        position.check_exit(current_price)
    }

    /// Barcha pozitsiyalarni vaqt bo'yicha tekshirish
    pub fn get_expired_positions(&self) -> Vec<Pubkey> {
        self.positions
            .iter()
            .filter(|entry| entry.value().is_expired())
            .map(|entry| *entry.key())
            .collect()
    }
}

/// SELL sababi
#[derive(Debug, Clone)]
pub enum ExitReason {
    TakeProfit,
    StopLoss,
    TimeExpired,
    Manual,
}

impl std::fmt::Display for ExitReason {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ExitReason::TakeProfit => write!(f, "Take Profit 🎉"),
            ExitReason::StopLoss => write!(f, "Stop Loss 🛑"),
            ExitReason::TimeExpired => write!(f, "Vaqt tugadi ⏰"),
            ExitReason::Manual => write!(f, "Qo'lda ✋"),
        }
    }
}
