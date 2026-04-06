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
