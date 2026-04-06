// 🚀 Solana Sniper Bot - Consolidated Version
// Pump.fun + Raydium | Rust + Tokio

mod config {
use anyhow::{bail, Context, Result};
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

    // NEW: Dashboard & Telegram
    pub dashboard_port: u16,
    pub telegram_token: Option<String>,
    pub telegram_chat_id: Option<String>,
}

impl Config {
    /// .env faylidan konfiguratsiyani yuklash
    pub fn load() -> Result<Self> {
        ::dotenvy::dotenv().ok();

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
            dashboard_port: get_env_u64("DASHBOARD_PORT", 8080)? as u16,
            telegram_token: env::var("TELEGRAM_TOKEN").ok(),
            telegram_chat_id: env::var("TELEGRAM_CHAT_ID").ok(),
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
}
mod monitor {
    pub mod types {
use chrono::{DateTime, Utc};
use solana_sdk::pubkey::Pubkey;

/// Token manbai
#[derive(Debug, Clone, PartialEq, serde::Serialize)]
pub enum TokenSource {
    PumpFun,
    Raydium,
}

/// Yangi token aniqlanganda yuboriluvchi event
#[derive(Debug, Clone, serde::Serialize)]
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
    }
    pub mod pump_fun {
use super::types::TokenEvent;
use crate::config::Config;
use anyhow::{bail, Result};
use futures_util::{SinkExt, StreamExt};
use serde_json::{json, Value};
use solana_sdk::pubkey::Pubkey;
use std::str::FromStr;
use std::time::Duration;
use tokio::sync::mpsc;
use tokio::time::sleep;
use tokio_tungstenite::{connect_async, tungstenite::Message};
use tracing::{debug, error, info, warn};

/// Pump.fun yangi tokenlarni kuzatuvchi
pub struct PumpFunMonitor {
    config: Config,
}

impl PumpFunMonitor {
    pub fn new(config: Config) -> Self {
        Self { config }
    }

    /// WebSocket orqali Pump.fun loglarini kuzatish
    pub async fn run(&self, tx: mpsc::Sender<TokenEvent>) -> Result<()> {
        let mut retry_count = 0u32;
        let max_retries = u32::MAX;

        loop {
            info!("🔌 Pump.fun WebSocket ga ulanmoqda...");

            match self.connect_and_listen(tx.clone()).await {
                Ok(_) => {
                    info!("Pump.fun ulanish yopildi, qayta ulanmoqda...");
                }
                Err(e) => {
                    retry_count += 1;
                    let wait = calculate_backoff(retry_count);
                    error!(
                        "❌ Pump.fun xatosi (urinish {retry_count}/{max_retries}): {e}. \
                         {wait}s kutmoqda..."
                    );
                    sleep(Duration::from_secs(wait)).await;
                }
            }
        }
    }

    async fn connect_and_listen(&self, tx: mpsc::Sender<TokenEvent>) -> Result<()> {
        let (ws_stream, _) = connect_async(&self.config.rpc_wss).await?;
        let (mut write, mut read) = ws_stream.split();

        info!("✅ Pump.fun WebSocket ulandi");

        // Pump.fun program loglariga subscribe bo'lish
        let subscribe_msg = json!({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "logsSubscribe",
            "params": [
                {
                    "mentions": [&self.config.pump_fun_program]
                },
                {
                    "commitment": "processed"
                }
            ]
        });

        write
            .send(Message::Text(subscribe_msg.to_string()))
            .await?;
        info!("📡 Pump.fun loglariga obuna bo'lindi");

        // Xabarlarni o'qish
        while let Some(msg) = read.next().await {
            match msg {
                Ok(Message::Text(text)) => {
                    if let Err(e) = self.process_message(&text, &tx).await {
                        debug!("Xabar qayta ishlash xatosi: {e}");
                    }
                }
                Ok(Message::Ping(data)) => {
                    write.send(Message::Pong(data)).await?;
                }
                Ok(Message::Close(_)) => {
                    warn!("⚠️ WebSocket ulanish yopildi");
                    break;
                }
                Err(e) => {
                    bail!("WebSocket xatosi: {e}");
                }
                _ => {}
            }
        }

        Ok(())
    }

    /// Kelgan xabarni qayta ishlash
    async fn process_message(&self, text: &str, tx: &mpsc::Sender<TokenEvent>) -> Result<()> {
        let value: Value = serde_json::from_str(text)?;

        // Subscription confirmation ni o'tkazib yuborish
        if value.get("result").is_some() && value["result"].is_number() {
            debug!("Pump.fun subscription tasdiqlandi");
            return Ok(());
        }

        // Log notification tekshirish
        let notification = match value.get("params") {
            Some(p) => p,
            None => return Ok(()),
        };

        let result = &notification["result"];
        let value_obj = &result["value"];
        let logs = match value_obj["logs"].as_array() {
            Some(l) => l,
            None => return Ok(()),
        };

        let signature = value_obj["signature"]
            .as_str()
            .unwrap_or("")
            .to_string();

        // Loglarni tekshirib yangi token (mint) aniqlash
        if self.is_new_token_creation(logs) {
            if let Some(event) = self.extract_token_event(logs, &signature) {
                info!(
                    "🎯 Pump.fun yangi token aniqlandi: {} | sig: {}...",
                    event.mint,
                    &signature[..8]
                );
                let _ = tx.send(event).await;
            }
        }

        Ok(())
    }

    /// Log massivida yangi token yaratilganini aniqlash
    fn is_new_token_creation(&self, logs: &[Value]) -> bool {
        logs.iter().any(|log| {
            let s = log.as_str().unwrap_or("");
            // Pump.fun "create" instruction log pattern
            s.contains("Program log: Instruction: Create")
                || s.contains("InitializeMint")
                || s.contains("Program log: ray_log")
        })
    }

