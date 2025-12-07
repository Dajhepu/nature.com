<?php
/**
 * Plugin Name:       Interactive Discounts
 * Plugin URI:        https://example.com/
 * Description:       Engage your customers with interactive discount games like the Wheel of Fortune.
 * Version:           1.1.0
 * Author:            Jules
 * Author URI:        https://example.com/
 * License:           GPL-2.0+
 * License URI:       http://www.gnu.org/licenses/gpl-2.0.txt
 * Text Domain:       interactive-discounts
 * Domain Path:       /languages
 */

// If this file is called directly, abort.
if ( ! defined( 'WPINC' ) ) {
    die;
}

define( 'INTERACTIVE_DISCOUNTS_VERSION', '1.1.0' );

/**
 * The code that runs during plugin activation.
 */
function activate_interactive_discounts() {
    require_once plugin_dir_path( __FILE__ ) . 'includes/class-interactive-discounts-activator.php';
    Interactive_Discounts_Activator::activate();
}

/**
 * The code that runs during plugin deactivation.
 */
function deactivate_interactive_discounts() {
    require_once plugin_dir_path( __FILE__ ) . 'includes/class-interactive-discounts-deactivator.php';
    Interactive_Discounts_Deactivator::deactivate();
}

register_activation_hook( __FILE__, 'activate_interactive_discounts' );
register_deactivation_hook( __FILE__, 'deactivate_interactive_discounts' );


require plugin_dir_path( __FILE__ ) . 'includes/class-interactive-discounts.php';

function run_interactive_discounts() {
    $plugin = new Interactive_Discounts();
    $plugin->run();
}
run_interactive_discounts();
