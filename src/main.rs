mod analyzer;
mod config;
mod executor;
mod monitor;
mod price;
mod stats;
mod strategy;

use analyzer::Analyzer;
use config::Config;
use executor::Executor;
use monitor::{Monitor, TokenEvent};
use price::PriceFetcher;
use stats::{Stats, TradeRecord};
use strategy::{ExitReason, Strategy};

use anyhow::Result;
use chrono::Utc;
use solana_client::nonblocking::rpc_client::RpcClient;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::mpsc;
use tokio::time::{interval, sleep};
use tracing::{error, info, warn, debug};
use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() -> Result<()> {
    setup_logging();
    print_banner();

    let config = Config::load().map_err(|e| {
        eprintln!("❌ Konfiguratsiya xatosi: {e}");
        eprintln!("💡 cp .env.example .env  va keyin to'ldiring");
        e
    })?;

    print_config(&config);

    let rpc = Arc::new(RpcClient::new_with_timeout(
        config.rpc_https.clone(),
        Duration::from_secs(10),
    ));

    let executor     = Arc::new(Executor::new(config.clone())?);
    let strategy     = Arc::new(Strategy::new(config.clone()));
    let analyzer     = Arc::new(Analyzer::new(config.clone()));
    let price_fetch  = Arc::new(PriceFetcher::new(rpc));
    let stats        = Arc::new(Stats::new());
    let monitor      = Monitor::new(config.clone());

    info!("✅ Barcha komponentlar tayyor | 👛 {}", executor.wallet_pubkey());

    let (event_tx, mut event_rx) = mpsc::channel::<TokenEvent>(2048);

    // Monitor task
    {
        let tx = event_tx.clone();
        tokio::spawn(async move {
            loop {
                if let Err(e) = monitor.run(tx.clone()).await {
                    error!("Monitor xatosi: {e}");
                    sleep(Duration::from_secs(3)).await;
                }
            }
        });
    }

    // Statistika (har 5 daqiqada)
    {
        let s = stats.clone();
        tokio::spawn(async move {
            let mut t = interval(Duration::from_secs(300));
            loop { t.tick().await; s.print_summary(); }
        });
    }

    // Muddati o'tgan pozitsiyalar skaneri (har 10 soniya)
    {
        let strategy_r = strategy.clone();
        let stats_r    = stats.clone();
        tokio::spawn(async move {
            let mut t = interval(Duration::from_secs(10));
            loop {
                t.tick().await;
                for mint in strategy_r.get_expired_positions() {
                    warn!("⏰ Muddati tugadi, yopilmoqda: {mint}");
                    strategy_r.close_position(&mint, 0);
                    stats_r.sell_attempted();
                }
            }
        });
    }

    info!("🚀 Bot ishga tushdi! Yangi tokenlar kutilmoqda...\n");

    while let Some(event) = event_rx.recv().await {
        stats.token_detected();

        let (cfg, ana, str, exe, pf, st) = (
            config.clone(), analyzer.clone(), strategy.clone(),
            executor.clone(), price_fetch.clone(), stats.clone(),
        );

        tokio::spawn(async move {
            if let Err(e) = process_event(event, cfg, ana, str, exe, pf, st).await {
                error!("Event xatosi: {e}");
            }
        });
    }

    Ok(())
}

