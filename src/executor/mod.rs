pub mod instructions;
pub mod pump_fun_ix;
pub mod raydium_ix;
pub mod transaction;

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
    async fn estimate_tokens_received(&self, sol_amount: u64, _reserve: u64) -> u64 {
        // Oddiy taxmin: haqiqiy botda bonding curve dan hisoblanadi
        sol_amount * 1000 // placeholder
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