    /// Log dan token ma'lumotlarini chiqarish
    fn extract_token_event(&self, logs: &[Value], signature: &str) -> Option<TokenEvent> {
        let mut mint_str: Option<&str> = None;
        let mut bonding_curve_str: Option<&str> = None;
        let mut name: Option<String> = None;
        let mut symbol: Option<String> = None;

        for log in logs {
            let s = log.as_str().unwrap_or("");

            // Mint adresini aniqlash
            if s.contains("mint:") {
                mint_str = extract_after(s, "mint:");
            }

            // Bonding curve adresini aniqlash
            if s.contains("bondingCurve:") || s.contains("bonding_curve:") {
                bonding_curve_str = extract_after(s, "bondingCurve:");
                if bonding_curve_str.is_none() {
                    bonding_curve_str = extract_after(s, "bonding_curve:");
                }
            }

            // Token nomi va symboli
            if s.contains("name:") {
                name = extract_after(s, "name:").map(str::trim).map(String::from);
            }
            if s.contains("symbol:") {
                symbol = extract_after(s, "symbol:").map(str::trim).map(String::from);
            }
        }

        let mint = mint_str.and_then(|s| Pubkey::from_str(s.trim()).ok())?;

        // Bonding curve mavjud bo'lmasa default yasash (haqiqiy botda RPC dan olinadi)
        let bonding_curve = bonding_curve_str
            .and_then(|s| Pubkey::from_str(s.trim()).ok())
            .unwrap_or(mint); // fallback

        Some(TokenEvent::new_pump_fun(
            mint,
            bonding_curve,
            signature.to_string(),
            name,
            symbol,
        ))
    }
}

// ── Yordamchi funksiyalar ──────────────────────────────────────────────────

fn extract_after<'a>(s: &'a str, key: &str) -> Option<&'a str> {
    s.find(key).map(|i| {
        let rest = &s[i + key.len()..];
        rest.split_whitespace().next().unwrap_or("").trim_matches(',')
    })
}

fn calculate_backoff(attempt: u32) -> u64 {
    let base = 2u64.pow(attempt.min(6));
    base.min(64)
}
    }
    pub mod raydium {
use super::types::TokenEvent;
use crate::config::Config;
use anyhow::{bail, Result};
use futures_util::{SinkExt, StreamExt};
use serde_json::{json, Value};
use solana_sdk::pubkey::Pubkey;
use std::str::FromStr;
use std::time::Duration;
use tokio::sync::mpsc;
use tokio::time::sleep;
use tokio_tungstenite::{connect_async, tungstenite::Message};
use tracing::{debug, error, info, warn};

/// Raydium yangi pool yaratilishini kuzatuvchi
pub struct RaydiumMonitor {
    config: Config,
}

impl RaydiumMonitor {
    pub fn new(config: Config) -> Self {
        Self { config }
    }

    pub async fn run(&self, tx: mpsc::Sender<TokenEvent>) -> Result<()> {
        let mut retry_count = 0u32;

        loop {
            info!("🔌 Raydium WebSocket ga ulanmoqda...");

            match self.connect_and_listen(tx.clone()).await {
                Ok(_) => {
                    info!("Raydium ulanish yopildi, qayta ulanmoqda...");
                }
                Err(e) => {
                    retry_count += 1;
                    let wait = 2u64.pow(retry_count.min(6)).min(64);
                    error!(
                        "❌ Raydium xatosi (urinish {retry_count}): {e}. \
                         {wait}s kutmoqda..."
                    );
                    sleep(Duration::from_secs(wait)).await;
                }
            }
        }
    }

    async fn connect_and_listen(&self, tx: mpsc::Sender<TokenEvent>) -> Result<()> {
        let (ws_stream, _) = connect_async(&self.config.rpc_wss).await?;
        let (mut write, mut read) = ws_stream.split();

        info!("✅ Raydium WebSocket ulandi");

        // Raydium AMM program loglariga subscribe
        let subscribe_msg = json!({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "logsSubscribe",
            "params": [
                {
                    "mentions": [&self.config.raydium_amm_program]
                },
                {
                    "commitment": "processed"
                }
            ]
        });

        write
            .send(Message::Text(subscribe_msg.to_string()))
            .await?;
        info!("📡 Raydium loglariga obuna bo'lindi");

        while let Some(msg) = read.next().await {
            match msg {
                Ok(Message::Text(text)) => {
                    if let Err(e) = self.process_message(&text, &tx).await {
                        debug!("Raydium xabar xatosi: {e}");
                    }
                }
                Ok(Message::Ping(data)) => {
                    write.send(Message::Pong(data)).await?;
                }
                Ok(Message::Close(_)) => {
                    warn!("⚠️ Raydium WebSocket yopildi");
                    break;
                }
                Err(e) => bail!("Raydium WebSocket xatosi: {e}"),
                _ => {}
            }
        }

        Ok(())
    }

    async fn process_message(&self, text: &str, tx: &mpsc::Sender<TokenEvent>) -> Result<()> {
        let value: Value = serde_json::from_str(text)?;

        if value.get("result").is_some() && value["result"].is_number() {
            debug!("Raydium subscription tasdiqlandi");
            return Ok(());
        }

        let notification = match value.get("params") {
            Some(p) => p,
            None => return Ok(()),
        };

        let result = &notification["result"];
        let value_obj = &result["value"];
        let logs = match value_obj["logs"].as_array() {
            Some(l) => l,
            None => return Ok(()),
        };

        let signature = value_obj["signature"]
            .as_str()
            .unwrap_or("")
            .to_string();

        // Yangi pool yaratilishini aniqlash
        if self.is_new_pool(logs) {
            if let Some(event) = self.extract_pool_event(logs, &signature) {
                info!(
                    "🎯 Raydium yangi pool aniqlandi: {} | sig: {}...",
                    event.mint,
                    &signature[..8.min(signature.len())]
                );
                let _ = tx.send(event).await;
            }
        }

        Ok(())
    }

    fn is_new_pool(&self, logs: &[Value]) -> bool {
        logs.iter().any(|log| {
            let s = log.as_str().unwrap_or("");
            // Raydium "initialize2" yoki "initialize" instruction
            s.contains("Instruction: Initialize2")
                || s.contains("Instruction: Initialize")
                || s.contains("initialize_amm")
        })
    }

    fn extract_pool_event(&self, logs: &[Value], signature: &str) -> Option<TokenEvent> {
        let mut pool_id: Option<Pubkey> = None;
        let mut base_mint: Option<Pubkey> = None;
        let mut initial_liquidity: Option<u64> = None;

        for log in logs {
            let s = log.as_str().unwrap_or("");

            if s.contains("amm_id:") || s.contains("pool_id:") {
                let key = if s.contains("amm_id:") {
                    "amm_id:"
                } else {
                    "pool_id:"
                };
                pool_id = extract_pubkey(s, key);
            }

            if s.contains("base_mint:") || s.contains("coin_mint:") {
                let key = if s.contains("base_mint:") {
                    "base_mint:"
                } else {
                    "coin_mint:"
                };
                base_mint = extract_pubkey(s, key);
            }

            if s.contains("liquidity:") || s.contains("pc_amount:") {
                initial_liquidity = extract_u64(s, "liquidity:")
                    .or_else(|| extract_u64(s, "pc_amount:"));
            }
        }

        let mint = base_mint?;
        let pool = pool_id.unwrap_or(mint);

        Some(TokenEvent::new_raydium(
            mint,
            pool,
            signature.to_string(),
            initial_liquidity,
        ))
    }
}

// ── Yordamchi funksiyalar ──────────────────────────────────────────────────

fn extract_pubkey(s: &str, key: &str) -> Option<Pubkey> {
    s.find(key).and_then(|i| {
        let rest = &s[i + key.len()..];
        let addr = rest
            .split_whitespace()
            .next()?
            .trim_matches(',')
            .trim_matches('"');
        Pubkey::from_str(addr).ok()
    })
}

fn extract_u64(s: &str, key: &str) -> Option<u64> {
    s.find(key).and_then(|i| {
        let rest = &s[i + key.len()..];
        let num_str = rest
            .split_whitespace()
            .next()?
            .trim_matches(',')
            .trim_matches('"');
        num_str.parse::<u64>().ok()
    })
}
    }

use crate::config::Config;
use anyhow::Result;
use tokio::sync::mpsc;
use tracing::{error, info};

pub use types::TokenEvent;

/// Monitor barcha kanallarni boshqaradi va TokenEvent larni yuboradi
pub struct Monitor {
    config: Config,
}

impl Monitor {
    pub fn new(config: Config) -> Self {
        Self { config }
    }

    /// Monitoring ni ishga tushirish (Pump.fun + Raydium parallel)
    pub async fn run(&self, event_tx: mpsc::Sender<TokenEvent>) -> Result<()> {
        info!("🔭 Monitor ishga tushmoqda...");

        let pump_tx = event_tx.clone();
        let raydium_tx = event_tx.clone();
        let pump_config = self.config.clone();
        let raydium_config = self.config.clone();

        // Pump.fun va Raydium monitoringini parallel ishlatish
        let pump_handle = pump_fun::PumpFunMonitor::new(pump_config);
        let raydium_handle = raydium::RaydiumMonitor::new(raydium_config);

        tokio::select! {
            result = pump_handle.run(pump_tx) => {
                if let Err(e) = result {
                    error!("❌ Pump.fun monitor xatosi: {e}");
                }
            }
            result = raydium_handle.run(raydium_tx) => {
                if let Err(e) = result {
                    error!("❌ Raydium monitor xatosi: {e}");
                }
            }
        }

        Ok(())
    }
}
}
mod analyzer {
    pub mod types {
use solana_sdk::pubkey::Pubkey;

/// Token haqida asosiy ma'lumot
#[derive(Debug, Clone, serde::Serialize)]
pub struct TokenInfo {
    pub mint: Pubkey,
    pub supply: u64,
    pub decimals: u8,
}

/// Risk darajasi
#[derive(Debug, Clone, PartialEq, serde::Serialize)]
pub enum RiskLevel {
    Low,
    Medium,
    High,
}

/// Tahlil natijasi
#[derive(Debug, Clone, serde::Serialize)]
pub struct AnalysisResult {
    pub approved: bool,
    pub reject_reason: Option<String>,
    pub token_info: Option<TokenInfo>,
    pub liquidity_lamports: u64,
    pub risk_level: RiskLevel,
}

impl AnalysisResult {
    pub fn approved(info: TokenInfo, liquidity: u64, risk: RiskLevel) -> Self {
        Self {
            approved: true,
            reject_reason: None,
            token_info: Some(info),
            liquidity_lamports: liquidity,
            risk_level: risk,
        }
    }

    pub fn rejected(reason: &str) -> Self {
        Self {
            approved: false,
            reject_reason: Some(reason.to_string()),
            token_info: None,
            liquidity_lamports: 0,
            risk_level: RiskLevel::High,
        }
    }
}
    }
    pub mod filters {
/// Filterlash yordamchi funksiyalari

/// Token honesty tekshirish
pub fn is_suspicious_name(name: &str) -> bool {
    let suspicious = ["rug", "scam", "fake", "test", "xxx", "ponzi"];
    let lower = name.to_lowercase();
    suspicious.iter().any(|s| lower.contains(s))
}

/// Supply mantiqiy diapazonda ekanligini tekshirish
pub fn is_valid_supply(supply: u64, decimals: u8) -> bool {
    let adjusted = supply as f64 / 10f64.powi(decimals as i32);
    // 1M dan 1 trillion orasida bo'lishi kerak
    adjusted >= 1_000_000.0 && adjusted <= 1_000_000_000_000.0
}
    }

use crate::config::Config;
use crate::monitor::TokenEvent;
use anyhow::Result;
use solana_client::nonblocking::rpc_client::RpcClient;
use solana_sdk::pubkey::Pubkey;
use std::sync::Arc;
use std::time::Duration;
use tokio::time::timeout;
use tracing::{debug, info, warn};

pub use types::{AnalysisResult, RiskLevel, TokenInfo};

/// Token analizator - likvidlik, risk, filter
pub struct Analyzer {
    config: Config,
    rpc: Arc<RpcClient>,
}

impl Analyzer {
    pub fn new(config: Config) -> Self {
        let rpc = Arc::new(RpcClient::new_with_timeout(
            config.rpc_https.clone(),
            Duration::from_secs(10),
        ));
        Self { config, rpc }
    }

    /// Tokenni to'liq tahlil qilish
    pub async fn analyze(&self, event: &TokenEvent) -> Result<AnalysisResult> {
        let timeout_ms = self.config.analysis_timeout_ms;

        let result = timeout(
            Duration::from_millis(timeout_ms),
            self.perform_analysis(event),
        )
        .await;

        match result {
            Ok(Ok(analysis)) => Ok(analysis),
            Ok(Err(e)) => {
                warn!("Tahlil xatosi: {e}");
                Ok(AnalysisResult::rejected("Tahlil xatosi"))
            }
            Err(_) => {
                warn!("Tahlil vaqt chegarasi ({timeout_ms}ms) tugadi");
                Ok(AnalysisResult::rejected("Timeout"))
            }
        }
    }

