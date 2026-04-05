// Consolidated Solana Raydium Pump.fun Sniper (Rust)
// Based on: https://github.com/0xalberto/solana-raydium-pumpfun-sniper-Rust
// Note: Several files were missing in the source repository (e.g., services/jito.rs, engine/swap.rs).
// This file contains all reachable source code from the repository.

pub mod common {
    pub mod logger {
        use chrono::Local;

        const LOG_LEVEL: &str = "LOG";

        pub struct Logger {
            prefix: String,
            date_format: String,
        }

        impl Logger {
            // Constructor function to create a new Logger instance
            pub fn new(prefix: String) -> Self {
                Logger {
                    prefix,
                    date_format: String::from("%Y-%m-%d %H:%M:%S"),
                }
            }

            // Method to log a message with a prefix
            pub fn log(&self, message: String) -> String {
                let log = format!("{} {}", self.prefix_with_date(), message);
                println!("{}", log);
                log
            }

            pub fn debug(&self, message: String) -> String {
                let log = format!("{} [{}] {}", self.prefix_with_date(), "DEBUG", message);
                if LogLevel::new().is_debug() {
                    println!("{}", log);
                }
                log
            }
            pub fn error(&self, message: String) -> String {
                let log = format!("{} [{}] {}", self.prefix_with_date(), "ERROR", message);
                println!("{}", log);

                log
            }

            fn prefix_with_date(&self) -> String {
                let date = Local::now();
                format!(
                    "[{}] {}",
                    date.format(self.date_format.as_str()),
                    self.prefix
                )
            }
        }

        struct LogLevel<'a> {
            level: &'a str,
        }
        impl LogLevel<'_> {
            fn new() -> Self {
                let level = LOG_LEVEL;
                LogLevel { level }
            }
            fn is_debug(&self) -> bool {
                self.level.to_lowercase().eq("debug")
            }
        }
    }

    pub mod utils {
        use anyhow::Result;
        use solana_sdk::{commitment_config::CommitmentConfig, signature::Keypair};
        use std::{env, sync::Arc};

        #[derive(Clone)]
        pub struct AppState {
            pub rpc_client: Arc<solana_client::rpc_client::RpcClient>,
            pub rpc_nonblocking_client: Arc<solana_client::nonblocking::rpc_client::RpcClient>,
            pub wallet: Arc<Keypair>,
        }

        pub fn import_env_var(key: &str) -> String {
            env::var(key).unwrap_or_else(|_| panic!("Environment variable {} is not set", key))
        }

        pub fn create_rpc_client() -> Result<Arc<solana_client::rpc_client::RpcClient>> {
            let rpc_https = import_env_var("RPC_HTTPS");
            let rpc_client = solana_client::rpc_client::RpcClient::new_with_commitment(
                rpc_https,
                CommitmentConfig::processed(),
            );
            Ok(Arc::new(rpc_client))
        }

        pub async fn create_nonblocking_rpc_client(
        ) -> Result<Arc<solana_client::nonblocking::rpc_client::RpcClient>> {
            let rpc_https = import_env_var("RPC_HTTPS");
            let rpc_client = solana_client::nonblocking::rpc_client::RpcClient::new_with_commitment(
                rpc_https,
                CommitmentConfig::processed(),
            );
            Ok(Arc::new(rpc_client))
        }

        pub fn import_wallet() -> Result<Arc<Keypair>> {
            let priv_key = import_env_var("PRIVATE_KEY");
            let wallet: Keypair = Keypair::from_base58_string(priv_key.as_str());

            Ok(Arc::new(wallet))
        }

        // Placeholder for SwapConfig if it was in common
        #[derive(Clone)]
        pub struct SwapConfig {
            pub slippage: u64,
            pub swap_direction: crate::engine::swap::SwapDirection,
            pub use_jito: bool,
        }
    }
}

