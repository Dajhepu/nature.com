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

/**
 * The admin-specific functionality of the plugin.
 *
 * Defines the plugin name, version, and two examples hooks for how to
 * enqueue the admin-specific stylesheet and JavaScript.
 *
 * @package    Smart_Upsell_For_Woocommerce
 * @subpackage Smart_Upsell_For_Woocommerce/admin
 * @author     Jules <jules@example.com>
 */
class Smart_Upsell_Admin {

    /**
     * The ID of this plugin.
     *
     * @since    1.0.0
     * @access   private
     * @var      string    $plugin_name    The ID of this plugin.
     */
    private $plugin_name;

    /**
     * The version of this plugin.
     *
     * @since    1.0.0
     * @access   private
     * @var      string    $version    The current version of this plugin.
     */
    private $version;

    /**
     * Initialize the class and set its properties.
     *
     * @since    1.0.0
     * @param      string    $plugin_name       The name of this plugin.
     * @param      string    $version    The version of this plugin.
     */
    public function __construct( $plugin_name, $version ) {

        $this->plugin_name = $plugin_name;
        $this->version = $version;

    }

    /**
     * Register the stylesheets for the admin area.
     *
     * @since    1.0.0
     */
    public function enqueue_styles() {
        // Enqueue admin-specific stylesheets here.
    }

    /**
     * Register the JavaScript for the admin area.
     *
     * @since    1.0.0
     */
    public function enqueue_scripts( $hook ) {
        global $post;

        if ( ( 'post.php' == $hook || 'post-new.php' == $hook ) && 'smart_upsell_rule' == $post->post_type ) {
            wp_enqueue_script( 'wc-product-search' );
        }
    }

    /**
     * Add the top-level admin menu.
     *
     * @since    1.0.0
     */
    public function add_admin_menu() {
        add_menu_page(
            __( 'Smart Upsells', 'smart-upsell-for-woocommerce' ),
            __( 'Smart Upsells', 'smart-upsell-for-woocommerce' ),
            'manage_options',
            $this->plugin_name,
            array( $this, 'display_plugin_setup_page' ),
            'dashicons-cart',
            56
        );

        add_submenu_page(
            $this->plugin_name,
            __( 'Upsell Rules', 'smart-upsell-for-woocommerce' ),
            __( 'Upsell Rules', 'smart-upsell-for-woocommerce' ),
            'manage_options',
            'edit.php?post_type=smart_upsell_rule'
        );

        add_submenu_page(
            $this->plugin_name,
            __( 'Settings', 'smart-upsell-for-woocommerce' ),
            __( 'Settings', 'smart-upsell-for-woocommerce' ),
            'manage_options',
            $this->plugin_name . '-settings',
            array( $this, 'display_settings_page' )
        );

        add_submenu_page(
            $this->plugin_name,
            __( 'Analytics', 'smart-upsell-for-woocommerce' ),
            __( 'Analytics', 'smart-upsell-for-woocommerce' ),
            'manage_options',
            $this->plugin_name . '-analytics',
            array( $this, 'display_analytics_page' )
        );
    }

    /**
     * Render the basic plugin setup page.
     *
     * @since    1.0.0
     */
    public function display_plugin_setup_page() {
        require_once 'partials/smart-upsell-for-woocommerce-admin-display.php';
    }

    /**
     * Render the settings page.
     *
     * @since    1.0.0
     */
    public function display_settings_page() {
        echo "<h1>Settings Page</h1>";
    }

    /**
     * Render the analytics page.
     *
     * @since    1.0.0
     */
    public function display_analytics_page() {
        $impressions = $this->get_stats_by_event_type( 'impression' );
        $clicks = $this->get_stats_by_event_type( 'click' );
        $conversion_rate = $this->get_conversion_rate( $impressions, $clicks );

        require_once 'partials/smart-upsell-for-woocommerce-analytics-display.php';
    }

    /**
     * Get stats by event type.
     *
     * @since    1.0.0
     * @param    string    $event_type    The event type.
     * @return   int       The number of events.
     */
    private function get_stats_by_event_type( $event_type ) {
        global $wpdb;

        $table_name = $wpdb->prefix . 'smart_upsell_stats';

        $count = $wpdb->get_var( $wpdb->prepare( "SELECT COUNT(*) FROM $table_name WHERE event_type = %s", $event_type ) );

        return $count;
    }