    async fn perform_analysis(&self, event: &TokenEvent) -> Result<AnalysisResult> {
        debug!("🔍 Tahlil boshlanmoqda: {}", event.mint);

        // Token info olish
        let token_info = self.fetch_token_info(&event.mint).await?;
        debug!("Token supply: {}", token_info.supply);

        // Likvidlik hisoblash
        let liquidity = self.calculate_liquidity(event, &token_info).await?;
        debug!("Likvidlik: {liquidity} lamports");

        // Minimal likvidlik filteri
        if liquidity < self.config.min_liquidity_lamports() {
            info!(
                "❌ Kam likvidlik: {} < {} SOL",
                lamports_to_sol(liquidity),
                self.config.min_liquidity_sol
            );
            return Ok(AnalysisResult::rejected("Kam likvidlik"));
        }

        // Shubhali faoliyatni aniqlash (sniper/rug check)
        let risk = self.assess_risk(event, &token_info, liquidity).await;
        info!("Risk darajasi: {:?}", risk);

        if matches!(risk, RiskLevel::High) {
            return Ok(AnalysisResult::rejected("Yuqori risk"));
        }

        // Slippage hisoblash
        let estimated_slippage = self.estimate_slippage(liquidity, self.config.max_position_lamports());
        if estimated_slippage > self.config.slippage_bps as f64 {
            info!(
                "❌ Slippage juda baland: {:.1}% > {}%",
                estimated_slippage / 100.0,
                self.config.slippage_bps / 100
            );
            return Ok(AnalysisResult::rejected("Slippage juda baland"));
        }

        info!(
            "✅ Token qabul qilindi: {} | likvidlik: {:.3} SOL | slippage: {:.1}%",
            event.mint,
            lamports_to_sol(liquidity),
            estimated_slippage / 100.0
        );

        Ok(AnalysisResult::approved(token_info, liquidity, risk))
    }

    /// Token supply va mint ma'lumotlarini olish
    async fn fetch_token_info(&self, mint: &Pubkey) -> Result<TokenInfo> {
        let supply = self.rpc.get_token_supply(mint).await;

        match supply {
            Ok(ui_amount) => Ok(TokenInfo {
                mint: *mint,
                supply: ui_amount.amount.parse::<u64>().unwrap_or(0),
                decimals: ui_amount.decimals,
            }),
            Err(e) => {
                debug!("Token supply olib bo'lmadi: {e}, default ishlatilmoqda");
                Ok(TokenInfo {
                    mint: *mint,
                    supply: 1_000_000_000_000_000, // 1 billion default
                    decimals: 6,
                })
            }
        }
    }

    /// Likvidlik hisoblash
    async fn calculate_liquidity(&self, event: &TokenEvent, _info: &TokenInfo) -> Result<u64> {
        // Agar ma'lum bo'lsa, eventdagi likvidlikni ishlatish
        if let Some(liq) = event.initial_liquidity {
            return Ok(liq);
        }

        // Pump.fun bonding curve dan likvidlik olish
        if let Some(curve) = &event.bonding_curve {
            if let Ok(account) = self.rpc.get_account(curve).await {
                // Bonding curve accountdan SOL miqdorini chiqarish
                // Haqiqiy Pump.fun struct: [discriminator 8 bytes][virtual_token_reserves 8][virtual_sol_reserves 8]...
                if account.data.len() >= 24 {
                    let sol_reserves = u64::from_le_bytes(
                        account.data[16..24].try_into().unwrap_or([0u8; 8]),
                    );
                    return Ok(sol_reserves);
                }
                return Ok(account.lamports);
            }
        }

        // Pool dan likvidlik olish
        if let Some(pool) = &event.pool_id {
            if let Ok(account) = self.rpc.get_account(pool).await {
                return Ok(account.lamports);
            }
        }

        Ok(0)
    }

    /// Risk baholash
    async fn assess_risk(
        &self,
        event: &TokenEvent,
        info: &TokenInfo,
        liquidity: u64,
    ) -> RiskLevel {
        let mut risk_score = 0u32;

        // Juda past supply - shubhali
        if info.supply < 1_000_000 {
            risk_score += 2;
        }

        // Juda kam likvidlik
        if liquidity < 500_000_000 {
            // < 0.5 SOL
            risk_score += 2;
        }

        // Tez yaratilgan tokenlar
        if event.age_ms() < 100 {
            risk_score += 1;
        }

        // Ism yoki symbol yo'q
        if event.name.is_none() && event.symbol.is_none() {
            risk_score += 1;
        }

        match risk_score {
            0..=1 => RiskLevel::Low,
            2..=3 => RiskLevel::Medium,
            _ => RiskLevel::High,
        }
    }