async fn process_event(
    event: TokenEvent,
    config: Config,
    analyzer: Arc<Analyzer>,
    strategy: Arc<Strategy>,
    executor: Arc<Executor>,
    price_fetcher: Arc<PriceFetcher>,
    stats: Arc<Stats>,
) -> Result<()> {
    info!("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    info!("🔔 {:?} | {} | +{}ms", event.source, event.mint, event.age_ms());

    // 1. TAHLIL
    stats.token_analyzed();
    let analysis = analyzer.analyze(&event).await?;

    if !analysis.approved {
        info!("🚫 Rad etildi [{}]: {}", analysis.reject_reason.as_deref().unwrap_or("-"), event.mint);
        stats.token_rejected();
        return Ok(());
    }

    // 2. STRATEGIYA
    if !strategy.should_buy(&event, &analysis) {
        info!("⏭️  BUY o'tkazildi: {}", event.mint);
        return Ok(());
    }

    // 3. KIRISH NARXI
    let entry_price = match price_fetcher.get_price(&event).await {
        Ok(p) => {
            info!("💱 Kirish narxi: {} lps/token | Pool: {:.3} SOL",
                p.price_lamports, p.sol_reserve as f64 / 1e9);
            p.price_lamports
        }
        Err(e) => { warn!("Narx olish xatosi: {e}"); 0 }
    };

    // 4. BUY
    stats.buy_attempted();
    let sol_amount = config.max_position_lamports();

    let buy_result = match executor.buy(&event, sol_amount, config.slippage_bps).await {
        Ok(r) => {
            info!("🟢 BUY OK | {} | {:.4} SOL", r.signature, r.sol_spent as f64 / 1e9);
            stats.buy_succeeded(r.sol_spent);
            r
        }
        Err(e) => { error!("❌ BUY xato: {e}"); return Ok(()); }
    };

    // 5. POZITSIYA OCHISH
    strategy.open_position(event.mint, entry_price, buy_result.tokens_received, buy_result.sol_spent);

    // 6. MONITORING + SELL (alohida task)
    let (ev, str2, exe2, pf2, st2, cfg2) = (
        event.clone(), strategy.clone(), executor.clone(),
        price_fetcher.clone(), stats.clone(), config.clone(),
    );
    let (tokens, sol_spent) = (buy_result.tokens_received, buy_result.sol_spent);

    tokio::spawn(async move {
        position_monitor(ev, tokens, sol_spent, entry_price, str2, exe2, pf2, st2, cfg2).await;
    });

    Ok(())
}

#[allow(clippy::too_many_arguments)]
async fn position_monitor(
    event: TokenEvent,
    token_amount: u64,
    sol_spent: u64,
    entry_price: u64,
    strategy: Arc<Strategy>,
    executor: Arc<Executor>,
    price_fetcher: Arc<PriceFetcher>,
    stats: Arc<Stats>,
    config: Config,
) {
    info!("👀 Monitoring: {} | TP={:.0}% SL={:.0}% Max={}s",
        event.mint, config.take_profit_pct, config.stop_loss_pct, config.max_hold_time_secs);

    let mut ticker  = interval(Duration::from_millis(500));
    let deadline    = tokio::time::Instant::now() + Duration::from_secs(config.max_hold_time_secs);

    let exit_reason = loop {
        if tokio::time::Instant::now() >= deadline { break ExitReason::TimeExpired; }

        ticker.tick().await;

        let current_price = match price_fetcher.get_price(&event).await {
            Ok(p) => { debug!("Narx: {} lps", p.price_lamports); p.price_lamports }
            Err(_) => continue,
        };

        if let Some(reason) = strategy.check_exit_signals(&event.mint, current_price) {
            break reason;
        }
    };

    // SELL
    info!("📤 SELL: {} | {}", event.mint, exit_reason);
    stats.sell_attempted();

    let sol_received = match executor.sell(&event, token_amount, config.slippage_bps).await {
        Ok(r) => {
            info!("🔴 SELL OK | {} | {:.4} SOL", r.signature, r.sol_received as f64 / 1e9);
            stats.sell_succeeded(r.sol_received);
            r.sol_received
        }
        Err(e) => {
            error!("❌ SELL xato: {e} — retry...");
            sleep(Duration::from_millis(200)).await;
            match executor.sell(&event, token_amount, config.slippage_bps + 500).await {
                Ok(r) => { stats.sell_succeeded(r.sol_received); r.sol_received }
                Err(e2) => { error!("❌ SELL retry xato: {e2}"); 0 }
            }
        }
    };

    strategy.close_position(&event.mint, sol_received);

    let pnl_pct = if sol_spent > 0 {
        (sol_received as f64 - sol_spent as f64) / sol_spent as f64 * 100.0
    } else { 0.0 };
    let pnl_sol = (sol_received as f64 - sol_spent as f64) / 1e9;
    let icon = if pnl_sol >= 0.0 { "🟢" } else { "🔴" };

    info!("{} PnL: {:+.2}% ({:+.4} SOL) | {}", icon, pnl_pct, pnl_sol, exit_reason);

    stats.record_trade(TradeRecord {
        mint: event.mint.to_string(),
        source: format!("{:?}", event.source),
        sol_spent,
        sol_received,
        opened_at: Some(event.detected_at),
        closed_at: Some(Utc::now()),
        exit_reason: exit_reason.to_string(),
        success: sol_received > 0,
    });
}

fn setup_logging() {
    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new("info,solana_client=warn,solana_sdk=warn,reqwest=warn"));
    tracing_subscriber::fmt()
        .with_env_filter(filter)
        .with_target(false)
        .with_ansi(true)
        .compact()
        .init();
}

fn print_banner() {
    println!(r#"
╔═══════════════════════════════════════════════════════════╗
║         SOLANA SNIPER BOT  v0.1.0                        ║
║         Pump.fun + Raydium | Rust + Tokio                ║
╚═══════════════════════════════════════════════════════════╝
"#);
}

fn print_config(c: &Config) {
    info!("⚙️  Konfiguratsiya:");
    info!("   📡 RPC:          {}", c.rpc_https);
    info!("   💸 Slippage:     {}%", c.slippage_bps / 100);
    info!("   💰 Pozitsiya:    {} SOL", c.max_position_sol);
    info!("   📈 TP/SL:        {}% / {}%", c.take_profit_pct, c.stop_loss_pct);
    info!("   ⏱  Max hold:     {}s", c.max_hold_time_secs);
    info!("   ⚡ Priority fee: {} microlamports", c.priority_fee_microlamports);
    if c.jito_tip_lamports > 0 {
        info!("   📦 Jito tip:    {} lamports", c.jito_tip_lamports);
    }
}
