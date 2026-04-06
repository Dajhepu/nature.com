use super::ExitReason;
use chrono::{DateTime, Utc};
use solana_sdk::pubkey::Pubkey;

/// Pozitsiya holati
#[derive(Debug, Clone, PartialEq)]
pub enum PositionStatus {
    Open,
    Closing,
    Closed,
}

/// Bitta savdo pozitsiyasi
#[derive(Debug, Clone)]
pub struct Position {
    pub mint: Pubkey,
    pub entry_price: u64,       // Token narxi kirish paytida (lamports/token)
    pub amount_tokens: u64,     // Sotib olingan token miqdori
    pub sol_spent: u64,         // Sarflangan SOL (lamports)
    pub opened_at: DateTime<Utc>,
    pub status: PositionStatus,

    // Exit parametrlari
    pub take_profit_price: u64,
    pub stop_loss_price: u64,
    pub max_hold_secs: u64,
}

impl Position {
    pub fn new(
        mint: Pubkey,
        entry_price: u64,
        amount_tokens: u64,
        sol_spent: u64,
        take_profit_pct: f64,
        stop_loss_pct: f64,
        max_hold_secs: u64,
    ) -> Self {
        let tp_multiplier = 1.0 + take_profit_pct / 100.0;
        let sl_multiplier = 1.0 - stop_loss_pct / 100.0;

        Self {
            mint,
            entry_price,
            amount_tokens,
            sol_spent,
            opened_at: Utc::now(),
            status: PositionStatus::Open,
            take_profit_price: (entry_price as f64 * tp_multiplier) as u64,
            stop_loss_price: (entry_price as f64 * sl_multiplier) as u64,
            max_hold_secs,
        }
    }

    /// Chiqish signalini tekshirish
    pub fn check_exit(&self, current_price: u64) -> Option<ExitReason> {
        if self.status != PositionStatus::Open {
            return None;
        }

        // Take Profit
        if current_price >= self.take_profit_price {
            return Some(ExitReason::TakeProfit);
        }

        // Stop Loss
        if current_price <= self.stop_loss_price {
            return Some(ExitReason::StopLoss);
        }

        // Vaqt tugadimi?
        if self.is_expired() {
            return Some(ExitReason::TimeExpired);
        }

        None
    }

    /// Vaqt chegarasi tugaganmi?
    pub fn is_expired(&self) -> bool {
        let elapsed = (Utc::now() - self.opened_at).num_seconds() as u64;
        elapsed >= self.max_hold_secs
    }

    /// PnL foizini hisoblash
    pub fn calculate_pnl(&self, exit_price: u64) -> f64 {
        if self.entry_price == 0 {
            return 0.0;
        }
        (exit_price as f64 - self.entry_price as f64) / self.entry_price as f64 * 100.0
    }

    /// Qancha vaqt ochiq turganini olish (soniyalarda)
    pub fn age_seconds(&self) -> i64 {
        (Utc::now() - self.opened_at).num_seconds()
    }
}