    /// Slippage taxmin qilish (basis points da)
    fn estimate_slippage(&self, liquidity: u64, trade_size: u64) -> f64 {
        if liquidity == 0 {
            return 10_000.0; // 100%
        }
        // Oddiy AMM formula: slippage ≈ trade_size / (liquidity + trade_size)
        let ratio = trade_size as f64 / (liquidity + trade_size) as f64;
        ratio * 10_000.0 // basis points da
    }
}

// ── Yordamchi ──────────────────────────────────────────────────────────────

fn lamports_to_sol(lamports: u64) -> f64 {
    lamports as f64 / 1_000_000_000.0
}
}
mod strategy {
    pub mod position {
use super::ExitReason;
use chrono::{DateTime, Utc};
use solana_sdk::pubkey::Pubkey;

/// Pozitsiya holati
#[derive(Debug, Clone, PartialEq, serde::Serialize)]
pub enum PositionStatus {
    Open,
    Closing,
    Closed,
}

/// Bitta savdo pozitsiyasi
#[derive(Debug, Clone, serde::Serialize)]
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
    }

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
}
mod executor {
    pub mod instructions {
/// Umumiy instruction yordamchilari
use anyhow::Result;
use solana_sdk::{
    instruction::Instruction,
    pubkey::Pubkey,
    system_instruction,
};
use spl_associated_token_account::{
    get_associated_token_address,
    instruction::create_associated_token_account,
};
use spl_token;

/// Associated Token Account mavjud emasligini tekshirib, kerak bo'lsa yaratish
pub fn create_ata_if_needed_ix(
    payer: &Pubkey,
    owner: &Pubkey,
    mint: &Pubkey,
) -> Instruction {
    create_associated_token_account(payer, owner, mint, &spl_token::id())
}

/// WSOL account yaratish (SOL → WSOL wrap qilish)
pub fn wrap_sol_instructions(
    payer: &Pubkey,
    amount_lamports: u64,
) -> Vec<Instruction> {
    let wsol_mint = spl_token::native_mint::id();
    let wsol_ata = get_associated_token_address(payer, &wsol_mint);

    vec![
        // ATA yaratish
        create_associated_token_account(payer, payer, &wsol_mint, &spl_token::id()),
        // SOL o'tkazish
        system_instruction::transfer(payer, &wsol_ata, amount_lamports),
        // Sync native
        spl_token::instruction::sync_native(&spl_token::id(), &wsol_ata).unwrap(),
    ]
}
    }
    pub mod pump_fun_ix {
/// Pump.fun BUY/SELL instructionlarini qo'lda yasash
/// Pump.fun ABI: https://github.com/nicholasgasior/pump-fun-bot
use anyhow::Result;
use borsh::BorshSerialize;
use solana_sdk::{
    instruction::{AccountMeta, Instruction},
    pubkey::Pubkey,
    system_program,
};
use spl_associated_token_account::get_associated_token_address;
use spl_token;
use std::str::FromStr;

// Pump.fun sabit adreslar
const PUMP_FUN_FEE_RECIPIENT: &str = "CebN5WGQ4jvEPvsVU4EoHEpgzq1VV7AbicfhtW4xC9iM";
const PUMP_FUN_GLOBAL: &str = "4wTV1YmiEkRvAtNtsSGPtUrqRYQMe5zP9QkouqzdC6k";
const PUMP_FUN_EVENT_AUTHORITY: &str = "Ce6TQqeHC9p8KetsN6JsjHK7UTZk7nasjjnr7XxXp9F1";

/// Pump.fun BUY instruction discriminator (Anchor borsh 8-bytes)
const BUY_DISCRIMINATOR: [u8; 8] = [102, 6, 61, 18, 1, 218, 235, 234];

/// Pump.fun SELL instruction discriminator
const SELL_DISCRIMINATOR: [u8; 8] = [51, 230, 133, 164, 1, 127, 131, 173];

#[derive(BorshSerialize)]
struct BuyArgs {
    amount: u64,            // Token miqdori (min_tokens out)
    max_sol_cost: u64,      // Maksimal SOL narxi (slippage bilan)
}

#[derive(BorshSerialize)]
struct SellArgs {
    amount: u64,            // Token miqdori
    min_sol_output: u64,    // Minimal SOL chiqishi (slippage bilan)
}

/// Pump.fun BUY instructionini yasash
pub fn build_buy_instruction(
    buyer: &Pubkey,
    mint: &Pubkey,
    bonding_curve: &Pubkey,
    sol_amount: u64,
    slippage_bps: u16,
    program_id_str: &str,
) -> Result<Instruction> {
    let program_id = Pubkey::from_str(program_id_str)?;
    let global = Pubkey::from_str(PUMP_FUN_GLOBAL)?;
    let fee_recipient = Pubkey::from_str(PUMP_FUN_FEE_RECIPIENT)?;
    let event_authority = Pubkey::from_str(PUMP_FUN_EVENT_AUTHORITY)?;

    // Associated token account (buyer tokenlar uchun)
    let buyer_ata = get_associated_token_address(buyer, mint);

    // Bonding curve token account
    let bonding_curve_ata = get_associated_token_address(bonding_curve, mint);

    // Slippage bilan maksimal SOL narxini hisoblash
    let max_sol = apply_slippage_up(sol_amount, slippage_bps);

    // Minimal token output (taxmin: 0 ya'ni nomi cheklovsiz)
    let min_tokens: u64 = 1;

    let args = BuyArgs {
        amount: min_tokens,
        max_sol_cost: max_sol,
    };

    // Instruction data = discriminator + borsh-encoded args
    let mut data = BUY_DISCRIMINATOR.to_vec();
    data.extend(borsh::to_vec(&args)?);

    let accounts = vec![
        AccountMeta::new_readonly(global, false),
        AccountMeta::new(fee_recipient, false),
        AccountMeta::new_readonly(*mint, false),
        AccountMeta::new(*bonding_curve, false),
        AccountMeta::new(bonding_curve_ata, false),
        AccountMeta::new(buyer_ata, false),
        AccountMeta::new(*buyer, true),
        AccountMeta::new_readonly(system_program::id(), false),
        AccountMeta::new_readonly(spl_token::id(), false),
        AccountMeta::new_readonly(spl_associated_token_account::id(), false),
        AccountMeta::new_readonly(event_authority, false),
        AccountMeta::new_readonly(program_id, false),
    ];

    Ok(Instruction {
        program_id,
        accounts,
        data,
    })
}

/// Pump.fun SELL instructionini yasash
pub fn build_sell_instruction(
    seller: &Pubkey,
    mint: &Pubkey,
    bonding_curve: &Pubkey,
    token_amount: u64,
    slippage_bps: u16,
    program_id_str: &str,
) -> Result<Instruction> {
    let program_id = Pubkey::from_str(program_id_str)?;
    let global = Pubkey::from_str(PUMP_FUN_GLOBAL)?;
    let fee_recipient = Pubkey::from_str(PUMP_FUN_FEE_RECIPIENT)?;
    let event_authority = Pubkey::from_str(PUMP_FUN_EVENT_AUTHORITY)?;

    let seller_ata = get_associated_token_address(seller, mint);
    let bonding_curve_ata = get_associated_token_address(bonding_curve, mint);

    // Minimal SOL chiqishi (0 = no minimum - slippage tekshiruvi on-chain)
    let min_sol: u64 = 0;

    let args = SellArgs {
        amount: token_amount,
        min_sol_output: min_sol,
    };

    let mut data = SELL_DISCRIMINATOR.to_vec();
    data.extend(borsh::to_vec(&args)?);

    let accounts = vec![
        AccountMeta::new_readonly(global, false),
        AccountMeta::new(fee_recipient, false),
        AccountMeta::new_readonly(*mint, false),
        AccountMeta::new(*bonding_curve, false),
        AccountMeta::new(bonding_curve_ata, false),
        AccountMeta::new(seller_ata, false),
        AccountMeta::new_readonly(*seller, true),
        AccountMeta::new_readonly(system_program::id(), false),
        AccountMeta::new_readonly(spl_associated_token_account::id(), false),
        AccountMeta::new_readonly(spl_token::id(), false),
        AccountMeta::new_readonly(event_authority, false),
        AccountMeta::new_readonly(program_id, false),
    ];

    Ok(Instruction {
        program_id,
        accounts,
        data,
    })
}

// ── Yordamchi ──────────────────────────────────────────────────────────────

/// Slippage bilan yuqori tomonga (BUY uchun max_cost)
fn apply_slippage_up(amount: u64, slippage_bps: u16) -> u64 {
    let multiplier = 10_000 + slippage_bps as u64;
    amount.saturating_mul(multiplier) / 10_000
}

/// Slippage bilan quyi tomonga (SELL uchun min_output)
fn apply_slippage_down(amount: u64, slippage_bps: u16) -> u64 {
    let multiplier = 10_000u64.saturating_sub(slippage_bps as u64);
    amount.saturating_mul(multiplier) / 10_000
}
    }
    pub mod raydium_ix {
/// Raydium AMM swap instructionlarini yasash
use anyhow::Result;
use borsh::BorshSerialize;
use solana_sdk::{
    instruction::{AccountMeta, Instruction},
    pubkey::Pubkey,
    system_program,
};
use spl_associated_token_account::get_associated_token_address;
use spl_token;
use std::str::FromStr;

// Raydium AMM sabit manzillar
const RAYDIUM_AUTHORITY: &str = "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1";
const WSOL_MINT: &str = "So11111111111111111111111111111111111111112";

/// Raydium SwapBaseIn discriminator
const SWAP_BASE_IN_DISCRIMINATOR: [u8; 8] = [143, 190, 90, 218, 196, 30, 51, 222];

/// Raydium SwapBaseOut discriminator
const SWAP_BASE_OUT_DISCRIMINATOR: [u8; 8] = [55, 217, 98, 86, 163, 74, 180, 173];

#[derive(BorshSerialize)]
struct SwapBaseInArgs {
    amount_in: u64,
    minimum_amount_out: u64,
}

#[derive(BorshSerialize)]
struct SwapBaseOutArgs {
    max_amount_in: u64,
    amount_out: u64,
}

/// Raydium BUY (SOL → Token) - SwapBaseIn
pub fn build_swap_in_instruction(
    user: &Pubkey,
    token_mint: &Pubkey,
    pool_id: &Pubkey,
    sol_amount_in: u64,
    slippage_bps: u16,
    program_id_str: &str,
) -> Result<Instruction> {
    let program_id = Pubkey::from_str(program_id_str)?;
    let amm_authority = Pubkey::from_str(RAYDIUM_AUTHORITY)?;
    let wsol_mint = Pubkey::from_str(WSOL_MINT)?;

    // Pool tokenlar uchun accountlar (haqiqiy botda pool state dan olinadi)
    let pool_coin_vault = get_associated_token_address(pool_id, &wsol_mint);
    let pool_pc_vault = get_associated_token_address(pool_id, token_mint);
    let user_source = get_associated_token_address(user, &wsol_mint);
    let user_destination = get_associated_token_address(user, token_mint);

    let min_amount_out: u64 = 1; // Haqiqiy botda slippage dan hisoblanadi

    let args = SwapBaseInArgs {
        amount_in: sol_amount_in,
        minimum_amount_out: min_amount_out,
    };

    let mut data = SWAP_BASE_IN_DISCRIMINATOR.to_vec();
    data.extend(borsh::to_vec(&args)?);

    let accounts = vec![
        AccountMeta::new_readonly(spl_token::id(), false),
        AccountMeta::new(*pool_id, false),
        AccountMeta::new_readonly(amm_authority, false),
        AccountMeta::new(*pool_id, false), // open_orders (simplified)
        AccountMeta::new(pool_coin_vault, false),
        AccountMeta::new(pool_pc_vault, false),
        AccountMeta::new(*pool_id, false), // serum_market (simplified)
        AccountMeta::new(*pool_id, false), // serum_bids
        AccountMeta::new(*pool_id, false), // serum_asks
        AccountMeta::new(*pool_id, false), // serum_event_queue
        AccountMeta::new(*pool_id, false), // serum_coin_vault
        AccountMeta::new(*pool_id, false), // serum_pc_vault
        AccountMeta::new_readonly(*pool_id, false), // serum_vault_signer
        AccountMeta::new(user_source, false),
        AccountMeta::new(user_destination, false),
        AccountMeta::new(*user, true),
    ];

    Ok(Instruction {
        program_id,
        accounts,
        data,
    })
}

/// Raydium SELL (Token → SOL) - SwapBaseOut
pub fn build_swap_out_instruction(
    user: &Pubkey,
    token_mint: &Pubkey,
    pool_id: &Pubkey,
    token_amount_out: u64,
    slippage_bps: u16,
    program_id_str: &str,
) -> Result<Instruction> {
    let program_id = Pubkey::from_str(program_id_str)?;
    let amm_authority = Pubkey::from_str(RAYDIUM_AUTHORITY)?;
    let wsol_mint = Pubkey::from_str(WSOL_MINT)?;

    let pool_coin_vault = get_associated_token_address(pool_id, &wsol_mint);
    let pool_pc_vault = get_associated_token_address(pool_id, token_mint);
    let user_source = get_associated_token_address(user, token_mint);
    let user_destination = get_associated_token_address(user, &wsol_mint);

    // Maksimal input (slippage bilan)
    let max_amount_in = apply_slippage_up(token_amount_out, slippage_bps);

    let args = SwapBaseOutArgs {
        max_amount_in,
        amount_out: token_amount_out,
    };

    let mut data = SWAP_BASE_OUT_DISCRIMINATOR.to_vec();
    data.extend(borsh::to_vec(&args)?);

    let accounts = vec![
        AccountMeta::new_readonly(spl_token::id(), false),
        AccountMeta::new(*pool_id, false),
        AccountMeta::new_readonly(amm_authority, false),
        AccountMeta::new(*pool_id, false),
        AccountMeta::new(pool_coin_vault, false),
        AccountMeta::new(pool_pc_vault, false),
        AccountMeta::new(*pool_id, false),
        AccountMeta::new(*pool_id, false),
        AccountMeta::new(*pool_id, false),
        AccountMeta::new(*pool_id, false),
        AccountMeta::new(*pool_id, false),
        AccountMeta::new(*pool_id, false),
        AccountMeta::new_readonly(*pool_id, false),
        AccountMeta::new(user_source, false),
        AccountMeta::new(user_destination, false),
        AccountMeta::new(*user, true),
    ];

    Ok(Instruction {
        program_id,
        accounts,
        data,
    })
}

// ── Yordamchi ──────────────────────────────────────────────────────────────

fn apply_slippage_up(amount: u64, slippage_bps: u16) -> u64 {
    let mult = 10_000 + slippage_bps as u64;
    amount.saturating_mul(mult) / 10_000
}
    }
    pub mod jito {
/// Jito MEV Bundle integratsiyasi
/// Jito orqali bundle yuborish frontrunning dan himoya qiladi va
/// prioritetni oshiradi.
///
/// Docs: https://jito-labs.gitbook.io/mev/searcher-resources/json-rpc-api-reference

use anyhow::{bail, Result};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use solana_sdk::{
    signature::Keypair,
    signer::Signer,
    transaction::Transaction,
    pubkey::Pubkey,
    system_instruction,
};
use std::str::FromStr;
use tracing::{debug, info, warn};

/// Jito tip account lar (MEV bloklari uchun)
const JITO_TIP_ACCOUNTS: &[&str] = &[
    "96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5",
    "HFqU5x63VTqvQss8hp11i4wVV8bD44PvwucfZ2bU7gRe",
    "Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY",
    "ADaUMid9yfUytqMBgopwjb2DTLSokTSzL1zt13X5ta1R",
    "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh",
    "ADuUkR4vqLUMWXxW9gh6D6L8pMSawimctcNZ5pGwDcEt",
    "DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL",
    "3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT",
];

/// Jito tip account ni tasodifiy tanlash (MEV distribusion uchun)
pub fn random_tip_account() -> Pubkey {
    let idx = rand::random::<usize>() % JITO_TIP_ACCOUNTS.len();
    Pubkey::from_str(JITO_TIP_ACCOUNTS[idx]).unwrap()
}

/// Jito tip instruksiyasini yaratish
pub fn create_tip_instruction(
    payer: &Pubkey,
    tip_lamports: u64,
) -> solana_sdk::instruction::Instruction {
    let tip_account = random_tip_account();
    system_instruction::transfer(payer, &tip_account, tip_lamports)
}

#[derive(Debug, Serialize, Deserialize)]
pub struct BundleStatus {
    pub bundle_id: String,
    pub status: String,
    pub landed_slot: Option<u64>,
}

/// Jito bundle sender
pub struct JitoClient {
    client: Client,
    endpoint: String,
    tip_lamports: u64,
}

impl JitoClient {
    pub fn new(endpoint: &str, tip_lamports: u64) -> Self {
        Self {
            client: Client::new(),
            endpoint: endpoint.to_string(),
            tip_lamports,
        }
    }

