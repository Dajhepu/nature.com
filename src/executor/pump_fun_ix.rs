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