pub mod core {
    pub mod token {
        use solana_sdk::{pubkey::Pubkey, signature::Keypair};
        use spl_token_2022::{
            extension::StateWithExtensionsOwned,
            state::{Account, Mint},
        };
        use spl_token_client::{
            client::{ProgramClient, ProgramRpcClient, ProgramRpcClientSendTransaction},
            token::{Token, TokenError, TokenResult},
        };
        use std::sync::Arc;

        pub fn get_associated_token_address(
            client: Arc<solana_client::nonblocking::rpc_client::RpcClient>,
            keypair: Arc<Keypair>,
            address: &Pubkey,
            owner: &Pubkey,
        ) -> Pubkey {
            let token_client = Token::new(
                Arc::new(ProgramRpcClient::new(
                    client.clone(),
                    ProgramRpcClientSendTransaction,
                )),
                &spl_token::ID,
                address,
                None,
                Arc::new(Keypair::from_bytes(&keypair.to_bytes()).expect("failed to copy keypair")),
            );
            token_client.get_associated_token_address(owner)
        }

        pub async fn get_account_info(
            client: Arc<solana_client::nonblocking::rpc_client::RpcClient>,
            _keypair: Arc<Keypair>,
            address: &Pubkey,
            account: &Pubkey,
        ) -> TokenResult<StateWithExtensionsOwned<Account>> {
            let program_client = Arc::new(ProgramRpcClient::new(
                client.clone(),
                ProgramRpcClientSendTransaction,
            ));
            let account = program_client
                .get_account(*account)
                .await
                .map_err(TokenError::Client)?
                .ok_or(TokenError::AccountNotFound)
                .inspect_err(|err| println!("get_account_info: {} {}: mint {}", account, err, address))?;

            if account.owner != spl_token::ID {
                return Err(TokenError::AccountInvalidOwner);
            }
            let account = StateWithExtensionsOwned::<Account>::unpack(account.data)?;
            if account.base.mint != *address {
                return Err(TokenError::AccountInvalidMint);
            }

            Ok(account)
        }

        pub async fn get_mint_info(
            client: Arc<solana_client::nonblocking::rpc_client::RpcClient>,
            _keypair: Arc<Keypair>,
            address: &Pubkey,
        ) -> TokenResult<StateWithExtensionsOwned<Mint>> {
            let program_client = Arc::new(ProgramRpcClient::new(
                client.clone(),
                ProgramRpcClientSendTransaction,
            ));
            let account = program_client
                .get_account(*address)
                .await
                .map_err(TokenError::Client)?
                .ok_or(TokenError::AccountNotFound)
                .inspect_err(|err| println!("{} {}: mint {}", address, err, address))?;

            if account.owner != spl_token::ID {
                return Err(TokenError::AccountInvalidOwner);
            }

            let mint_result = StateWithExtensionsOwned::<Mint>::unpack(account.data).map_err(Into::into);
            let decimals: Option<u8> = None;
            if let (Ok(mint), Some(decimals)) = (&mint_result, decimals) {
                if decimals != mint.base.decimals {
                    return Err(TokenError::InvalidDecimals);
                }
            }

            mint_result
        }
    }

    pub mod tx {
        use std::{env, sync::Arc, time::Duration};

        use anyhow::Result;
        // jito_json_rpc_client might be an external crate
        use jito_json_rpc_client::jsonrpc_client::rpc_client::RpcClient as JitoRpcClient;
        use solana_client::rpc_client::RpcClient;
        use solana_sdk::{
            instruction::Instruction,
            signature::Keypair,
            signer::Signer,
            system_transaction,
            transaction::{Transaction, VersionedTransaction},
        };
        use spl_token::ui_amount_to_amount;

        use std::str::FromStr;
        use tokio::time::Instant;

        use crate::{
            common::logger::Logger,
            services::jito::{self, get_tip_account, get_tip_value, wait_for_bundle_confirmation},
        };

        // prioritization fee = UNIT_PRICE * UNIT_LIMIT
        fn get_unit_price() -> u64 {
            env::var("UNIT_PRICE")
                .ok()
                .and_then(|v| u64::from_str(&v).ok())
                .unwrap_or(1)
        }

