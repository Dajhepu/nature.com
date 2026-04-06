.PHONY: build run run-dev clean test check fmt lint devnet mainnet

# ── Build ──────────────────────────────────────────────────
build:
	cargo build --release

build-dev:
	cargo build

# ── Run ────────────────────────────────────────────────────
run: build
	./target/release/sniper

run-dev:
	RUST_LOG=debug cargo run

# ── Test/Check ─────────────────────────────────────────────
check:
	cargo check

test:
	cargo test

fmt:
	cargo fmt

lint:
	cargo clippy -- -D warnings

# ── Network ────────────────────────────────────────────────
devnet:
	@echo "🧪 Devnet rejimida ishga tushirilmoqda..."
	RPC_HTTPS=https://api.devnet.solana.com \
	RPC_WSS=wss://api.devnet.solana.com \
	cargo run --release

mainnet: build
	@echo "🚨 MAINNET! Ishonchingiz komilmi? [Ctrl+C bekor qilish]"
	@sleep 3
	./target/release/sniper

# ── Boshqa ─────────────────────────────────────────────────
clean:
	cargo clean

wallet:
	bash scripts/generate_wallet.sh

setup:
	bash scripts/setup.sh

logs:
	RUST_LOG=trace ./target/release/sniper 2>&1 | tee bot.log
