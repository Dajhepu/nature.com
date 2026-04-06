/// Umumiy instruction yordamchilari
use anyhow::Result;
use solana_sdk::{
    instruction::Instruction,
    pubkey::Pubkey,
    system_instruction,
};
use spl_associated_token_account::{
    get_associated_token_address,
    instruction::create_associated_token_account,
};
use spl_token;

/// Associated Token Account mavjud emasligini tekshirib, kerak bo'lsa yaratish
pub fn create_ata_if_needed_ix(
    payer: &Pubkey,
    owner: &Pubkey,
    mint: &Pubkey,
) -> Instruction {
    create_associated_token_account(payer, owner, mint, &spl_token::id())
}

/// WSOL account yaratish (SOL → WSOL wrap qilish)
pub fn wrap_sol_instructions(
    payer: &Pubkey,
    amount_lamports: u64,
) -> Vec<Instruction> {
    let wsol_mint = spl_token::native_mint::id();
    let wsol_ata = get_associated_token_address(payer, &wsol_mint);

    vec![
        // ATA yaratish
        create_associated_token_account(payer, payer, &wsol_mint, &spl_token::id()),
        // SOL o'tkazish
        system_instruction::transfer(payer, &wsol_ata, amount_lamports),
        // Sync native
        spl_token::instruction::sync_native(&spl_token::id(), &wsol_ata).unwrap(),
    ]
}
