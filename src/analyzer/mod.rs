pub mod filters;
pub mod types;

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