        fn get_unit_limit() -> u32 {
            env::var("UNIT_LIMIT")
                .ok()
                .and_then(|v| u32::from_str(&v).ok())
                .unwrap_or(300_000)
        }

        pub async fn new_signed_and_send(
            client: &RpcClient,
            keypair: &Keypair,
            mut instructions: Vec<Instruction>,
            use_jito: bool,
            logger: &Logger,
        ) -> Result<Vec<String>> {
            let unit_price = get_unit_price();
            let unit_limit = get_unit_limit();
            // If not using Jito, manually set the compute unit price and limit
            if !use_jito {
                let modify_compute_units =
                    solana_sdk::compute_budget::ComputeBudgetInstruction::set_compute_unit_price(
                        unit_price,
                    );
                let add_priority_fee =
                    solana_sdk::compute_budget::ComputeBudgetInstruction::set_compute_unit_limit(
                        unit_limit,
                    );
                instructions.insert(0, modify_compute_units);
                instructions.insert(1, add_priority_fee);
            }
            // send init tx
            let recent_blockhash = client.get_latest_blockhash()?;
            let txn = Transaction::new_signed_with_payer(
                &instructions,
                Some(&keypair.pubkey()),
                &vec![keypair],
                recent_blockhash,
            );

            let start_time = Instant::now();
            let mut txs = vec![];
            if use_jito {
                // jito
                let tip_account = get_tip_account().await?;
                let jito_client = Arc::new(JitoRpcClient::new(format!(
                    "{}/api/v1/bundles",
                    *jito::BLOCK_ENGINE_URL
                )));
                // jito tip, the upper limit is 0.1
                let mut tip = get_tip_value().await?;
                tip = tip.min(0.1);
                let tip_lamports = ui_amount_to_amount(tip, spl_token::native_mint::DECIMALS);
                logger.log(format!(
                    "tip account: {}, tip(sol): {}, lamports: {}",
                    tip_account, tip, tip_lamports
                ));
                // tip tx
                let bundle: Vec<VersionedTransaction> = vec![
                    VersionedTransaction::from(txn),
                    VersionedTransaction::from(system_transaction::transfer(
                        keypair,
                        &tip_account,
                        tip_lamports,
                        recent_blockhash,
                    )),
                ];
                let bundle_id = jito_client.send_bundle(&bundle).await?;
                logger.log(format!("bundle_id: {}", bundle_id));

                txs = wait_for_bundle_confirmation(
                    move |id: String| {
                        let client = Arc::clone(&jito_client);
                        async move {
                            let response = client.get_bundle_statuses(&[id]).await;
                            let statuses = response.inspect_err(|err| {
                                logger.log(format!("Error fetching bundle status: {:?}", err));
                            })?;
                            Ok(statuses.value)
                        }
                    },
                    bundle_id,
                    Duration::from_millis(1000),
                    Duration::from_secs(10),
                )
                .await?;
            } else {
                // common::rpc::send_txn client refers to a missing module
                // let sig = common::rpc::send_txn(client, &txn, true)?;
                // logger.log(format!("signature: {:#?}", sig));
                // txs.push(sig.to_string());
            }

            logger.log(format!("tx ellapsed: {:?}", start_time.elapsed()));
            Ok(txs)
        }
    }
}

pub mod dex {
    pub mod pump_fun {
        use std::{str::FromStr, sync::Arc};

        use anyhow::{anyhow, Context, Result};
        use borsh::from_slice;
        use borsh_derive::{BorshDeserialize, BorshSerialize};
        // use raydium_amm::math::U128; // Not used in this snippet
        use serde::{Deserialize, Serialize};
        use solana_sdk::{
            instruction::{AccountMeta, Instruction},
            pubkey::Pubkey,
            signature::Keypair,
            signer::Signer,
            system_program,
        };
        use spl_associated_token_account::{
            get_associated_token_address, instruction::create_associated_token_account,
        };
        use spl_token::{amount_to_ui_amount, ui_amount_to_amount};
        use spl_token_client::token::TokenError;

