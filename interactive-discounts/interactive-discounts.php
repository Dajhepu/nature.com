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

require plugin_dir_path( __FILE__ ) . 'includes/class-interactive-discounts.php';

function run_interactive_discounts() {
    $plugin = new Interactive_Discounts();
    $plugin->run();
}
run_interactive_discounts();