    /// Bir nechta transactionni bundle sifatida yuborish
    pub async fn send_bundle(&self, transactions: Vec<Transaction>) -> Result<String> {
        if transactions.is_empty() {
            bail!("Bundle bo'sh bo'lishi mumkin emas");
        }

        if transactions.len() > 5 {
            bail!("Bundle maksimal 5 ta transaction (Jito cheklov)");
        }

        // Transactionlarni base58 ga o'girish
        let encoded: Vec<String> = transactions
            .iter()
            .map(|tx| {
                let bytes = bincode::serialize(tx)
                    .map_err(|e| anyhow::anyhow!("Serialize xatosi: {e}"))?;
                Ok(bs58::encode(&bytes).into_string())
            })
            .collect::<Result<Vec<_>>>()?;

        debug!("Bundle yuborilmoqda: {} transaction", encoded.len());

        let request = json!({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sendBundle",
            "params": [encoded]
        });

        let url = format!("{}/api/v1/bundles", self.endpoint);
        let response = self
            .client
            .post(&url)
            .header("Content-Type", "application/json")
            .json(&request)
            .send()
            .await?;

        let status = response.status();
        let body: Value = response.json().await?;

        if !status.is_success() {
            bail!("Jito xatosi {status}: {body}");
        }

        if let Some(error) = body.get("error") {
            bail!("Jito RPC xatosi: {error}");
        }

        let bundle_id = body["result"]
            .as_str()
            .ok_or_else(|| anyhow::anyhow!("Bundle ID olinmadi"))?
            .to_string();

        info!("📦 Jito bundle yuborildi: {bundle_id}");
        Ok(bundle_id)
    }

    /// Bundle holatini tekshirish
    pub async fn get_bundle_status(&self, bundle_id: &str) -> Result<BundleStatus> {
        let request = json!({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBundleStatuses",
            "params": [[bundle_id]]
        });

        let url = format!("{}/api/v1/bundles", self.endpoint);
        let response = self
            .client
            .post(&url)
            .header("Content-Type", "application/json")
            .json(&request)
            .send()
            .await?;

        let body: Value = response.json().await?;

        let context = &body["result"]["value"][0];

        Ok(BundleStatus {
            bundle_id: bundle_id.to_string(),
            status: context["confirmation_status"]
                .as_str()
                .unwrap_or("unknown")
                .to_string(),
            landed_slot: context["slot"].as_u64(),
        })
    }

    /// Bundle tasdiqlanguncha kutish
    pub async fn wait_for_confirmation(
        &self,
        bundle_id: &str,
        timeout_secs: u64,
    ) -> Result<bool> {
        use tokio::time::{sleep, Duration, Instant};

        let deadline = Instant::now() + Duration::from_secs(timeout_secs);

        loop {
            if Instant::now() >= deadline {
                warn!("⏰ Jito bundle tasdiqlash vaqti tugadi: {bundle_id}");
                return Ok(false);
            }

            match self.get_bundle_status(bundle_id).await {
                Ok(status) => {
                    debug!("Bundle holati: {:?}", status.status);
                    match status.status.as_str() {
                        "confirmed" | "finalized" => {
                            info!(
                                "✅ Jito bundle tasdiqlandi (slot: {:?}): {bundle_id}",
                                status.landed_slot
                            );
                            return Ok(true);
                        }
                        "failed" => {
                            warn!("❌ Jito bundle muvaffaqiyatsiz: {bundle_id}");
                            return Ok(false);
                        }
                        _ => {
                            sleep(Duration::from_millis(400)).await;
                        }
                    }
                }
                Err(e) => {
                    debug!("Bundle status xatosi: {e}");
                    sleep(Duration::from_millis(500)).await;
                }
            }
        }
    }

    pub fn tip_lamports(&self) -> u64 {
        self.tip_lamports
    }
}
    }
    pub mod transaction {
use anyhow::{bail, Result};
use solana_client::nonblocking::rpc_client::RpcClient;
use solana_sdk::{
    compute_budget::ComputeBudgetInstruction,
    instruction::Instruction,
    message::Message,
    signature::{Keypair, Signature},
    signer::Signer,
    transaction::Transaction,
};
use std::sync::Arc;
use std::time::Duration;
use tokio::time::sleep;
use tracing::{debug, error, info, warn};

/// Transaction yaratish va yuborish
pub struct TransactionBuilder {
    rpc: Arc<RpcClient>,
    wallet: Arc<Keypair>,
    priority_fee: u64,
}

impl TransactionBuilder {
    pub fn new(rpc: Arc<RpcClient>, wallet: Arc<Keypair>, priority_fee: u64) -> Self {
        Self {
            rpc,
            wallet,
            priority_fee,
        }
    }

    /// Transaction yaratish, sign qilish va retry bilan yuborish
    pub async fn send_with_retry(
        &self,
        mut instructions: Vec<Instruction>,
        max_retries: u32,
    ) -> Result<Signature> {
        // Priority fee qo'shish (agar belgilangan bo'lsa)
        if self.priority_fee > 0 {
            let priority_ix =
                ComputeBudgetInstruction::set_compute_unit_price(self.priority_fee);
            let compute_ix =
                ComputeBudgetInstruction::set_compute_unit_limit(200_000);
            instructions.insert(0, priority_ix);
            instructions.insert(1, compute_ix);
        }

        let mut last_error = None;

        for attempt in 1..=max_retries {
            match self.send_once(&instructions).await {
                Ok(sig) => {
                    info!("📨 Transaction yuborildi (urinish {attempt}): {sig}");
                    return Ok(sig);
                }
                Err(e) => {
                    warn!("⚠️ Transaction xatosi (urinish {attempt}/{max_retries}): {e}");
                    last_error = Some(e);

                    if attempt < max_retries {
                        // Eksponensial kutish
                        let wait_ms = 100 * 2u64.pow(attempt - 1);
                        sleep(Duration::from_millis(wait_ms)).await;
                    }
                }
            }
        }

        bail!(
            "Transaction {max_retries} urinishdan keyin ham muvaffaqiyatsiz: {:?}",
            last_error
        )
    }

    async fn send_once(&self, instructions: &[Instruction]) -> Result<Signature> {
        // Eng so'nggi blockhash olish
        let recent_blockhash = self
            .rpc
            .get_latest_blockhash()
            .await
            .map_err(|e| anyhow::anyhow!("Blockhash xatosi: {e}"))?;

        debug!("Blockhash: {recent_blockhash}");

        // Transaction yaratish
        let message = Message::new(instructions, Some(&self.wallet.pubkey()));
        let mut tx = Transaction::new_unsigned(message);
        tx.sign(&[self.wallet.as_ref()], recent_blockhash);

        // Yuborish
        let sig = self
            .rpc
            .send_transaction(&tx)
            .await
            .map_err(|e| anyhow::anyhow!("Transaction yuborish xatosi: {e}"))?;

        Ok(sig)
    }