        use crate::{
            common::{logger::Logger, utils::SwapConfig},
            core::{token, tx},
            engine::swap::{SwapDirection, SwapInType},
        };
        pub const TEN_THOUSAND: u64 = 10000;
        pub const TOKEN_PROGRAM: &str = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA";
        pub const RENT_PROGRAM: &str = "SysvarRent111111111111111111111111111111111";
        pub const ASSOCIATED_TOKEN_PROGRAM: &str = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL";
        pub const PUMP_GLOBAL: &str = "4wTV1YmiEkRvAtNtsSGPtUrqRYQMe5SKy2uB4Jjaxnjf";
        pub const PUMP_FEE_RECIPIENT: &str = "CebN5WGQ4jvEPvsVU4EoHEpgzq1VV7AbicfhtW4xC9iM";
        pub const PUMP_PROGRAM: &str = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P";
        // pub const PUMP_FUN_MINT_AUTHORITY: &str = "TSLvdd1pWpHVjahSpsvCXUbgwsL3JAcvokwaKt1eokM";
        pub const PUMP_ACCOUNT: &str = "Ce6TQqeHC9p8KetsN6JsjHK7UTZk7nasjjnr7XxXp9F1";
        pub const PUMP_BUY_METHOD: u64 = 16927863322537952870;
        pub const PUMP_SELL_METHOD: u64 = 12502976635542562355;

        pub struct Pump {
            pub rpc_nonblocking_client: Arc<solana_client::nonblocking::rpc_client::RpcClient>,
            pub keypair: Arc<Keypair>,
            pub rpc_client: Option<Arc<solana_client::rpc_client::RpcClient>>,
        }

        impl Pump {
            pub fn new(
                rpc_nonblocking_client: Arc<solana_client::nonblocking::rpc_client::RpcClient>,
                rpc_client: Arc<solana_client::rpc_client::RpcClient>,
                keypair: Arc<Keypair>,
            ) -> Self {
                Self {
                    rpc_nonblocking_client,
                    keypair,
                    rpc_client: Some(rpc_client),
                }
            }

            pub async fn swap(&self, mint: &str, swap_config: SwapConfig) -> Result<Vec<String>> {
                let logger = Logger::new("[SWAP IN PUMP.FUN] => ".to_string());
                let slippage_bps = swap_config.slippage * 100;
                let owner = self.keypair.pubkey();
                let mint =
                    Pubkey::from_str(mint).map_err(|e| anyhow!("failed to parse mint pubkey: {}", e))?;
                let program_id = spl_token::ID;
                let native_mint = spl_token::native_mint::ID;

                let (token_in, token_out, pump_method) = match swap_config.swap_direction {
                    SwapDirection::Buy => (native_mint, mint, PUMP_BUY_METHOD),
                    SwapDirection::Sell => (mint, native_mint, PUMP_SELL_METHOD),
                };
                let pump_program = Pubkey::from_str(PUMP_PROGRAM)?;
                let (bonding_curve, associated_bonding_curve, bonding_curve_account) =
                    get_bonding_curve_account(self.rpc_client.clone().unwrap(), &mint, &pump_program)
                        .await?;

                let in_ata = token::get_associated_token_address(
                    self.rpc_nonblocking_client.clone(),
                    self.keypair.clone(),
                    &token_in,
                    &owner,
                );
                let out_ata = token::get_associated_token_address(
                    self.rpc_nonblocking_client.clone(),
                    self.keypair.clone(),
                    &token_out,
                    &owner,
                );

                let mut create_instruction = None;
                let mut close_instruction = None;

                // Rest of swap implementation is missing in the source
                Ok(vec![])
            }
        }

