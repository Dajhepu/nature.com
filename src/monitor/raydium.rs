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