    /// Transaction tasdiqlashni kutish
    pub async fn confirm(&self, signature: &Signature, timeout_secs: u64) -> Result<bool> {
        let deadline = std::time::Instant::now() + Duration::from_secs(timeout_secs);

        while std::time::Instant::now() < deadline {
            match self.rpc.get_signature_status(signature).await {
                Ok(Some(Ok(_))) => {
                    info!("✅ Transaction tasdiqlandi: {signature}");
                    return Ok(true);
                }
                Ok(Some(Err(e))) => {
                    error!("❌ Transaction xato bilan tugatildi: {e}");
                    return Ok(false);
                }
                Ok(None) => {
                    debug!("Transaction hali pending...");
                    sleep(Duration::from_millis(500)).await;
                }
                Err(e) => {
                    warn!("Status so'rovida xato: {e}");
                    sleep(Duration::from_millis(1000)).await;
                }
            }
        }

        warn!("Transaction tasdiqlash vaqti tugadi");
        Ok(false)
    }
}
    }

use crate::config::Config;
use crate::monitor::types::TokenSource;
use crate::monitor::TokenEvent;
use anyhow::{bail, Result};
use solana_client::nonblocking::rpc_client::RpcClient;
use solana_sdk::{
    commitment_config::CommitmentConfig,
    pubkey::Pubkey,
    signature::{Keypair, Signature},
    signer::Signer,
};
use std::sync::Arc;
use std::time::Duration;
use tracing::{error, info, warn};

pub use transaction::TransactionBuilder;

/// Transaction executor - BUY/SELL operatsiyalarini bajaradi
pub struct Executor {
    config: Config,
    pub wallet: Arc<Keypair>,
    rpc: Arc<RpcClient>,
}

impl Executor {
    pub fn new(config: Config) -> Result<Self> {
        let wallet = parse_keypair(&config.private_key)?;
        let rpc = Arc::new(RpcClient::new_with_commitment(
            config.rpc_https.clone(),
            CommitmentConfig::processed(),
        ));

        info!("👛 Wallet: {}", wallet.pubkey());

        Ok(Self {
            config,
            wallet: Arc::new(wallet),
            rpc,
        })
    }

    pub fn wallet_pubkey(&self) -> Pubkey {
        self.wallet.pubkey()
    }

    /// BUY operatsiyasini bajarish
    pub async fn buy(
        &self,
        event: &TokenEvent,
        sol_amount: u64,
        slippage_bps: u16,
    ) -> Result<BuyResult> {
        info!(
            "🟢 BUY boshlandi: {} | {:.4} SOL",
            event.mint,
            sol_amount as f64 / 1e9
        );

        let signature = match &event.source {
            TokenSource::PumpFun => {
                self.buy_pump_fun(event, sol_amount, slippage_bps).await?
            }
            TokenSource::Raydium => {
                self.buy_raydium(event, sol_amount, slippage_bps).await?
            }
        };

        info!("✅ BUY muvaffaqiyatli: {}", signature);

        Ok(BuyResult {
            signature,
            sol_spent: sol_amount,
            tokens_received: self.estimate_tokens_received(sol_amount, 0).await,
        })
    }

    /// SELL operatsiyasini bajarish
    pub async fn sell(
        &self,
        event: &TokenEvent,
        token_amount: u64,
        slippage_bps: u16,
    ) -> Result<SellResult> {
        info!(
            "🔴 SELL boshlandi: {} | {} token",
            event.mint, token_amount
        );

        let signature = match &event.source {
            TokenSource::PumpFun => {
                self.sell_pump_fun(event, token_amount, slippage_bps).await?
            }
            TokenSource::Raydium => {
                self.sell_raydium(event, token_amount, slippage_bps).await?
            }
        };

        info!("✅ SELL muvaffaqiyatli: {}", signature);

        Ok(SellResult {
            signature,
            tokens_sold: token_amount,
            sol_received: 0, // Haqiqiy botda event dan olinadi
        })
    }

    // ── Pump.fun ────────────────────────────────────────────────────────────

    async fn buy_pump_fun(
        &self,
        event: &TokenEvent,
        sol_amount: u64,
        slippage_bps: u16,
    ) -> Result<Signature> {
        let bonding_curve = event
            .bonding_curve
            .ok_or_else(|| anyhow::anyhow!("Bonding curve adresi topilmadi"))?;

        let ix = pump_fun_ix::build_buy_instruction(
            &self.wallet.pubkey(),
            &event.mint,
            &bonding_curve,
            sol_amount,
            slippage_bps,
            &self.config.pump_fun_program,
        )?;

        let builder = TransactionBuilder::new(
            self.rpc.clone(),
            self.wallet.clone(),
            self.config.priority_fee_microlamports,
        );

        builder.send_with_retry(vec![ix], 3).await
    }

    async fn sell_pump_fun(
        &self,
        event: &TokenEvent,
        token_amount: u64,
        slippage_bps: u16,
    ) -> Result<Signature> {
        let bonding_curve = event
            .bonding_curve
            .ok_or_else(|| anyhow::anyhow!("Bonding curve adresi topilmadi"))?;

        let ix = pump_fun_ix::build_sell_instruction(
            &self.wallet.pubkey(),
            &event.mint,
            &bonding_curve,
            token_amount,
            slippage_bps,
            &self.config.pump_fun_program,
        )?;

        let builder = TransactionBuilder::new(
            self.rpc.clone(),
            self.wallet.clone(),
            self.config.priority_fee_microlamports,
        );

        builder.send_with_retry(vec![ix], 3).await
    }

    // ── Raydium ─────────────────────────────────────────────────────────────

    async fn buy_raydium(
        &self,
        event: &TokenEvent,
        sol_amount: u64,
        slippage_bps: u16,
    ) -> Result<Signature> {
        let pool_id = event
            .pool_id
            .ok_or_else(|| anyhow::anyhow!("Raydium pool ID topilmadi"))?;

        let ix = raydium_ix::build_swap_in_instruction(
            &self.wallet.pubkey(),
            &event.mint,
            &pool_id,
            sol_amount,
            slippage_bps,
            &self.config.raydium_amm_program,
        )?;

        let builder = TransactionBuilder::new(
            self.rpc.clone(),
            self.wallet.clone(),
            self.config.priority_fee_microlamports,
        );

        builder.send_with_retry(vec![ix], 3).await
    }

    async fn sell_raydium(
        &self,
        event: &TokenEvent,
        token_amount: u64,
        slippage_bps: u16,
    ) -> Result<Signature> {
        let pool_id = event
            .pool_id
            .ok_or_else(|| anyhow::anyhow!("Raydium pool ID topilmadi"))?;

        let ix = raydium_ix::build_swap_out_instruction(
            &self.wallet.pubkey(),
            &event.mint,
            &pool_id,
            token_amount,
            slippage_bps,
            &self.config.raydium_amm_program,
        )?;

        let builder = TransactionBuilder::new(
            self.rpc.clone(),
            self.wallet.clone(),
            self.config.priority_fee_microlamports,
        );

        builder.send_with_retry(vec![ix], 3).await
    }

    /// Taxminiy token miqdori hisoblash
    async fn estimate_tokens_received(&self, sol_amount: u64, reserve: u64) -> u64 {
        if reserve == 0 {
            return sol_amount * 1000; // fallback
        }
        // Simplified estimate for UI purposes
        sol_amount * 1000 // placeholder for now, real calculation is internal to instruction
    }
}

// ── Natija tiplari ──────────────────────────────────────────────────────────

#[derive(Debug)]
pub struct BuyResult {
    pub signature: Signature,
    pub sol_spent: u64,
    pub tokens_received: u64,
}

#[derive(Debug)]
pub struct SellResult {
    pub signature: Signature,
    pub tokens_sold: u64,
    pub sol_received: u64,
}

// ── Yordamchi ──────────────────────────────────────────────────────────────

fn parse_keypair(private_key: &str) -> Result<Keypair> {
    // Base58 formatini tekshirish
    if let Ok(bytes) = bs58::decode(private_key).into_vec() {
        if bytes.len() == 64 {
            return Ok(Keypair::from_bytes(&bytes)
                .map_err(|e| anyhow::anyhow!("Keypair xatosi: {e}"))?);
        }
    }

    // JSON array formatini tekshirish
    if let Ok(bytes) = serde_json::from_str::<Vec<u8>>(private_key) {
        return Ok(Keypair::from_bytes(&bytes)
            .map_err(|e| anyhow::anyhow!("Keypair xatosi: {e}"))?);
    }

    bail!("Private key noto'g'ri format (base58 yoki JSON array kerak)")
}
}
mod price {
/// Real-time narx ma'lumotlarini Pump.fun bonding curve va
/// Raydium AMM pool dan o'qish moduli.

use crate::monitor::types::{TokenEvent, TokenSource};
use anyhow::{bail, Result};
use solana_client::nonblocking::rpc_client::RpcClient;
use solana_sdk::pubkey::Pubkey;
use std::sync::Arc;
use tracing::debug;

/// Narx ma'lumoti
#[derive(Debug, Clone)]
pub struct PriceInfo {
    /// Tokenning SOL da narxi (lamports per token, scaled x10^9)
    pub price_lamports: u64,
    /// Pool / bonding curve dagi SOL zaxirasi
    pub sol_reserve: u64,
    /// Pool / bonding curve dagi token zaxirasi
    pub token_reserve: u64,
    /// Hozirgi market cap (lamports)
    pub market_cap: u64,
}

/// Pump.fun bonding curve account layout (Anchor struct)
/// Offset  Size  Field
/// 0       8     discriminator
/// 8       32    mint
/// 40      32    creator
/// 72      8     virtualTokenReserves
/// 80      8     virtualSolReserves
/// 88      8     realTokenReserves
/// 96      8     realSolReserves
/// 104     8     tokenTotalSupply
/// 112     1     complete (bool)
#[derive(Debug)]
pub struct BondingCurveState {
    pub virtual_token_reserves: u64,
    pub virtual_sol_reserves: u64,
    pub real_token_reserves: u64,
    pub real_sol_reserves: u64,
    pub token_total_supply: u64,
    pub complete: bool,
}

impl BondingCurveState {
    /// Account data dan bonding curve state ni parse qilish
    pub fn from_bytes(data: &[u8]) -> Option<Self> {
        if data.len() < 113 {
            return None;
        }
        Some(Self {
            virtual_token_reserves: u64::from_le_bytes(data[72..80].try_into().ok()?),
            virtual_sol_reserves: u64::from_le_bytes(data[80..88].try_into().ok()?),
            real_token_reserves: u64::from_le_bytes(data[88..96].try_into().ok()?),
            real_sol_reserves: u64::from_le_bytes(data[96..104].try_into().ok()?),
            token_total_supply: u64::from_le_bytes(data[104..112].try_into().ok()?),
            complete: data[112] != 0,
        })
    }