    /**
     * Get the conversion rate.
     *
     * @since    1.0.0
     * @param    int    $impressions    The number of impressions.
     * @param    int    $clicks         The number of clicks.
     * @return   float  The conversion rate.
     */
    private function get_conversion_rate( $impressions, $clicks ) {
        if ( $impressions == 0 ) {
            return 0;
        }

        return round( ( $clicks / $impressions ) * 100, 2 );
    }

    /**
     * Register the custom post type for upsell rules.
     *
     * @since    1.0.0
     */
    public function register_rules_cpt() {
        $labels = array(
            'name'                  => _x( 'Upsell Rules', 'Post Type General Name', 'smart-upsell-for-woocommerce' ),
            'singular_name'         => _x( 'Upsell Rule', 'Post Type Singular Name', 'smart-upsell-for-woocommerce' ),
            'menu_name'             => __( 'Upsell Rules', 'smart-upsell-for-woocommerce' ),
            'name_admin_bar'        => __( 'Upsell Rule', 'smart-upsell-for-woocommerce' ),
            'archives'              => __( 'Rule Archives', 'smart-upsell-for-woocommerce' ),
            'attributes'            => __( 'Rule Attributes', 'smart-upsell-for-woocommerce' ),
            'parent_item_colon'     => __( 'Parent Rule:', 'smart-upsell-for-woocommerce' ),
            'all_items'             => __( 'All Rules', 'smart-upsell-for-woocommerce' ),
            'add_new_item'          => __( 'Add New Rule', 'smart-upsell-for-woocommerce' ),
            'add_new'               => __( 'Add New', 'smart-upsell-for-woocommerce' ),
            'new_item'              => __( 'New Rule', 'smart-upsell-for-woocommerce' ),
            'edit_item'             => __( 'Edit Rule', 'smart-upsell-for-woocommerce' ),
            'update_item'           => __( 'Update Rule', 'smart-upsell-for-woocommerce' ),
            'view_item'             => __( 'View Rule', 'smart-upsell-for-woocommerce' ),
            'view_items'            => __( 'View Rules', 'smart-upsell-for-woocommerce' ),
            'search_items'          => __( 'Search Rule', 'smart-upsell-for-woocommerce' ),
            'not_found'             => __( 'Not found', 'smart-upsell-for-woocommerce' ),
            'not_found_in_trash'    => __( 'Not found in Trash', 'smart-upsell-for-woocommerce' ),
            'featured_image'        => __( 'Featured Image', 'smart-upsell-for-woocommerce' ),
            'set_featured_image'    => __( 'Set featured image', 'smart-upsell-for-woocommerce' ),
            'remove_featured_image' => __( 'Remove featured image', 'smart-upsell-for-woocommerce' ),
            'use_featured_image'    => __( 'Use as featured image', 'smart-upsell-for-woocommerce' ),
            'insert_into_item'      => __( 'Insert into rule', 'smart-upsell-for-woocommerce' ),
            'uploaded_to_this_item' => __( 'Uploaded to this rule', 'smart-upsell-for-woocommerce' ),
            'items_list'            => __( 'Rules list', 'smart-upsell-for-woocommerce' ),
            'items_list_navigation' => __( 'Rules list navigation', 'smart-upsell-for-woocommerce' ),
            'filter_items_list'     => __( 'Filter rules list', 'smart-upsell-for-woocommerce' ),
        );
        $args = array(
            'label'                 => __( 'Upsell Rule', 'smart-upsell-for-woocommerce' ),
            'description'           => __( 'Custom Post Type for Upsell Rules', 'smart-upsell-for-woocommerce' ),
            'labels'                => $labels,
            'supports'              => array( 'title' ),
            'hierarchical'          => false,
            'public'                => false,
            'show_ui'               => true,
            'show_in_menu'          => 'smart-upsell-for-woocommerce',
            'menu_position'         => 5,
            'show_in_admin_bar'     => false,
            'show_in_nav_menus'     => false,
            'can_export'            => true,
            'has_archive'           => false,
            'exclude_from_search'   => true,
            'publicly_queryable'    => false,
            'capability_type'       => 'page',
        );
        register_post_type( 'smart_upsell_rule', $args );
    }

