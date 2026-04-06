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
