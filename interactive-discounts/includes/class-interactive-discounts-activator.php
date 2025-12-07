<?php
/**
 * Fired during plugin activation.
 *
 * @link       https://example.com
 * @since      1.1.0
 *
 * @package    Interactive_Discounts
 * @subpackage Interactive_Discounts/includes
 */

class Interactive_Discounts_Activator {

    public static function activate() {
        global $wpdb;
        $table_name = $wpdb->prefix . 'id_collected_emails';
        $charset_collate = $wpdb->get_charset_collate();

        $sql = "CREATE TABLE $table_name (
            id mediumint(9) NOT NULL AUTO_INCREMENT,
            time datetime DEFAULT '0000-00-00 00:00:00' NOT NULL,
            email varchar(100) NOT NULL,
            PRIMARY KEY  (id)
        ) $charset_collate;";

        require_once( ABSPATH . 'wp-admin/includes/upgrade.php' );
        dbDelta( $sql );
    }

}