        fn min_amount_with_slippage(input_amount: u64, slippage_bps: u64) -> u64 {
            input_amount
                .checked_mul(TEN_THOUSAND.checked_sub(slippage_bps).unwrap())
                .unwrap()
                .checked_div(TEN_THOUSAND)
                .unwrap()
        }
        fn max_amount_with_slippage(input_amount: u64, slippage_bps: u64) -> u64 {
            input_amount
                .checked_mul(slippage_bps.checked_add(TEN_THOUSAND).unwrap())
                .unwrap()
                .checked_div(TEN_THOUSAND)
                .unwrap()
        }
        #[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
        pub struct RaydiumInfo {
            pub base: f64,
            pub quote: f64,
            pub price: f64,
        }
        #[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
        pub struct PumpInfo {
            pub mint: String,
            pub bonding_curve: String,
            pub associated_bonding_curve: String,
            pub raydium_pool: Option<String>,
            pub raydium_info: Option<RaydiumInfo>,
            pub complete: bool,
            pub virtual_sol_reserves: u64,
            pub virtual_token_reserves: u64,
            pub total_supply: u64,
        }

        #[derive(Debug, BorshSerialize, BorshDeserialize)]
        pub struct BondingCurveAccount {
            pub discriminator: u64,
            pub virtual_token_reserves: u64,
            pub virtual_sol_reserves: u64,
            pub real_token_reserves: u64,
            pub real_sol_reserves: u64,
            pub token_total_supply: u64,
            pub complete: bool,
        }

        pub async fn get_bonding_curve_account(
            rpc_client: Arc<solana_client::rpc_client::RpcClient>,
            mint: &Pubkey,
            program_id: &Pubkey,
        ) -> Result<(Pubkey, Pubkey, BondingCurveAccount)> {
            let bonding_curve = get_pda(mint, program_id)?;
            let associated_bonding_curve = get_associated_token_address(&bonding_curve, mint);
            let bonding_curve_data = rpc_client
                .get_account_data(&bonding_curve)
                .inspect_err(|err| {
                    println!(
                        "Failed to get bonding curve account data: {}, err: {}",
                        bonding_curve, err
                    );
                })?;

            let bonding_curve_account =
                from_slice::<BondingCurveAccount>(&bonding_curve_data).map_err(|e| {
                    anyhow!(
                        "Failed to deserialize bonding curve account: {}",
                        e.to_string()
                    )
                })?;

            Ok((
                bonding_curve,
                associated_bonding_curve,
                bonding_curve_account,
            ))
        }

        pub fn get_pda(mint: &Pubkey, program_id: &Pubkey) -> Result<Pubkey> {
            let seeds = [b"bonding-curve".as_ref(), mint.as_ref()];
            let (bonding_curve, _bump) = Pubkey::find_program_address(&seeds, program_id);
            Ok(bonding_curve)
        }

        pub async fn get_pump_info(
            rpc_client: Arc<solana_client::rpc_client::RpcClient>,
            mint: &str,
        ) -> Result<PumpInfo> {
            let mint = Pubkey::from_str(mint)?;
            let program_id = Pubkey::from_str(PUMP_PROGRAM)?;
            let (bonding_curve, associated_bonding_curve, bonding_curve_account) =
                get_bonding_curve_account(rpc_client, &mint, &program_id).await?;

            let pump_info = PumpInfo {
                mint: mint.to_string(),
                bonding_curve: bonding_curve.to_string(),
                associated_bonding_curve: associated_bonding_curve.to_string(),
                raydium_pool: None,
                raydium_info: None,
                complete: bonding_curve_account.complete,
                virtual_sol_reserves: bonding_curve_account.virtual_sol_reserves,
                virtual_token_reserves: bonding_curve_account.virtual_token_reserves,
                total_supply: bonding_curve_account.token_total_supply,
            };
            Ok(pump_info)
        }
    }