    /// Hozirgi token narxini hisoblash (lamports per token)
    /// Constant product AMM: price = virtualSolReserves / virtualTokenReserves
    pub fn current_price(&self) -> u64 {
        if self.virtual_token_reserves == 0 {
            return 0;
        }
        // 1e9 ni ko'paytirib keyin bo'lamiz (precision uchun)
        (self.virtual_sol_reserves as u128)
            .saturating_mul(1_000_000_000)
            .checked_div(self.virtual_token_reserves as u128)
            .unwrap_or(0) as u64
    }

    /// Market cap hisoblash
    pub fn market_cap(&self) -> u64 {
        let price = self.current_price();
        (price as u128)
            .saturating_mul(self.token_total_supply as u128)
            .checked_div(1_000_000_000)
            .unwrap_or(0) as u64
    }
}

/// Raydium AMM pool state (minimal)
/// Pump.fun dan farqli, Raydium pool state juda katta,
/// bizga faqat coin va pc reserve kerak
#[derive(Debug)]
pub struct RaydiumPoolState {
    pub coin_vault_balance: u64, // Base token (yangi token)
    pub pc_vault_balance: u64,   // Quote token (SOL/USDC)
}

impl RaydiumPoolState {
    pub fn current_price(&self) -> u64 {
        if self.coin_vault_balance == 0 {
            return 0;
        }
        (self.pc_vault_balance as u128)
            .saturating_mul(1_000_000_000)
            .checked_div(self.coin_vault_balance as u128)
            .unwrap_or(0) as u64
    }
}

/// Narx ma'lumotlarini olish servisi
pub struct PriceFetcher {
    rpc: Arc<RpcClient>,
}

impl PriceFetcher {
    pub fn new(rpc: Arc<RpcClient>) -> Self {
        Self { rpc }
    }

    /// Tokenning hozirgi narxini olish
    pub async fn get_price(&self, event: &TokenEvent) -> Result<PriceInfo> {
        match event.source {
            TokenSource::PumpFun => self.get_pump_fun_price(event).await,
            TokenSource::Raydium => self.get_raydium_price(event).await,
        }
    }

    /// Pump.fun bonding curve dan narx olish
    pub async fn get_pump_fun_price(&self, event: &TokenEvent) -> Result<PriceInfo> {
        let curve_addr = event
            .bonding_curve
            .ok_or_else(|| anyhow::anyhow!("Bonding curve adresi yo'q"))?;

        let account = self.rpc.get_account(&curve_addr).await?;

        let state = BondingCurveState::from_bytes(&account.data)
            .ok_or_else(|| anyhow::anyhow!("Bonding curve parse xatosi"))?;

        debug!(
            "BondingCurve: vSol={} vToken={} price={}",
            state.virtual_sol_reserves,
            state.virtual_token_reserves,
            state.current_price()
        );

        Ok(PriceInfo {
            price_lamports: state.current_price(),
            sol_reserve: state.virtual_sol_reserves,
            token_reserve: state.virtual_token_reserves,
            market_cap: state.market_cap(),
        })
    }

    /// Raydium pool vault balancelaridan narx olish
    pub async fn get_raydium_price(&self, event: &TokenEvent) -> Result<PriceInfo> {
        let pool_id = event
            .pool_id
            .ok_or_else(|| anyhow::anyhow!("Pool ID yo'q"))?;

        let pool_account = self.rpc.get_account(&pool_id).await?;
        if pool_account.data.len() < 752 { // AmmV4 size
            bail!("Raydium pool data juda qisqa");
        }

        // AmmV4 offsets: coinVault at 336, pcVault at 368
        let coin_vault = Pubkey::new_from_array(pool_account.data[336..368].try_into()?);
        let pc_vault = Pubkey::new_from_array(pool_account.data[368..400].try_into()?);

        let coin_balance = self.rpc.get_token_account_balance(&coin_vault).await?;
        let pc_balance = self.rpc.get_token_account_balance(&pc_vault).await?;

        let coin_reserve = coin_balance.amount.parse::<u64>().unwrap_or(0);
        let pc_reserve = pc_balance.amount.parse::<u64>().unwrap_or(0);

        let price = if coin_reserve > 0 {
            (pc_reserve as u128)
                .saturating_mul(1_000_000_000)
                .checked_div(coin_reserve as u128)
                .unwrap_or(0) as u64
        } else {
            0
        };

        Ok(PriceInfo {
            price_lamports: price,
            sol_reserve: pc_reserve,
            token_reserve: coin_reserve,
            market_cap: 0, // Simplified
        })
    }
}
}
mod stats {
/// Savdo statistikasini kuzatish va chiqarish

use chrono::{DateTime, Utc};
use parking_lot::RwLock;
use std::sync::Arc;
use tracing::info;

#[derive(Debug, Default, Clone, serde::Serialize)]
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

#[derive(Debug, Default, Clone, serde::Serialize)]
pub struct StatsInner {
    pub tokens_detected: u64,
    pub tokens_analyzed: u64,
    pub tokens_rejected: u64,
    pub buys_attempted: u64,
    pub buys_succeeded: u64,
    pub sells_attempted: u64,
    pub sells_succeeded: u64,
    pub total_sol_spent: u64,
    pub total_sol_received: u64,
    pub trades: Vec<TradeRecord>,
    pub start_time: Option<DateTime<Utc>>,
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

    pub fn get_data(&self) -> StatsInner {
        let s = self.inner.read();
        s.clone()
    }
}
}

mod dashboard {
    use crate::stats::Stats;
    use crate::strategy::Strategy;
    use crate::config::Config;
    use axum::{extract::State, routing::get, Json, Router};
    use serde::Serialize;
    use std::sync::Arc;
    use tower_http::cors::CorsLayer;
    use tracing::info;

    #[derive(Clone)]
    pub struct AppState {
        pub stats: Arc<Stats>,
        pub strategy: Arc<Strategy>,
        pub config: Config,
    }

    #[derive(Serialize)]
    pub struct DashboardStatus {
        pub stats: crate::stats::StatsInner,
        pub positions: Vec<crate::strategy::Position>,
    }

    pub async fn run_server(state: AppState) {
        let port = state.config.dashboard_port;
        let addr = format!("0.0.0.0:{}", port);

        let app = Router::new()
            .route("/api/status", get(get_status))
            .layer(CorsLayer::permissive())
            .with_state(state);

        info!("🚀 Dashboard API: http://localhost:{}", port);
        let listener = tokio::net::TcpListener::bind(&addr).await.unwrap();
        axum::serve(listener, app).await.unwrap();
    }

    async fn get_status(State(state): State<AppState>) -> Json<DashboardStatus> {
        let stats = state.stats.get_data();
        let positions = state.strategy.positions()
            .iter()
            .map(|entry| entry.value().clone())
            .collect();

        Json(DashboardStatus { stats, positions })
    }
}

mod notifier {
    use crate::config::Config;
    use crate::monitor::TokenEvent;
    use crate::strategy::ExitReason;
    use teloxide::prelude::*;
    use tracing::{error, info};

    pub async fn send_signal(config: &Config, event: &TokenEvent) {
        if let (Some(token), Some(chat_id)) = (&config.telegram_token, &config.telegram_chat_id) {
            let bot = Bot::new(token);
            let message = format!(
                "🎯 *YANGI SIGNAL*\n\nToken: `{}`\nManba: {:?}\n\n[DEXScreener](https://dexscreener.com/solana/{})",
                event.mint, event.source, event.mint
            );
            
            if let Err(e) = bot.send_message(chat_id.clone(), message).parse_mode(teloxide::types::ParseMode::MarkdownV2).await {
                error!("Telegram signal yuborish xatosi: {e}");
            }
        }
    }

    pub async fn send_exit(config: &Config, mint: &str, pnl: f64, reason: ExitReason) {
        if let (Some(token), Some(chat_id)) = (&config.telegram_token, &config.telegram_chat_id) {
            let bot = Bot::new(token);
            let icon = if pnl >= 0.0 { "🟢" } else { "🔴" };
            let message = format!(
                "{} *SAVDO YOPILDI*\n\nToken: `{}`\nResultat: {:+.2}%\nSabab: {}",
                icon, mint, pnl, reason
            );

            if let Err(e) = bot.send_message(chat_id.clone(), message).parse_mode(teloxide::types::ParseMode::MarkdownV2).await {
                error!("Telegram exit yuborish xatosi: {e}");
            }
        }
    }
}

use analyzer::Analyzer;
use config::Config;
use executor::Executor;
use monitor::{Monitor, TokenEvent};
use price::PriceFetcher;
use stats::{Stats, TradeRecord};
use strategy::{ExitReason, Strategy};

