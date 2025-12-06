<?php
/**
 * The public-facing functionality of the plugin.
 *
 * @link       https://example.com
 * @since      1.0.0
 *
 * @package    Interactive_Discounts
 * @subpackage Interactive_Discounts/public
 */

class Interactive_Discounts_Public {

    private $plugin_name;
    private $version;
    private $options;

    public function __construct( $plugin_name, $version ) {
        $this->plugin_name = $plugin_name;
        $this->version = $version;
        $this->options = get_option( 'id_wheel_settings' );
    }

    /**
     * Register the stylesheets for the public-facing side of the site.
     *
     * @since    1.0.0
     */
    public function enqueue_styles() {
        if ( !isset($this->options['enable_wheel']) || $this->options['enable_wheel'] != 1 ) return;
        wp_enqueue_style( $this->plugin_name, plugin_dir_url( __FILE__ ) . 'css/interactive-discounts-public.css', array(), $this->version, 'all' );
    }

    /**
     * Register the JavaScript for the public-facing side of the site.
     *
     * @since    1.0.0
     */
    public function enqueue_scripts() {
        if ( !isset($this->options['enable_wheel']) || $this->options['enable_wheel'] != 1 ) return;

        // Winwheel.js library
        wp_enqueue_script( 'winwheel', plugin_dir_url( __FILE__ ) . 'js/Winwheel.min.js', array(), '2.8.0', true );

        // Plugin's public script
        wp_enqueue_script( $this->plugin_name, plugin_dir_url( __FILE__ ) . 'js/interactive-discounts-public.js', array( 'jquery', 'winwheel' ), $this->version, true );

        wp_localize_script( $this->plugin_name, 'id_wheel_ajax', array(
            'ajax_url' => admin_url( 'admin-ajax.php' ),
            'nonce'    => wp_create_nonce( 'id-wheel-nonce' ),
            'segments' => !empty($this->options['segments']) ? $this->options['segments'] : $this->get_default_segments(),
            'l10n'     => [
                'want_a_discount' => __( 'Want a Discount?', 'interactive-discounts' ),
                'spin_to_win' => __( 'Spin the wheel to win a coupon!', 'interactive-discounts' ),
                'canvas_unsupported' => __( 'Sorry, your browser doesn\'t support canvas. Please try another.', 'interactive-discounts' ),
                'spin_button_text' => __( 'Spin the Wheel!', 'interactive-discounts' ),
                'try_again_message' => __( 'Better luck next time!', 'interactive-discounts' ),
                'congrats_message' => __( 'Congratulations! Your coupon code is:', 'interactive-discounts' ),
                'error_message' => __( 'Something went wrong. Please try again.', 'interactive-discounts' )
            ]
        ) );
    }

    /**
     * Add the popup container to the footer.
     */
    public function add_popup_container() {
        if ( !isset($this->options['enable_wheel']) || $this->options['enable_wheel'] != 1 ) return;

        echo '<div id="id-wheel-popup-wrapper"></div>';
    }

    private function get_default_segments() {
        return [
            ['text' => '10% Off', 'type' => 'percentage', 'value' => '10'],
            ['text' => 'Try Again', 'type' => 'none', 'value' => '0'],
            ['text' => '$5 Off', 'type' => 'fixed_cart', 'value' => '5'],
            ['text' => '20% Off', 'type' => 'percentage', 'value' => '20'],
            ['text' => 'No Luck', 'type' => 'none', 'value' => '0'],
            ['text' => '$10 Off', 'type' => 'fixed_cart', 'value' => '10'],
        ];
    }

    /**
     * AJAX handler to generate a coupon.
     */
    public function generate_coupon_ajax_handler() {
        check_ajax_referer( 'id-wheel-nonce', 'nonce' );

        $segment_index = isset($_POST['segment_index']) ? absint($_POST['segment_index']) : -1;
        $segments = !empty($this->options['segments']) ? $this->options['segments'] : $this->get_default_segments();

        if ( $segment_index < 0 || !isset($segments[$segment_index]) ) {
            wp_send_json_error( [ 'message' => 'Invalid segment.' ] );
        }

        $won_segment = $segments[$segment_index];

        if ($won_segment['type'] === 'none') {
            wp_send_json_success( [ 'coupon_code' => null, 'message' => 'Better luck next time!' ] );
        }

        $coupon_code = 'WHEEL-' . strtoupper( wp_generate_password( 8, false ) );
        $amount = $won_segment['value'];
        $discount_type = $won_segment['type']; // 'percentage', 'fixed_cart'

        $coupon = array(
            'post_title' => $coupon_code,
            'post_content' => '',
            'post_status' => 'publish',
            'post_author' => 1,
            'post_type' => 'shop_coupon'
        );

        $new_coupon_id = wp_insert_post( $coupon );

        update_post_meta( $new_coupon_id, 'discount_type', $discount_type );
        update_post_meta( $new_coupon_id, 'coupon_amount', $amount );
        update_post_meta( $new_coupon_id, 'individual_use', 'yes' );
        update_post_meta( $new_coupon_id, 'usage_limit', '1' );
        update_post_meta( $new_coupon_id, 'expiry_date', date('Y-m-d', strtotime('+1 day')) );

        wp_send_json_success( [ 'coupon_code' => $coupon_code, 'message' => 'Congratulations! Your coupon code is:' ] );
    }

}
