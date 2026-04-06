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