    /**
     * Add meta boxes for the upsell rules CPT.
     *
     * @since    1.0.0
     */
    public function add_rules_meta_boxes() {
        add_meta_box(
            'smart_upsell_rule_settings',
            __( 'Rule Settings', 'smart-upsell-for-woocommerce' ),
            array( $this, 'render_rules_meta_box' ),
            'smart_upsell_rule',
            'normal',
            'high'
        );
    }

    /**
     * Render the meta box for the upsell rules CPT.
     *
     * @since    1.0.0
     * @param    WP_Post    $post    The post object.
     */
    public function render_rules_meta_box( $post ) {
        wp_nonce_field( 'smart_upsell_rule_meta_box', 'smart_upsell_rule_meta_box_nonce' );

        $offer_type = get_post_meta( $post->ID, '_offer_type', true );
        ?>
        <p>
            <label for="offer_type"><?php esc_html_e( 'Offer Type', 'smart-upsell-for-woocommerce' ); ?></label>
            <select name="offer_type" id="offer_type">
                <option value="upsell" <?php selected( $offer_type, 'upsell' ); ?>><?php esc_html_e( 'Upsell', 'smart-upsell-for-woocommerce' ); ?></option>
                <option value="cross-sell" <?php selected( $offer_type, 'cross-sell' ); ?>><?php esc_html_e( 'Cross-sell', 'smart-upsell-for-woocommerce' ); ?></option>
            </select>
        </p>
        <p>
            <label for="trigger_product"><?php esc_html_e( 'Trigger Product', 'smart-upsell-for-woocommerce' ); ?></label>
            <select class="wc-product-search" name="trigger_product" id="trigger_product" data-placeholder="<?php esc_attr_e( 'Search for a product…', 'smart-upsell-for-woocommerce' ); ?>" data-action="woocommerce_json_search_products_and_variations" data-multiple="false">
                <?php
                $product_id = get_post_meta( $post->ID, '_trigger_product', true );
                if ( $product_id ) {
                    $product = wc_get_product( $product_id );
                    if ( $product ) {
                        echo '<option value="' . esc_attr( $product_id ) . '" selected="selected">' . esc_html( $product->get_formatted_name() ) . '</option>';
                    }
                }
                ?>
            </select>
        </p>
        <p>
            <label for="upsell_product"><?php esc_html_e( 'Upsell/Cross-sell Product', 'smart-upsell-for-woocommerce' ); ?></label>
            <select class="wc-product-search" name="upsell_product" id="upsell_product" data-placeholder="<?php esc_attr_e( 'Search for a product…', 'smart-upsell-for-woocommerce' ); ?>" data-action="woocommerce_json_search_products_and_variations" data-multiple="false">
                <?php
                $product_id = get_post_meta( $post->ID, '_upsell_product', true );
                if ( $product_id ) {
                    $product = wc_get_product( $product_id );
                    if ( $product ) {
                        echo '<option value="' . esc_attr( $product_id ) . '" selected="selected">' . esc_html( $product->get_formatted_name() ) . '</option>';
                    }
                }
                ?>
            </select>
        </p>
        <?php
    }

    /**
     * Save the meta box data for the upsell rules CPT.
     *
     * @since    1.0.0
     * @param    int    $post_id    The post ID.
     */
    public function save_rules_meta_box_data( $post_id ) {
        if ( ! isset( $_POST['smart_upsell_rule_meta_box_nonce'] ) ) {
            return;
        }

        if ( ! wp_verify_nonce( $_POST['smart_upsell_rule_meta_box_nonce'], 'smart_upsell_rule_meta_box' ) ) {
            return;
        }

        if ( defined( 'DOING_AUTOSAVE' ) && DOING_AUTOSAVE ) {
            return;
        }

        if ( ! current_user_can( 'edit_post', $post_id ) ) {
            return;
        }

        if ( isset( $_POST['offer_type'] ) ) {
            update_post_meta( $post_id, '_offer_type', sanitize_text_field( $_POST['offer_type'] ) );
        }

        if ( isset( $_POST['trigger_product'] ) ) {
            update_post_meta( $post_id, '_trigger_product', absint( $_POST['trigger_product'] ) );
        }

        if ( isset( $_POST['upsell_product'] ) ) {
            update_post_meta( $post_id, '_upsell_product', absint( $_POST['upsell_product'] ) );
        }
    }

}
