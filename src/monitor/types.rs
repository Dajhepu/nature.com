use chrono::{DateTime, Utc};
use solana_sdk::pubkey::Pubkey;

/// Token manbai
#[derive(Debug, Clone, PartialEq)]
pub enum TokenSource {
    PumpFun,
    Raydium,
}

/// Yangi token aniqlanganda yuboriluvchi event
#[derive(Debug, Clone)]
pub struct TokenEvent {
    /// Token mint adresi
    pub mint: Pubkey,

    /// Token manbai (Pump.fun yoki Raydium)
    pub source: TokenSource,

    /// Aniqlangan vaqt
    pub detected_at: DateTime<Utc>,

    /// Boshlang'ich likvidlik (lamports)
    pub initial_liquidity: Option<u64>,

    /// Token nomi (agar ma'lum bo'lsa)
    pub name: Option<String>,

    /// Token symboli
    pub symbol: Option<String>,

    /// Pump.fun bonding curve adresi
    pub bonding_curve: Option<Pubkey>,

    /// Raydium pool adresi
    pub pool_id: Option<Pubkey>,

    /// Transaction signature
    pub signature: String,
}

impl TokenEvent {
    pub fn new_pump_fun(
        mint: Pubkey,
        bonding_curve: Pubkey,
        signature: String,
        name: Option<String>,
        symbol: Option<String>,
    ) -> Self {
        Self {
            mint,
            source: TokenSource::PumpFun,
            detected_at: Utc::now(),
            initial_liquidity: None,
            name,
            symbol,
            bonding_curve: Some(bonding_curve),
            pool_id: None,
            signature,
        }
    }

    pub fn new_raydium(
        mint: Pubkey,
        pool_id: Pubkey,
        signature: String,
        initial_liquidity: Option<u64>,
    ) -> Self {
        Self {
            mint,
            source: TokenSource::Raydium,
            detected_at: Utc::now(),
            initial_liquidity,
            name: None,
            symbol: None,
            bonding_curve: None,
            pool_id: Some(pool_id),
            signature,
        }
    }

    pub fn age_ms(&self) -> i64 {
        (Utc::now() - self.detected_at).num_milliseconds()
    }
}
