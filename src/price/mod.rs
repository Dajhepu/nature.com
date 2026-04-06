/// Real-time narx ma'lumotlarini Pump.fun bonding curve va
/// Raydium AMM pool dan o'qish moduli.

use crate::monitor::types::{TokenEvent, TokenSource};
use anyhow::Result;
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

        // Pool state dan vault adreslarini olamiz
        // To'liq implementatsiyada pool state ni to'liq parse qilish kerak
        // Bu erda pool account balanceni ishlatamiz (soddalashtirilgan)
        let pool_account = self.rpc.get_account(&pool_id).await?;

        // Haqiqiy implementatsiyada:
        // 1. Pool state dan coinVault va pcVault pubkey larni o'qish
        // 2. get_token_account_balance() bilan vault balancelarni olish
        // 3. Narxni hisoblash
        let sol_reserve = pool_account.lamports;
        let token_reserve = 1_000_000_000u64; // placeholder

        let price = if token_reserve > 0 {
            (sol_reserve as u128)
                .saturating_mul(1_000_000_000)
                .checked_div(token_reserve as u128)
                .unwrap_or(0) as u64
        } else {
            0
        };

        Ok(PriceInfo {
            price_lamports: price,
            sol_reserve,
            token_reserve,
            market_cap: 0,
        })
    }
}
