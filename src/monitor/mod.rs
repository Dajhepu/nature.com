pub mod pump_fun;
pub mod raydium;
pub mod types;

use crate::config::Config;
use anyhow::Result;
use tokio::sync::mpsc;
use tracing::{error, info};

pub use types::TokenEvent;

/// Monitor barcha kanallarni boshqaradi va TokenEvent larni yuboradi
pub struct Monitor {
    config: Config,
}

impl Monitor {
    pub fn new(config: Config) -> Self {
        Self { config }
    }

    /// Monitoring ni ishga tushirish (Pump.fun + Raydium parallel)
    pub async fn run(&self, event_tx: mpsc::Sender<TokenEvent>) -> Result<()> {
        info!("🔭 Monitor ishga tushmoqda...");

        let pump_tx = event_tx.clone();
        let raydium_tx = event_tx.clone();
        let pump_config = self.config.clone();
        let raydium_config = self.config.clone();

        // Pump.fun va Raydium monitoringini parallel ishlatish
        let pump_handle = pump_fun::PumpFunMonitor::new(pump_config);
        let raydium_handle = raydium::RaydiumMonitor::new(raydium_config);

        tokio::select! {
            result = pump_handle.run(pump_tx) => {
                if let Err(e) = result {
                    error!("❌ Pump.fun monitor xatosi: {e}");
                }
            }
            result = raydium_handle.run(raydium_tx) => {
                if let Err(e) = result {
                    error!("❌ Raydium monitor xatosi: {e}");
                }
            }
        }

        Ok(())
    }
}
