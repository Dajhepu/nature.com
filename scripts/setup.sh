#!/usr/bin/env bash
# ============================================================
# Solana Sniper Bot - Avtomatik o'rnatish skripti
# ============================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()    { echo -e "${GREEN}[✓]${NC} $1"; }
warn()   { echo -e "${YELLOW}[!]${NC} $1"; }
error()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }
info()   { echo -e "${BLUE}[i]${NC} $1"; }

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Solana Sniper Bot - Setup              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── 1. Rust tekshirish ──────────────────────────────────────
info "Rust tekshirilmoqda..."
if command -v rustc &>/dev/null; then
    RUST_VER=$(rustc --version | awk '{print $2}')
    log "Rust topildi: $RUST_VER"

    # Versiya tekshirish (1.82+ kerak)
    MAJOR=$(echo $RUST_VER | cut -d. -f1)
    MINOR=$(echo $RUST_VER | cut -d. -f2)
    if [ "$MAJOR" -lt 1 ] || ([ "$MAJOR" -eq 1 ] && [ "$MINOR" -lt 82 ]); then
        warn "Rust $RUST_VER juda eski. 1.82+ kerak. Yangilanmoqda..."
        rustup update stable
    fi
else
    warn "Rust topilmadi. O'rnatilmoqda..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
    log "Rust o'rnatildi: $(rustc --version)"
fi

# ── 2. .env fayl tekshirish ─────────────────────────────────
info ".env fayli tekshirilmoqda..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        warn ".env fayli yaratildi. Iltimos, .env ni to'ldiring:"
        warn "  nano .env"
    else
        error ".env.example fayli topilmadi!"
    fi
else
    log ".env fayli mavjud"
fi

# PRIVATE_KEY tekshirish
if grep -q "your_base58_private_key_here" .env 2>/dev/null; then
    warn "⚠️  PRIVATE_KEY hali o'rnatilmagan! .env faylini tahrirlang."
fi

# ── 3. Build ────────────────────────────────────────────────
info "Bot build qilinmoqda (release mode)..."
echo ""
cargo build --release
echo ""
log "Build muvaffaqiyatli yakunlandi!"
log "Binary: ./target/release/sniper"

# ── 4. Yakuniy ko'rsatmalar ─────────────────────────────────
echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}  O'rnatish muvaffaqiyatli yakunlandi!  ${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
info "Keyingi qadamlar:"
echo "  1. .env faylini to'ldiring:  nano .env"
echo "  2. Botni ishga tushiring:    ./target/release/sniper"
echo "  3. Log kuzatish:             RUST_LOG=debug ./target/release/sniper"
echo ""
warn "DIQQAT: Avval devnet'da sinab ko'ring!"
warn "  RPC_HTTPS=https://api.devnet.solana.com"
echo ""
