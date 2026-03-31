<?php

/**
 * Fired during plugin activation
 *
 * @link       https://example.com
 * @since      1.0.0
 *
 * @package    Smart_Upsell_For_Woocommerce
 * @subpackage Smart_Upsell_For_Woocommerce/includes
 */

/**
 * Fired during plugin activation.
 *
 * This class defines all code necessary to run during the plugin's activation.
 *
 * @since      1.0.0
 * @package    Smart_Upsell_For_Woocommerce
 * @subpackage Smart_Upsell_For_Woocommerce/includes
 * @author     Jules <jules@example.com>
 */
class Smart_Upsell_For_Woocommerce_Activator {

    /**
     * Short Description. (use period)
     *
     * Long Description.
     *
     * @since    1.0.0
     */
    public static function activate() {
        global $wpdb;

        $table_name = $wpdb->prefix . 'smart_upsell_stats';

        $charset_collate = $wpdb->get_charset_collate();

        $sql = "CREATE TABLE $table_name (
            id mediumint(9) NOT NULL AUTO_INCREMENT,
            time datetime DEFAULT '0000-00-00 00:00:00' NOT NULL,
            offer_id mediumint(9) NOT NULL,
            event_type varchar(255) NOT NULL,
            PRIMARY KEY  (id)
        ) $charset_collate;";

        require_once ABSPATH . 'wp-admin/includes/upgrade.php';
        dbDelta( $sql );
    }

}
