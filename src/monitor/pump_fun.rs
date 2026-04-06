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
