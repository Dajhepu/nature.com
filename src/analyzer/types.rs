use solana_sdk::pubkey::Pubkey;

/// Token haqida asosiy ma'lumot
#[derive(Debug, Clone)]
pub struct TokenInfo {
    pub mint: Pubkey,
    pub supply: u64,
    pub decimals: u8,
}

/// Risk darajasi
#[derive(Debug, Clone, PartialEq)]
pub enum RiskLevel {
    Low,
    Medium,
    High,
}

/// Tahlil natijasi
#[derive(Debug, Clone)]
pub struct AnalysisResult {
    pub approved: bool,
    pub reject_reason: Option<String>,
    pub token_info: Option<TokenInfo>,
    pub liquidity_lamports: u64,
    pub risk_level: RiskLevel,
}

impl AnalysisResult {
    pub fn approved(info: TokenInfo, liquidity: u64, risk: RiskLevel) -> Self {
        Self {
            approved: true,
            reject_reason: None,
            token_info: Some(info),
            liquidity_lamports: liquidity,
            risk_level: risk,
        }
    }

    pub fn rejected(reason: &str) -> Self {
        Self {
            approved: false,
            reject_reason: Some(reason.to_string()),
            token_info: None,
            liquidity_lamports: 0,
            risk_level: RiskLevel::High,
        }
    }
}
