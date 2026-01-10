<?php
/**
 * The admin-specific functionality of the plugin.
 *
 * @link       https://example.com
 * @since      1.0.0
 *
 * @package    Smart_Upsell_For_Woocommerce
 * @subpackage Smart_Upsell_For_Woocommerce/admin
 */
class Smart_Upsell_Admin {

    private $plugin_name;
    private $version;

    public function __construct( $plugin_name, $version ) {
        $this->plugin_name = $plugin_name;
        $this->version = $version;
    }

    public function enqueue_styles() {
        wp_enqueue_style( 'wp-color-picker' );
    }

    public function enqueue_scripts( $hook ) {
        $screen = get_current_screen();
        if ( $screen && 'smart_upsell_rule' === $screen->post_type ) {
            wp_enqueue_script( 'wc-product-search' );
            wp_enqueue_script( $this->plugin_name . '-admin-rules', plugin_dir_url( __FILE__ ) . 'js/smart-upsell-admin-rules.js', [ 'jquery' ], $this->version, false );
        }

        if ( 'smart-upsells_page_smart-upsell-for-woocommerce-settings' === $hook ) {
            wp_enqueue_script( 'wp-color-picker' );
            wp_enqueue_script( $this->plugin_name . '-admin-settings', plugin_dir_url( __FILE__ ) . 'js/smart-upsell-admin-settings.js', array( 'wp-color-picker' ), $this->version, false );
        }
    }

    public function add_admin_menu() {
        add_menu_page( __( 'Smart Upsells', 'smart-upsell-for-woocommerce' ), __( 'Smart Upsells', 'smart-upsell-for-woocommerce' ), 'manage_options', $this->plugin_name, array( $this, 'display_analytics_page' ), 'dashicons-cart', 56 );
        add_submenu_page( $this->plugin_name, __( 'Upsell Rules', 'smart-upsell-for-woocommerce' ), __( 'Upsell Rules', 'smart-upsell-for-woocommerce' ), 'manage_options', 'edit.php?post_type=smart_upsell_rule' );
        add_submenu_page( $this->plugin_name, __( 'Add New Rule', 'smart-upsell-for-woocommerce' ), __( 'Add New Rule', 'smart-upsell-for-woocommerce' ), 'manage_options', 'post-new.php?post_type=smart_upsell_rule' );
        add_submenu_page( $this->plugin_name, __( 'Analytics', 'smart-upsell-for-woocommerce' ), __( 'Analytics', 'smart-upsell-for-woocommerce' ), 'manage_options', $this->plugin_name . '-analytics', array( $this, 'display_analytics_page' ) );
        add_submenu_page( $this->plugin_name, __( 'Settings', 'smart-upsell-for-woocommerce' ), __( 'Settings', 'smart-upsell-for-woocommerce' ), 'manage_options', $this->plugin_name . '-settings', array( $this, 'display_settings_page' ) );
    }

    public function register_settings() {
        register_setting( 'smart_upsell_settings', 'smart_upsell_settings', array( $this, 'sanitize_settings' ) );
        add_settings_section( 'smart_upsell_popup_settings', __( 'Popup Settings', 'smart-upsell-for-woocommerce' ), null, 'smart_upsell_settings' );
        add_settings_field( 'popup_title', __( 'Popup Title', 'smart-upsell-for-woocommerce' ), array( $this, 'render_settings_field' ), 'smart_upsell_settings', 'smart_upsell_popup_settings', [ 'type' => 'text', 'id' => 'popup_title', 'name' => 'popup_title', 'default' => __( 'Don\'t miss this exclusive offer!', 'smart-upsell-for-woocommerce' ) ] );
        add_settings_field( 'popup_bg_color', __( 'Popup Background Color', 'smart-upsell-for-woocommerce' ), array( $this, 'render_settings_field' ), 'smart_upsell_settings', 'smart_upsell_popup_settings', [ 'type' => 'color', 'id' => 'popup_bg_color', 'name' => 'popup_bg_color', 'default' => '#ffffff' ] );
        add_settings_field( 'popup_button_color', __( 'Popup Button Color', 'smart-upsell-for-woocommerce' ), array( $this, 'render_settings_field' ), 'smart_upsell_settings', 'smart_upsell_popup_settings', [ 'type' => 'color', 'id' => 'popup_button_color', 'name' => 'popup_button_color', 'default' => '#0073aa' ] );
    }

    public function render_settings_field( $args ) {
        $options = get_option( 'smart_upsell_settings', [] );
        $value = isset( $options[ $args['name'] ] ) ? $options[ $args['name'] ] : $args['default'];
        $class = $args['type'] === 'color' ? 'class="wp-color-picker-field"' : 'class="regular-text"';
        echo '<input type="' . esc_attr($args['type']) . '" id="' . esc_attr( $args['id'] ) . '" name="smart_upsell_settings[' . esc_attr( $args['name'] ) . ']" value="' . esc_attr( $value ) . '" ' . $class . '>';
    }