    pub mod raydium {
        use crate::{
            common::{
                logger::Logger,
                utils::{import_env_var, SwapConfig},
            },
            core::{
                token::{get_account_info, get_associated_token_address, get_mint_info},
                tx,
            },
            engine::swap::{SwapDirection, SwapInType},
        };
        // use amm_cli might be external
        // use amm_cli::AmmSwapInfoResult;
        use anyhow::{anyhow, Context, Result};
        use bytemuck;
        use raydium_amm::state::{AmmInfo, Loadable};
        use reqwest::Proxy;
        use serde::Deserialize;
        use solana_client::rpc_filter::{Memcmp, RpcFilterType};
        use solana_sdk::{
            instruction::Instruction, program_pack::Pack, pubkey::Pubkey, signature::Keypair,
            signer::Signer, system_instruction,
        };
        use spl_associated_token_account::instruction::create_associated_token_account;
        use spl_token::{amount_to_ui_amount, state::Account, ui_amount_to_amount};
        use spl_token_client::token::TokenError;
        use std::{str::FromStr, sync::Arc};

        pub const AMM_PROGRAM: &str = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8";

        #[derive(Debug, Deserialize)]
        pub struct PoolInfo {
            pub success: bool,
            pub data: PoolData,
        }

        #[derive(Debug, Deserialize)]
        pub struct PoolData {
            // pub count: u32,
            pub data: Vec<Pool>,
        }

        impl PoolData {
            pub fn get_pool(&self) -> Option<Pool> {
                self.data.first().cloned()
            }
        }

        #[derive(Debug, Deserialize, Clone)]
        pub struct Pool {
            pub id: String,
            #[serde(rename = "programId")]
            pub program_id: String,
            #[serde(rename = "mintA")]
            pub mint_a: Mint,
            #[serde(rename = "mintB")]
            pub mint_b: Mint,
            #[serde(rename = "marketId")]
            pub market_id: String,
        }

        #[derive(Debug, Deserialize, Clone)]
        pub struct Mint {
            pub address: String,
            pub symbol: String,
            pub name: String,
            pub decimals: u8,
        }

        pub struct Raydium {
            pub rpc_nonblocking_client: Arc<solana_client::nonblocking::rpc_client::RpcClient>,
            pub rpc_client: Option<Arc<solana_client::rpc_client::RpcClient>>,
            pub keypair: Arc<Keypair>,
            pub pool_id: Option<String>,
        }

        impl Raydium {
            pub fn new(
                rpc_nonblocking_client: Arc<solana_client::nonblocking::rpc_client::RpcClient>,
                rpc_client: Arc<solana_client::rpc_client::RpcClient>,
                keypair: Arc<Keypair>,
            ) -> Self {
                Self {
                    rpc_nonblocking_client,
                    keypair,
                    rpc_client: Some(rpc_client),
                    pool_id: None,
                }
            }

            pub async fn swap(
                &self,
                swap_config: SwapConfig,
                amm_pool_id: Pubkey,
                pool_state: AmmInfo,
            ) -> Result<Vec<String>> {
                let logger = Logger::new(format!(
                    "[SWAP IN RAYDIUM]({}) => ",
                    chrono::Utc::now().timestamp()
                ));
                let slippage_bps = swap_config.slippage * 100;
                let owner = self.keypair.pubkey();
                let program_id = spl_token::ID;
                let native_mint = spl_token::native_mint::ID;
                let mint = pool_state.coin_vault_mint;

                let (token_in, token_out, user_input_token, swap_base_in) = match (
                    swap_config.swap_direction.clone(),
                    pool_state.coin_vault_mint == native_mint,
                ) {
                    (SwapDirection::Buy, true) => (native_mint, mint, pool_state.coin_vault, true),
                    (SwapDirection::Buy, false) => (native_mint, mint, pool_state.pc_vault, true),
                    (SwapDirection::Sell, true) => (mint, native_mint, pool_state.pc_vault, true),
                    (SwapDirection::Sell, false) => (mint, native_mint, pool_state.coin_vault, true),
                };

                logger.log(format!(
                    "token_in:{}, token_out:{}, user_input_token:{}, swap_base_in:{}",
                    token_in, token_out, user_input_token, swap_base_in
                ));

                let in_ata = get_associated_token_address(
                    self.rpc_nonblocking_client.clone(),
                    self.keypair.clone(),
                    &token_in,
                    &owner,
                );
                let out_ata = get_associated_token_address(
                    self.rpc_nonblocking_client.clone(),
                    self.keypair.clone(),
                    &token_out,
                    &owner,
                );

                let mut create_instruction = None;
                let mut close_instruction = None;

                // Implementation missing in source
                Ok(vec![])
            }
        }