use anyhow::Result;
use chrono::Utc;
use solana_client::nonblocking::rpc_client::RpcClient;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::mpsc;
use tokio::time::{interval, sleep};
use tracing::{error, info, warn, debug};
use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() -> Result<()> {
    setup_logging();
    print_banner();

    let config = Config::load().map_err(|e| {
        eprintln!("❌ Konfiguratsiya xatosi: {e}");
        eprintln!("💡 cp .env.example .env  va keyin to'ldiring");
        e
    })?;

    print_config(&config);

    let rpc = Arc::new(RpcClient::new_with_timeout(
        config.rpc_https.clone(),
        Duration::from_secs(10),
    ));

    let executor     = Arc::new(Executor::new(config.clone())?);
    let strategy     = Arc::new(Strategy::new(config.clone()));
    let analyzer     = Arc::new(Analyzer::new(config.clone()));
    let price_fetch  = Arc::new(PriceFetcher::new(rpc));
    let stats        = Arc::new(Stats::new());
    let monitor      = Monitor::new(config.clone());

    // NEW: Dashboard state and Server
    let dashboard_state = dashboard::AppState {
        stats: stats.clone(),
        strategy: strategy.clone(),
        config: config.clone(),
    };
    tokio::spawn(dashboard::run_server(dashboard_state));

    info!("✅ Barcha komponentlar tayyor | 👛 {}", executor.wallet_pubkey());

    let (event_tx, mut event_rx) = mpsc::channel::<TokenEvent>(2048);

    // Monitor task
    {
        let tx = event_tx.clone();
        tokio::spawn(async move {
            loop {
                if let Err(e) = monitor.run(tx.clone()).await {
                    error!("Monitor xatosi: {e}");
                    sleep(Duration::from_secs(3)).await;
                }
            }
        });
    }

    // Statistika (har 5 daqiqada)
    {
        let s = stats.clone();
        tokio::spawn(async move {
            let mut t = interval(Duration::from_secs(300));
            loop { t.tick().await; s.print_summary(); }
        });
    }

    // Muddati o'tgan pozitsiyalar skaneri (har 10 soniya)
    {
        let strategy_r = strategy.clone();
        let stats_r    = stats.clone();
        tokio::spawn(async move {
            let mut t = interval(Duration::from_secs(10));
            loop {
                t.tick().await;
                for mint in strategy_r.get_expired_positions() {
                    warn!("⏰ Muddati tugadi, yopilmoqda: {mint}");
                    strategy_r.close_position(&mint, 0);
                    stats_r.sell_attempted();
                }
            }
        });
    }

    info!("🚀 Bot ishga tushdi! Yangi tokenlar kutilmoqda...\n");

    while let Some(event) = event_rx.recv().await {
        stats.token_detected();

        let (cfg, ana, str, exe, pf, st) = (
            config.clone(), analyzer.clone(), strategy.clone(),
            executor.clone(), price_fetch.clone(), stats.clone(),
        );

        tokio::spawn(async move {
            if let Err(e) = process_event(event, cfg.clone(), ana, str, exe, pf, st).await {
                error!("Event xatosi: {e}");
            }
        });
    }

    Ok(())
}

async fn process_event(
    event: TokenEvent,
    config: Config,
    analyzer: Arc<Analyzer>,
    strategy: Arc<Strategy>,
    executor: Arc<Executor>,
    price_fetcher: Arc<PriceFetcher>,
    stats: Arc<Stats>,
) -> Result<()> {
    info!("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    info!("🔔 {:?} | {} | +{}ms", event.source, event.mint, event.age_ms());

    // 1. TAHLIL
    stats.token_analyzed();
    let analysis = analyzer.analyze(&event).await?;

    if !analysis.approved {
        info!("🚫 Rad etildi [{}]: {}", analysis.reject_reason.as_deref().unwrap_or("-"), event.mint);
        stats.token_rejected();
        return Ok(());
    }

    // 2. STRATEGIYA
    if !strategy.should_buy(&event, &analysis) {
        info!("⏭️  BUY o'tkazildi: {}", event.mint);
        return Ok(());
    }

    // 3. KIRISH NARXI
    let entry_price = match price_fetcher.get_price(&event).await {
        Ok(p) => {
            info!("💱 Kirish narxi: {} lps/token | Pool: {:.3} SOL",
                p.price_lamports, p.sol_reserve as f64 / 1e9);
            p.price_lamports
        }
        Err(e) => { warn!("Narx olish xatosi: {e}"); 0 }
    };

    // 4. BUY
    notifier::send_signal(&config, &event).await;

    stats.buy_attempted();
    let sol_amount = config.max_position_lamports();

    let buy_result = match executor.buy(&event, sol_amount, config.slippage_bps).await {
        Ok(r) => {
            info!("🟢 BUY OK | {} | {:.4} SOL", r.signature, r.sol_spent as f64 / 1e9);
            stats.buy_succeeded(r.sol_spent);
            r
        }
        Err(e) => { error!("❌ BUY xato: {e}"); return Ok(()); }
    };

    // 5. POZITSIYA OCHISH
    strategy.open_position(event.mint, entry_price, buy_result.tokens_received, buy_result.sol_spent);

    // 6. MONITORING + SELL (alohida task)
    let (ev, str2, exe2, pf2, st2, cfg2) = (
        event.clone(), strategy.clone(), executor.clone(),
        price_fetcher.clone(), stats.clone(), config.clone(),
    );
    let (tokens, sol_spent) = (buy_result.tokens_received, buy_result.sol_spent);

    tokio::spawn(async move {
        position_monitor(ev, tokens, sol_spent, entry_price, str2, exe2, pf2, st2, cfg2).await;
    });

    Ok(())
}

#[allow(clippy::too_many_arguments)]
async fn position_monitor(
    event: TokenEvent,
    token_amount: u64,
    sol_spent: u64,
    entry_price: u64,
    strategy: Arc<Strategy>,
    executor: Arc<Executor>,
    price_fetcher: Arc<PriceFetcher>,
    stats: Arc<Stats>,
    config: Config,
) {
    info!("👀 Monitoring: {} | TP={:.0}% SL={:.0}% Max={}s",
        event.mint, config.take_profit_pct, config.stop_loss_pct, config.max_hold_time_secs);

    let mut ticker  = interval(Duration::from_millis(500));
    let deadline    = tokio::time::Instant::now() + Duration::from_secs(config.max_hold_time_secs);

    let exit_reason = loop {
        if tokio::time::Instant::now() >= deadline { break ExitReason::TimeExpired; }

        ticker.tick().await;

        let current_price = match price_fetcher.get_price(&event).await {
            Ok(p) => { debug!("Narx: {} lps", p.price_lamports); p.price_lamports }
            Err(_) => continue,
        };

        if let Some(reason) = strategy.check_exit_signals(&event.mint, current_price) {
            break reason;
        }
    };

    // SELL
    info!("📤 SELL: {} | {}", event.mint, exit_reason);
    stats.sell_attempted();

    let sol_received = match executor.sell(&event, token_amount, config.slippage_bps).await {
        Ok(r) => {
            info!("🔴 SELL OK | {} | {:.4} SOL", r.signature, r.sol_received as f64 / 1e9);
            stats.sell_succeeded(r.sol_received);
            r.sol_received
        }
        Err(e) => {
            error!("❌ SELL xato: {e} — retry...");
            sleep(Duration::from_millis(200)).await;
            match executor.sell(&event, token_amount, config.slippage_bps + 500).await {
                Ok(r) => { stats.sell_succeeded(r.sol_received); r.sol_received }
                Err(e2) => { error!("❌ SELL retry xato: {e2}"); 0 }
            }
        }
    };

    strategy.close_position(&event.mint, sol_received);

    let pnl_pct = if sol_spent > 0 {
        (sol_received as f64 - sol_spent as f64) / sol_spent as f64 * 100.0
    } else { 0.0 };
    let pnl_sol = (sol_received as f64 - sol_spent as f64) / 1e9;
    let icon = if pnl_sol >= 0.0 { "🟢" } else { "🔴" };

    info!("{} PnL: {:+.2}% ({:+.4} SOL) | {}", icon, pnl_pct, pnl_sol, exit_reason);

    notifier::send_exit(&config, &event.mint.to_string(), pnl_pct, exit_reason.clone()).await;

    stats.record_trade(TradeRecord {
        mint: event.mint.to_string(),
        source: format!("{:?}", event.source),
        sol_spent,
        sol_received,
        opened_at: Some(event.detected_at),
        closed_at: Some(Utc::now()),
        exit_reason: exit_reason.to_string(),
        success: sol_received > 0,
    });
}

fn setup_logging() {
    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new("info,solana_client=warn,solana_sdk=warn,reqwest=warn"));
    tracing_subscriber::fmt()
        .with_env_filter(filter)
        .with_target(false)
        .with_ansi(true)
        .compact()
        .init();
}

fn print_banner() {
    println!(r#"
╔═══════════════════════════════════════════════════════════╗
║         SOLANA SNIPER BOT  v0.1.0                        ║
║         Pump.fun + Raydium | Rust + Tokio                ║
╚═══════════════════════════════════════════════════════════╝
"#);
}

fn print_config(c: &Config) {
    info!("⚙️  Konfiguratsiya:");
    info!("   📡 RPC:          {}", c.rpc_https);
    info!("   💸 Slippage:     {}%", c.slippage_bps / 100);
    info!("   💰 Pozitsiya:    {} SOL", c.max_position_sol);
    info!("   📈 TP/SL:        {}% / {}%", c.take_profit_pct, c.stop_loss_pct);
    info!("   ⏱  Max hold:     {}s", c.max_hold_time_secs);
    info!("   ⚡ Priority fee: {} microlamports", c.priority_fee_microlamports);
    if c.jito_tip_lamports > 0 {
        info!("   📦 Jito tip:    {} lamports", c.jito_tip_lamports);
    }
}
