/// Filterlash yordamchi funksiyalari

/// Token honesty tekshirish
pub fn is_suspicious_name(name: &str) -> bool {
    let suspicious = ["rug", "scam", "fake", "test", "xxx", "ponzi"];
    let lower = name.to_lowercase();
    suspicious.iter().any(|s| lower.contains(s))
}

/// Supply mantiqiy diapazonda ekanligini tekshirish
pub fn is_valid_supply(supply: u64, decimals: u8) -> bool {
    let adjusted = supply as f64 / 10f64.powi(decimals as i32);
    // 1M dan 1 trillion orasida bo'lishi kerak
    adjusted >= 1_000_000.0 && adjusted <= 1_000_000_000_000.0
}
