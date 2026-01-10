<?php
/**
 * Define the internationalization functionality
 *
 * @link       https://example.com
 * @since      1.0.0
 *
 * @package    Smart_Upsell_For_Woocommerce
 * @subpackage Smart_Upsell_For_Woocommerce/includes
 */

/**
 * Define the internationalization functionality.
 *
 * @since      1.0.0
 * @package    Smart_Upsell_For_Woocommerce
 * @subpackage Smart_Upsell_For_Woocommerce/includes
 * @author     Jules <jules@example.com>
 */
class Smart_Upsell_For_Woocommerce_i18n {

    /**
     * Load the plugin text domain for translation.
     *
     * @since    1.0.0
     */
    public function load_plugin_textdomain() {
        load_plugin_textdomain(
            'smart-upsell-for-woocommerce',
            false,
            dirname( dirname( plugin_basename( __FILE__ ) ) ) . '/languages/'
        );
    }
}