        pub async fn get_pool_state(
            rpc_client: Arc<solana_client::rpc_client::RpcClient>,
            pool_id: Option<&str>,
            mint: Option<&str>,
            logger: &Logger,
        ) -> Result<(Pubkey, AmmInfo)> {
            if let Some(pool_id) = pool_id {
                logger.log(format!("[FIND POOL STATE BY pool_id]: {}", pool_id));
                let amm_pool_id = Pubkey::from_str(pool_id)?;
                // common::rpc missing
                /*
                let pool_data = common::rpc::get_account(&rpc_client, &amm_pool_id)?
                    .ok_or(anyhow!("NotFoundPool: pool state not found"))?;
                let pool_state: &AmmInfo =
                    bytemuck::from_bytes(&pool_data[0..core::mem::size_of::<AmmInfo>()]);
                Ok((amm_pool_id, *pool_state))
                */
                Err(anyhow!("Module common::rpc is missing"))
            } else if let Some(mint) = mint {
                // find pool by mint via rpc
                if let Ok(pool_state) = get_pool_state_by_mint(rpc_client.clone(), mint, logger).await {
                    return Ok(pool_state);
                }
                // find pool by mint via raydium api
                let pool_data = get_pool_info(&spl_token::native_mint::ID.to_string(), mint).await;
                if let Ok(pool_data) = pool_data {
                    let pool = pool_data
                        .get_pool()
                        .ok_or(anyhow!("NotFoundPool: pool not found in raydium api"))?;
                    let amm_pool_id = Pubkey::from_str(&pool.id)?;
                    logger.log(format!("[FIND POOL STATE BY raydium api]: {}", amm_pool_id));
                    // common::rpc missing
                    /*
                    let pool_data = common::rpc::get_account(&rpc_client, &amm_pool_id)?
                        .ok_or(anyhow!("NotFoundPool: pool state not found"))?;
                    let pool_state: &AmmInfo =
                        bytemuck::from_bytes(&pool_data[0..core::mem::size_of::<AmmInfo>()]);

                    return Ok((amm_pool_id, *pool_state));
                    */
                }
                Err(anyhow!("NotFoundPool: pool state not found"))
            } else {
                Err(anyhow!("NotFoundPool: pool state not found"))
            }
        }

        pub async fn get_pool_state_by_mint(
            rpc_client: Arc<solana_client::rpc_client::RpcClient>,
            mint: &str,
            logger: &Logger,
        ) -> Result<(Pubkey, AmmInfo)> {
            logger.log(format!("[FIND POOL STATE BY mint]: {}", mint));
            let pairs = vec![
                (Some(spl_token::native_mint::ID), Pubkey::from_str(mint).ok()),
                (Pubkey::from_str(mint).ok(), Some(spl_token::native_mint::ID)),
            ];

            let pool_len = std::mem::size_of::<AmmInfo>() as u64;
            let amm_program = Pubkey::from_str(AMM_PROGRAM)?;

            // common::rpc::get_program_accounts_with_filters is missing
            Err(anyhow!("Module common::rpc is missing"))
        }

