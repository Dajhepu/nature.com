<?php
class Interactive_Discounts {
    protected $loader;
    protected $plugin_name;
    protected $version;

    public function __construct() {
        if ( defined( 'INTERACTIVE_DISCOUNTS_VERSION' ) ) {
            $this->version = INTERACTIVE_DISCOUNTS_VERSION;
        } else {
            $this->version = '1.1.0';
        }
        $this->plugin_name = 'interactive-discounts';
        $this->load_dependencies();
        $this->define_admin_hooks();
        $this->define_public_hooks();
    }

    private function load_dependencies() {
        require_once plugin_dir_path( dirname( __FILE__ ) ) . 'includes/class-interactive-discounts-loader.php';
        require_once plugin_dir_path( dirname( __FILE__ ) ) . 'admin/class-interactive-discounts-admin.php';
        require_once plugin_dir_path( dirname( __FILE__ ) ) . 'public/class-interactive-discounts-public.php';
        $this->loader = new Interactive_Discounts_Loader();
    }

    private function define_admin_hooks() {
        $plugin_admin = new Interactive_Discounts_Admin( $this->get_plugin_name(), $this->get_version() );
        $this->loader->add_action( 'admin_enqueue_scripts', $plugin_admin, 'enqueue_styles' );
        $this->loader->add_action( 'admin_enqueue_scripts', $plugin_admin, 'enqueue_scripts' );
        $this->loader->add_action( 'admin_menu', $plugin_admin, 'add_options_page' );
        $this->loader->add_action( 'admin_init', $plugin_admin, 'page_init' );
    }

    private function define_public_hooks() {
        $plugin_public = new Interactive_Discounts_Public( $this->get_plugin_name(), $this->get_version() );
        $this->loader->add_action( 'wp_enqueue_scripts', $plugin_public, 'enqueue_styles' );
        $this->loader->add_action( 'wp_enqueue_scripts', $plugin_public, 'enqueue_scripts' );
        $this->loader->add_action( 'wp_footer', $plugin_public, 'add_popup_container' );
        $this->loader->add_action( 'wp_ajax_generate_coupon', $plugin_public, 'generate_coupon_ajax_handler' );
        $this->loader->add_action( 'wp_ajax_nopriv_generate_coupon', $plugin_public, 'generate_coupon_ajax_handler' );
    }

    public function run() {
        $this->loader->run();
    }
    public function get_plugin_name() {
        return $this->plugin_name;
    }
    public function get_version() {
        return $this->version;
    }
}
