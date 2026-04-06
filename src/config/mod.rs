use anyhow::{Context, Result};
use std::env;

/// Bot konfiguratsiyasi - barcha sozlamalar
#[derive(Debug, Clone)]
pub struct Config {
    // RPC
    pub rpc_https: String,
    pub rpc_wss: String,

    // Wallet
    pub private_key: String,

    // Trading
    pub slippage_bps: u16,        // Basis points (100 = 1%)
    pub max_position_sol: f64,
    pub min_liquidity_sol: f64,

    // Exit strategy
    pub take_profit_pct: f64,
    pub stop_loss_pct: f64,
    pub max_hold_time_secs: u64,

    // Fees
    pub priority_fee_microlamports: u64,
    pub jito_tip_lamports: u64,
    pub jito_endpoint: String,

    // Program IDs
    pub pump_fun_program: String,
    pub raydium_amm_program: String,

    // Logging
    pub log_level: String,

    // Safety
    pub max_concurrent_positions: usize,
    pub analysis_timeout_ms: u64,
}

impl Config {
    /// .env faylidan konfiguratsiyani yuklash
    pub fn load() -> Result<Self> {
        dotenv::dotenv().ok();

        let slippage_pct: f64 = get_env_f64("SLIPPAGE", 15.0)?;
        let slippage_bps = (slippage_pct * 100.0) as u16;

        Ok(Config {
            rpc_https: get_env("RPC_HTTPS", "https://api.mainnet-beta.solana.com"),
            rpc_wss: get_env("RPC_WSS", "wss://api.mainnet-beta.solana.com"),
            private_key: env::var("PRIVATE_KEY")
                .context("PRIVATE_KEY .env faylida topilmadi")?,
            slippage_bps,
            max_position_sol: get_env_f64("MAX_POSITION_SIZE", 0.1)?,
            min_liquidity_sol: get_env_f64("MIN_LIQUIDITY", 1.0)?,
            take_profit_pct: get_env_f64("TAKE_PROFIT", 50.0)?,
            stop_loss_pct: get_env_f64("STOP_LOSS", 30.0)?,
            max_hold_time_secs: get_env_u64("MAX_HOLD_TIME", 120)?,
            priority_fee_microlamports: get_env_u64("PRIORITY_FEE", 100_000)?,
            jito_tip_lamports: get_env_u64("JITO_TIP", 0)?,
            jito_endpoint: get_env(
                "JITO_ENDPOINT",
                "https://mainnet.block-engine.jito.wtf",
            ),
            pump_fun_program: get_env(
                "PUMP_FUN_PROGRAM",
                "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
            ),
            raydium_amm_program: get_env(
                "RAYDIUM_AMM_PROGRAM",
                "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
            ),
            log_level: get_env("LOG_LEVEL", "info"),
            max_concurrent_positions: get_env_usize("MAX_CONCURRENT_POSITIONS", 3)?,
            analysis_timeout_ms: get_env_u64("ANALYSIS_TIMEOUT_MS", 500)?,
        })
    }

    /// Pozitsiya hajmini lamports da qaytarish
    pub fn max_position_lamports(&self) -> u64 {
        (self.max_position_sol * 1_000_000_000.0) as u64
    }

    /// Minimal likvidlikni lamports da qaytarish
    pub fn min_liquidity_lamports(&self) -> u64 {
        (self.min_liquidity_sol * 1_000_000_000.0) as u64
    }
}

// ── Yordamchi funksiyalar ──────────────────────────────────────────────────

fn get_env(key: &str, default: &str) -> String {
    env::var(key).unwrap_or_else(|_| default.to_string())
}

fn get_env_f64(key: &str, default: f64) -> Result<f64> {
    match env::var(key) {
        Ok(val) => val
            .parse::<f64>()
            .with_context(|| format!("{key} noto'g'ri format: f64 kutilgan")),
        Err(_) => Ok(default),
    }
}

fn get_env_u64(key: &str, default: u64) -> Result<u64> {
    match env::var(key) {
        Ok(val) => val
            .parse::<u64>()
            .with_context(|| format!("{key} noto'g'ri format: u64 kutilgan")),
        Err(_) => Ok(default),
    }
}

fn get_env_usize(key: &str, default: usize) -> Result<usize> {
    match env::var(key) {
        Ok(val) => val
            .parse::<usize>()
            .with_context(|| format!("{key} noto'g'ri format: usize kutilgan")),
        Err(_) => Ok(default),
    }
}
