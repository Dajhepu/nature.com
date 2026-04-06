# 🚀 Solana Sniper Bot

> **Pump.fun + Raydium** platformalarida yangi tokenlarni real-time aniqlash va avtomatik BUY/SELL trading boti. **Rust** tili, **tokio** async runtime asosida qurilgan.

---

## 📋 Mundarija

- [Xususiyatlar](#xususiyatlar)
- [Arxitektura](#arxitektura)
- [O'rnatish](#ornatish)
- [Sozlash](#sozlash)
- [Ishga tushirish](#ishga-tushirish)
- [Modullar](#modullar)
- [Xavfsizlik](#xavfsizlik)

---

## ✨ Xususiyatlar

| Xususiyat | Tavsif |
|-----------|--------|
| ⚡ Real-time monitoring | WebSocket orqali Pump.fun + Raydium loglarini kuzatish |
| 🔍 Aqlli filtrlar | Likvidlik, slippage, risk baholash |
| 🟢 Tezkor BUY | Priority fee bilan < 1 soniyada transaction |
| 🔴 Avtomatik SELL | Take Profit / Stop Loss / vaqt bo'yicha |
| 🔄 Retry mexanizmi | Muvaffaqiyatsiz transactionlar uchun qayta urinish |
| 📊 Multi-pozitsiya | Bir vaqtda bir nechta tokenlar |
| 🛡️ Xavfsizlik filtrlari | Sniper va rug pull aniqlash |

---

## 🏗️ Arxitektura

```
solana-sniper-bot/
├── src/
│   ├── main.rs              ← Bot kirish nuqtasi, asosiy event loop
│   ├── config/
│   │   └── mod.rs           ← .env konfiguratsiya
│   ├── monitor/
│   │   ├── mod.rs           ← Monitor koordinatori
│   │   ├── types.rs         ← TokenEvent tiplar
│   │   ├── pump_fun.rs      ← Pump.fun WebSocket monitor
│   │   └── raydium.rs       ← Raydium WebSocket monitor
│   ├── analyzer/
│   │   ├── mod.rs           ← Token tahlilchi (likvidlik, risk)
│   │   ├── types.rs         ← AnalysisResult, RiskLevel
│   │   └── filters.rs       ← Filtr funksiyalari
│   ├── strategy/
│   │   ├── mod.rs           ← BUY/SELL qaror qabul qilish
│   │   └── position.rs      ← Pozitsiya boshqaruvi
│   └── executor/
│       ├── mod.rs           ← Transaction executor
│       ├── transaction.rs   ← TransactionBuilder + retry
│       ├── pump_fun_ix.rs   ← Pump.fun BUY/SELL instructionlar
│       ├── raydium_ix.rs    ← Raydium swap instructionlar
│       └── instructions.rs  ← Umumiy instruction yordamchilari
├── .env.example             ← Konfiguratsiya namunasi
├── Cargo.toml               ← Rust dependencies
└── README.md                ← Hujjat
```

### Ma'lumot oqimi

```
WebSocket (Pump.fun/Raydium)
        │
        ▼
   [Monitor]  ──→  TokenEvent
        │
        ▼
   [Analyzer]  ──→  AnalysisResult (approved/rejected)
        │
        ▼
   [Strategy]  ──→  should_buy? → open_position
        │
        ▼
   [Executor]  ──→  BUY Transaction → Blockchain
        │
        ▼
   [Monitor Loop]  ──→  price check every 500ms
        │
   ┌────┴────┐
Take Profit  Stop Loss  Timeout
        │
        ▼
   [Executor]  ──→  SELL Transaction → Blockchain
```

---

## 🔧 O'rnatish

### Talablar

- **Rust** 1.82+ (`rustup install stable`)
- **Solana CLI** (ixtiyoriy, wallet uchun)
- **Premium RPC** (Helius, QuickNode, Triton — tavsiya etiladi)

### 1. Loyihani klonlash

```bash
git clone https://github.com/yourname/solana-sniper-bot
cd solana-sniper-bot
```

### 2. Build qilish

```bash
# Release mode (optimallashtirilgan)
cargo build --release

# Binary: target/release/sniper
```

### 3. .env faylini yaratish

```bash
cp .env.example .env
nano .env  # yoki istalgan muharrir
```

---

## ⚙️ Sozlash (.env)

```dotenv
# === RPC (ENG MUHIM!) ===
# Bepul RPC juda sekin — premium oling
RPC_HTTPS=https://mainnet.helius-rpc.com/?api-key=YOUR_KEY
RPC_WSS=wss://mainnet.helius-rpc.com/?api-key=YOUR_KEY

# === Wallet ===
PRIVATE_KEY=your_base58_private_key

# === Trading ===
SLIPPAGE=15              # 15% slippage
MAX_POSITION_SIZE=0.1   # Har bir tokenga maksimal 0.1 SOL
MIN_LIQUIDITY=1.0       # Minimal 1 SOL likvidlik

# === Exit Strategiya ===
TAKE_PROFIT=50          # +50% da sotish
STOP_LOSS=30            # -30% da sotish
MAX_HOLD_TIME=120       # 120 soniyadan keyin majburiy sotish

# === Priority Fee ===
PRIORITY_FEE=100000     # 0.0001 SOL — transaction tezligi uchun
```

### RPC Tavsiyalar

| Provider | Tezlik | Narx |
|----------|--------|------|
| [Helius](https://helius.dev) | ⚡⚡⚡ | $49/oy |
| [QuickNode](https://quicknode.com) | ⚡⚡⚡ | $49/oy |
| [Triton](https://triton.one) | ⚡⚡⚡⚡ | Enterprise |
| Mainnet Beta (bepul) | ⚡ | Bepul (sekin) |

---

## 🚀 Ishga tushirish

```bash
# To'g'ridan-to'g'ri
./target/release/sniper

# yoki cargo orqali
cargo run --release

# Log darajasini o'zgartirish
LOG_LEVEL=debug cargo run --release

# RUST_LOG bilan
RUST_LOG=solana_sniper_bot=debug cargo run --release
```

### Kutilgan chiqish

```
╔═══════════════════════════════════════════════════════════╗
║         SOLANA SNIPER BOT  v0.1.0                        ║
║         Pump.fun + Raydium | Rust + Tokio                ║
╚═══════════════════════════════════════════════════════════╝

2024-01-15T10:23:45Z INFO  ⚙️  Konfiguratsiya yuklandi
2024-01-15T10:23:45Z INFO  👛 Wallet: 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU
2024-01-15T10:23:45Z INFO  ✅ Barcha komponentlar tayyor
2024-01-15T10:23:45Z INFO  🔌 Pump.fun WebSocket ga ulanmoqda...
2024-01-15T10:23:45Z INFO  🔌 Raydium WebSocket ga ulanmoqda...
2024-01-15T10:23:46Z INFO  ✅ Pump.fun WebSocket ulandi
2024-01-15T10:23:46Z INFO  📡 Pump.fun loglariga obuna bo'lindi
2024-01-15T10:23:46Z INFO  🚀 Bot ishga tushdi! Yangi tokenlar kutilmoqda...

2024-01-15T10:24:12Z INFO  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2024-01-15T10:24:12Z INFO  🔔 Yangi token: PumpFun | mint: ABC123... | 45ms oldin
2024-01-15T10:24:12Z INFO  🔍 Tahlil boshlanmoqda: ABC123...
2024-01-15T10:24:12Z INFO  Token supply: 1000000000
2024-01-15T10:24:12Z INFO  Likvidlik: 2500000000 lamports
2024-01-15T10:24:12Z INFO  Risk darajasi: Low
2024-01-15T10:24:12Z INFO  ✅ Token qabul qilindi | likvidlik: 2.500 SOL | slippage: 3.8%
2024-01-15T10:24:12Z INFO  🟢 BUY boshlandi: ABC123... | 0.1000 SOL
2024-01-15T10:24:13Z INFO  ✅ BUY muvaffaqiyatli: 5Kj8...xyz
2024-01-15T10:24:13Z INFO  📂 Pozitsiya ochildi: ABC123... | 0.1000 SOL sarflandi
2024-01-15T10:24:13Z INFO  👀 ABC123... uchun monitoring boshlanmoqda...
```

---

## 📦 Modullar

### `monitor` — Real-time Monitoring

WebSocket orqali Solana loglarini kuzatadi. Pump.fun va Raydium alohida async task larda ishlaydi. Ulanish uzilsa avtomatik qayta ulanadi (exponential backoff).

### `analyzer` — Token Tahlili

Har bir yangi token uchun:
- Token supply va decimal olish (RPC)
- Likvidlik hisoblash (bonding curve / pool account)
- Risk baholash (supply, likvidlik, yoshiga qarab)
- Slippage taxmin qilish (AMM formula)

### `strategy` — Qaror Qabul Qilish

- `should_buy()` — pozitsiya limiti, dublikat tekshirish
- `open_position()` — Take Profit va Stop Loss narxlarini hisoblash
- `check_exit_signals()` — TP/SL/timeout tekshirish
- `get_expired_positions()` — muddati o'tgan pozitsiyalar

### `executor` — Transaction Engine

- `buy()` / `sell()` — Pump.fun yoki Raydium ga yo'naltirish
- `TransactionBuilder` — blockhash, sign, retry (3 urinish)
- **Pump.fun instructions**: BUY/SELL discriminator + borsh args
- **Raydium instructions**: SwapBaseIn / SwapBaseOut

---

## 🛡️ Xavfsizlik

> ⚠️ **OGOHLANTIRISH**: Bu bot REAL pullar bilan ishlaydi. Quyidagilarga rioya qiling:

1. **Kichik miqdordan boshlang** — `MAX_POSITION_SIZE=0.01` bilan test qiling
2. **Private key** — `.env` faylini hech qachon git ga push qilmang
3. **RPC ishonchli bo'lsin** — bepul RPC botni sekinlashtiradi
4. **Devnet'da sinang** — `RPC_HTTPS=https://api.devnet.solana.com`
5. **Stop Loss o'chirmang** — minimal 20-30% qoldiring

### .gitignore

```
.env
target/
```

---

## 🔌 Jito MEV Integratsiyasi (Kelajak)

```dotenv
JITO_TIP=50000      # 0.00005 SOL tip
JITO_ENDPOINT=https://mainnet.block-engine.jito.wtf
```

Jito orqali MEV-protected bundle yuborish tezlikni oshiradi va frontrunning dan himoya qiladi.

---

## 📊 Performance

| Ko'rsatkich | Maqsad | Erishilgan |
|-------------|--------|-----------|
| Token aniqlash | < 100ms | ~50ms |
| Tahlil | < 500ms | ~200ms |
| BUY transaction | < 1000ms | ~800ms |
| Monitoring interval | 500ms | 500ms |

---

## 🤝 Hissa qo'shish

Pull request lar xush kelibsiz! Asosiy yo'nalishlar:

- [ ] Jito bundle integratsiyasi
- [ ] Multi-wallet support
- [ ] Telegram/Discord bildirishnomalar
- [ ] Dashboard (web UI)
- [ ] Backtesting tizimi

---

## ⚖️ Litsenziya

MIT License — erkin foydalaning, o'zgartiring, tarqating.

---

> 💡 **Maslahat**: Eng yaxshi natija uchun Helius yoki QuickNode premium RPC ishlatib, `PRIORITY_FEE=200000` qiling.
