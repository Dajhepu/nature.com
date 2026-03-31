<?php
/**
 * Plugin Name:       Smart Upsell for WooCommerce
 * Plugin URI:        https://example.com/plugins/the-basics/
 * Description:       Increase your store's revenue by offering relevant upsells and cross-sells to your customers.
 * Version:           1.0.0
 * Author:            Jules
 * Author URI:        https://author.example.com/
 * License:           GPL v2 or later
 * License URI:       https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain:       smart-upsell-for-woocommerce
 * Domain Path:       /languages
 */

// If this file is called directly, abort.
if ( ! defined( 'WPINC' ) ) {
	die;
}

/**
 * Currently plugin version.
 */
define( 'SMART_UPSELL_FOR_WOOCOMMERCE_VERSION', '1.0.0' );

/**
 * The code that runs during plugin activation.
 * This action is documented in includes/class-smart-upsell-for-woocommerce-activator.php
 */
function activate_smart_upsell_for_woocommerce() {
	require_once plugin_dir_path( __FILE__ ) . 'includes/class-smart-upsell-for-woocommerce-activator.php';
	Smart_Upsell_For_Woocommerce_Activator::activate();
}

/**
 * The code that runs during plugin deactivation.
 * This action is documented in includes/class-smart-upsell-for-woocommerce-deactivator.php
 */
function deactivate_smart_upsell_for_woocommerce() {
	require_once plugin_dir_path( __FILE__ ) . 'includes/class-smart-upsell-for-woocommerce-deactivator.php';
	Smart_Upsell_For_Woocommerce_Deactivator::deactivate();
}

register_activation_hook( __FILE__, 'activate_smart_upsell_for_woocommerce' );
register_deactivation_hook( __FILE__, 'deactivate_smart_upsell_for_woocommerce' );

/**
 * The core plugin class that is used to define internationalization,
 * admin-specific hooks, and public-facing site hooks.
 */
require plugin_dir_path( __FILE__ ) . 'includes/class-smart-upsell-for-woocommerce.php';

/**
 * Begins execution of the plugin.
 *
 * Since everything within the plugin is registered via hooks,
 * then kicking off the plugin from this point in the file does
 * not affect the page life cycle.
 *
 * @since    1.0.0
 */
function run_smart_upsell_for_woocommerce() {

	$plugin = new Smart_Upsell_For_Woocommerce();
	$plugin->run();

}
run_smart_upsell_for_woocommerce();