    public function sanitize_settings( $input ) {
        $new_input = [];
        if ( isset( $input['popup_title'] ) ) $new_input['popup_title'] = sanitize_text_field( $input['popup_title'] );
        if ( isset( $input['popup_bg_color'] ) ) $new_input['popup_bg_color'] = sanitize_hex_color( $input['popup_bg_color'] );
        if ( isset( $input['popup_button_color'] ) ) $new_input['popup_button_color'] = sanitize_hex_color( $input['popup_button_color'] );
        return $new_input;
    }

    public function display_settings_page() {
        echo '<div class="wrap"><h1>' . esc_html( get_admin_page_title() ) . '</h1><form action="options.php" method="post">';
        settings_fields( 'smart_upsell_settings' );
        do_settings_sections( 'smart_upsell_settings' );
        submit_button();
        echo '</form></div>';
    }

    public function display_analytics_page() {
        $impressions = $this->get_stats_by_event_type( 'impression' );
        $clicks = $this->get_stats_by_event_type( 'click' );
        $conversion_rate = $this->get_conversion_rate( $impressions, $clicks );
        $total_revenue = $this->get_total_revenue();
        require_once 'partials/smart-upsell-for-woocommerce-analytics-display.php';
    }

    private function get_stats_by_event_type( $event_type ) {
        global $wpdb;
        return $wpdb->get_var( $wpdb->prepare( "SELECT COUNT(*) FROM {$wpdb->prefix}smart_upsell_stats WHERE event_type = %s", $event_type ) );
    }

    private function get_conversion_rate( $impressions, $clicks ) {
        return $impressions > 0 ? round( ( $clicks / $impressions ) * 100, 2 ) : 0;
    }

    private function get_total_revenue() {
        global $wpdb;
        return $wpdb->get_var( "SELECT SUM(meta_value) FROM $wpdb->postmeta WHERE meta_key = '_revenue'" );
    }

    public function register_rules_cpt() {
        $labels = [ 'name' => _x( 'Upsell Rules', 'Post Type General Name', 'smart-upsell-for-woocommerce' ), 'singular_name' => _x( 'Upsell Rule', 'Post Type Singular Name', 'smart-upsell-for-woocommerce' ), 'menu_name' => __( 'Upsell Rules', 'smart-upsell-for-woocommerce' ), 'all_items' => __( 'All Rules', 'smart-upsell-for-woocommerce' ), 'add_new_item' => __( 'Add New Rule', 'smart-upsell-for-woocommerce' ), 'add_new' => __( 'Add New', 'smart-upsell-for-woocommerce' ), 'edit_item' => __( 'Edit Rule', 'smart-upsell-for-woocommerce' ), 'update_item' => __( 'Update Rule', 'smart-upsell-for-woocommerce' ) ];
        register_post_type( 'smart_upsell_rule', [ 'label' => __( 'Upsell Rule', 'smart-upsell-for-woocommerce' ), 'labels' => $labels, 'supports' => [ 'title' ], 'public' => false, 'show_ui' => true, 'show_in_menu' => false, 'capability_type' => 'post' ] );
    }

    public function add_rules_meta_boxes() {
        add_meta_box( 'smart_upsell_rule_settings', __( 'Rule Settings', 'smart-upsell-for-woocommerce' ), [ $this, 'render_rules_meta_box' ], 'smart_upsell_rule', 'normal', 'high' );
    }

    public function render_rules_meta_box( $post ) {
        wp_nonce_field( 'smart_upsell_rule_meta_box', 'smart_upsell_rule_meta_box_nonce' );
        require_once 'partials/smart-upsell-for-woocommerce-meta-box-display.php';
    }

    public function save_rules_meta_box_data( $post_id ) {
        if ( ! isset( $_POST['smart_upsell_rule_meta_box_nonce'] ) || ! wp_verify_nonce( $_POST['smart_upsell_rule_meta_box_nonce'], 'smart_upsell_rule_meta_box' ) || ( defined( 'DOING_AUTOSAVE' ) && DOING_AUTOSAVE ) || ! current_user_can( 'edit_post', $post_id ) ) return;
        $fields = [ '_offer_type', '_trigger_type', '_discount_type', '_discount_amount', '_trigger_product', '_trigger_category', '_upsell_product' ];
        foreach ( $fields as $field ) {
            $key = substr( $field, 1 );
            if ( isset( $_POST[ $key ] ) ) {
                update_post_meta( $post_id, $field, sanitize_text_field( $_POST[ $key ] ) );
            }
        }
    }
}
