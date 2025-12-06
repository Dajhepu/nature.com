<?php
/**
 * The file that defines the core plugin class
 *
 * @link       https://example.com
 * @since      1.0.0
 *
 * @package    Smart_Upsell_For_Woocommerce
 * @subpackage Smart_Upsell_For_Woocommerce/includes
 */

/**
 * The core plugin class.
 *
 * @since      1.0.0
 * @package    Smart_Upsell_For_Woocommerce
 * @subpackage Smart_Upsell_For_Woocommerce/includes
 * @author     Jules <jules@example.com>
 */
class Smart_Upsell_For_Woocommerce {

    /**
     * The loader that's responsible for maintaining and registering all hooks that power
     * the plugin.
     *
     * @since    1.0.0
     * @access   protected
     * @var      Smart_Upsell_For_Woocommerce_Loader    $loader    Maintains and registers all hooks for the plugin.
     */
    protected $loader;

    /**
     * The unique identifier of this plugin.
     *
     * @since    1.0.0
     * @access   protected
     * @var      string    $plugin_name    The string used to uniquely identify this plugin.
     */
    protected $plugin_name;

    /**
     * The current version of the plugin.
     *
     * @since    1.0.0
     * @access   protected
     * @var      string    $version    The current version of the plugin.
     */
    protected $version;

    /**
     * Define the core functionality of the plugin.
     *
     * @since    1.0.0
     */
    public function __construct() {
        if ( defined( 'SMART_UPSELL_FOR_WOOCOMMERCE_VERSION' ) ) {
            $this->version = SMART_UPSELL_FOR_WOOCOMMERCE_VERSION;
        } else {
            $this->version = '1.0.0';
        }
        $this->plugin_name = 'smart-upsell-for-woocommerce';

        $this->load_dependencies();
        $this->set_locale();
        $this->define_admin_hooks();
        $this->define_public_hooks();
    }

    /**
     * Load the required dependencies for this plugin.
     *
     * @since    1.0.0
     * @access   private
     */
    private function load_dependencies() {
        require_once plugin_dir_path( dirname( __FILE__ ) ) . 'includes/class-smart-upsell-for-woocommerce-loader.php';
        require_once plugin_dir_path( dirname( __FILE__ ) ) . 'includes/class-smart-upsell-for-woocommerce-i18n.php';
        require_once plugin_dir_path( dirname( __FILE__ ) ) . 'admin/class-smart-upsell-admin.php';
        require_once plugin_dir_path( dirname( __FILE__ ) ) . 'public/class-smart-upsell-public.php';

        $this->loader = new Smart_Upsell_For_Woocommerce_Loader();
    }

    /**
     * Define the locale for this plugin for internationalization.
     *
     * @since    1.0.0
     * @access   private
     */
    private function set_locale() {
        $plugin_i18n = new Smart_Upsell_For_Woocommerce_i18n();
        $this->loader->add_action( 'plugins_loaded', $plugin_i18n, 'load_plugin_textdomain' );
    }

    /**
     * Register all of the hooks related to the admin area functionality
     * of the plugin.
     *
     * @since    1.0.0
     * @access   private
     */
    private function define_admin_hooks() {
        $plugin_admin = new Smart_Upsell_Admin( $this->get_plugin_name(), $this->get_version() );

        $this->loader->add_action( 'admin_enqueue_scripts', $plugin_admin, 'enqueue_styles' );
        $this->loader->add_action( 'admin_enqueue_scripts', $plugin_admin, 'enqueue_scripts' );
        $this->loader->add_action( 'admin_menu', $plugin_admin, 'add_admin_menu' );
        $this->loader->add_action( 'init', $plugin_admin, 'register_rules_cpt' );
        $this->loader->add_action( 'add_meta_boxes', $plugin_admin, 'add_rules_meta_boxes' );
        $this->loader->add_action( 'save_post', $plugin_admin, 'save_rules_meta_box_data' );
        $this->loader->add_action( 'admin_init', $plugin_admin, 'register_settings' );
    }

    /**
     * Register all of the hooks related to the public-facing functionality
     * of the plugin.
     *
     * @since    1.0.0
     * @access   private
     */
    private function define_public_hooks() {
        $plugin_public = new Smart_Upsell_Public( $this->get_plugin_name(), $this->get_version() );

        $this->loader->add_action( 'wp_enqueue_scripts', $plugin_public, 'enqueue_styles' );
        $this->loader->add_action( 'wp_enqueue_scripts', $plugin_public, 'enqueue_scripts' );
        $this->loader->add_action( 'wp_enqueue_scripts', $plugin_public, 'add_inline_styles' );
        $this->loader->add_action( 'wp_footer', $plugin_public, 'render_popup_container' );
        $this->loader->add_action( 'wp_ajax_get_upsell_offer', $plugin_public, 'get_upsell_offer_ajax_handler' );
        $this->loader->add_action( 'wp_ajax_nopriv_get_upsell_offer', $plugin_public, 'get_upsell_offer_ajax_handler' );
        $this->loader->add_action( 'woocommerce_before_checkout_form', $plugin_public, 'display_cross_sell_products' );

        // Separate AJAX handlers for clarity
        $this->loader->add_action( 'wp_ajax_add_upsell_to_cart', $plugin_public, 'add_upsell_to_cart_ajax_handler' );
        $this->loader->add_action( 'wp_ajax_nopriv_add_upsell_to_cart', $plugin_public, 'add_upsell_to_cart_ajax_handler' );
        $this->loader->add_action( 'wp_ajax_add_cross_sell_to_order', $plugin_public, 'add_cross_sell_to_order_ajax_handler' );
        $this->loader->add_action( 'wp_ajax_nopriv_add_cross_sell_to_order', $plugin_public, 'add_cross_sell_to_order_ajax_handler' );
        $this->loader->add_action( 'woocommerce_before_calculate_totals', $plugin_public, 'apply_discount', 10, 1 );
        $this->loader->add_action( 'woocommerce_checkout_create_order_line_item', $plugin_public, 'add_custom_meta_to_order_item', 10, 4 );
        $this->loader->add_action( 'woocommerce_checkout_order_processed', $plugin_public, 'track_conversion', 10, 1 );
    }

    /**
     * Run the loader to execute all of the hooks with WordPress.
     *
     * @since    1.0.0
     */
    public function run() {
        $this->loader->run();
    }

    /**
     * The name of the plugin.
     *
     * @since     1.0.0
     * @return    string    The name of the plugin.
     */
    public function get_plugin_name() {
        return $this->plugin_name;
    }

    /**
     * The reference to the class that orchestrates the hooks with the plugin.
     *
     * @since     1.0.0
     * @return    Smart_Upsell_For_Woocommerce_Loader    Orchestrates the hooks of the plugin.
     */
    public function get_loader() {
        return $this->loader;
    }

    /**
     * Retrieve the version number of the plugin.
     *
     * @since     1.0.0
     * @return    string    The version number of the plugin.
     */
    public function get_version() {
        return $this->version;
    }
}