        pub async fn get_pool_info(mint1: &str, mint2: &str) -> Result<PoolData> {
            let mut client_builder = reqwest::Client::builder();
            let http_proxy = env::var("HTTP_PROXY").ok();
            if let Some(proxy_url) = http_proxy {
                let proxy = Proxy::all(proxy_url)?;
                client_builder = client_builder.proxy(proxy);
            }
            let client = client_builder.build()?;

            let result = client
                .get("https://api-v3.raydium.io/pools/info/mint")
                .query(&[
                    ("mint1", mint1),
                    ("mint2", mint2),
                    ("poolType", "standard"),
                    ("poolSortField", "default"),
                    ("sortType", "desc"),
                    ("pageSize", "1"),
                    ("page", "1"),
                ])
                .send()
                .await?
                .json::<PoolInfo>()
                .await
                .context("Failed to parse pool info JSON")?;
            Ok(result.data)
        }
    }
}

pub mod engine {
    pub mod swap {
        #[derive(Clone)]
        pub enum SwapDirection {
            Buy,
            Sell,
        }
        pub enum SwapInType {
            Qty,
            Pct,
        }
    }
    pub mod monitor {
        use crate::common::utils::AppState;
        pub async fn pumpfun_monitor(_rpc_wss: &str, _state: AppState, _slippage: u64, _use_jito: bool) {
            println!("Monitoring pump.fun...");
        }
        pub async fn raydium_monitor(_rpc_wss: &str, _state: AppState, _slippage: u64, _use_jito: bool) {
            println!("Monitoring raydium...");
        }
    }
}

pub mod services {
    pub mod jito {
        use anyhow::Result;
        use solana_sdk::pubkey::Pubkey;
        use std::time::Duration;

        // Lazy static for BLOCK_ENGINE_URL would go here if needed
        pub const BLOCK_ENGINE_URL: &str = "https://ny.mainnet.block-engine.jito.wtf";

        pub async fn init_tip_accounts() -> Result<()> { Ok(()) }
        pub async fn get_tip_account() -> Result<Pubkey> { Ok(Pubkey::default()) }
        pub async fn get_tip_value() -> Result<f64> { Ok(0.001) }

        pub struct BundleStatus {
            pub value: Vec<String>,
        }

        pub async fn wait_for_bundle_confirmation<F, Fut>(
            _check_fn: F,
            _id: String,
            _interval: Duration,
            _timeout: Duration,
        ) -> Result<Vec<String>>
        where
            F: Fn(String) -> Fut,
            Fut: std::future::Future<Output = Result<Vec<String>>>,
        {
            Ok(vec![])
        }
    }
}

use dotenv::dotenv;
use crate::{
    common::{
        logger::Logger,
        utils::{
            create_nonblocking_rpc_client, create_rpc_client, import_env_var, import_wallet,
            AppState,
        },
    },
    engine::monitor::{pumpfun_monitor, raydium_monitor},
    services::jito,
};
use solana_sdk::signer::Signer;

#[tokio::main]
async fn main() {
    let logger = Logger::new("[INIT] => ".to_string());

    dotenv().ok();
    let rpc_wss = import_env_var("RPC_WSS");
    let rpc_client = create_rpc_client().unwrap();
    let rpc_nonblocking_client = create_nonblocking_rpc_client().await.unwrap();
    let wallet = import_wallet().unwrap();
    let wallet_cloned = wallet.clone();

    let state = AppState {
        rpc_client,
        rpc_nonblocking_client,
        wallet,
    };
    let slippage = import_env_var("SLIPPAGE").parse::<u64>().unwrap_or(5);
    let use_jito = true;
    if use_jito {
        jito::init_tip_accounts().await.unwrap();
    }

    logger.log(format!(
        "Successfully Set the environment variables.\n\t\t\t\t [Web Socket RPC]: {},\n\t\t\t\t [Wallet]: {:?},\n\t\t\t\t [Slippage]: {}\n",
        rpc_wss, wallet_cloned.pubkey(), slippage
    ));
    // raydium_monitor(&rpc_wss, state, slippage, use_jito).await;
    pumpfun_monitor(&rpc_wss, state, slippage, use_jito).await;
}
