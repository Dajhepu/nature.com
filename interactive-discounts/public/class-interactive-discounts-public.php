<?php
class Interactive_Discounts_Public {

    private $plugin_name;
    private $version;
    private $options;

    public function __construct( $plugin_name, $version ) {
        $this->plugin_name = $plugin_name;
        $this->version = $version;
        $this->options = get_option( 'id_wheel_settings' );
    }

    public function enqueue_styles() {
        if ( !isset($this->options['enable_wheel']) || $this->options['enable_wheel'] != 1 ) return;
        wp_enqueue_style( $this->plugin_name, plugin_dir_url( __FILE__ ) . 'css/interactive-discounts-public.css', array(), $this->version, 'all' );
    }

    public function enqueue_scripts() {
        if ( !isset($this->options['enable_wheel']) || $this->options['enable_wheel'] != 1 ) return;
        wp_enqueue_script( 'winwheel', plugin_dir_url( __FILE__ ) . 'js/Winwheel.min.js', array(), '2.8.0', true );
        wp_enqueue_script( $this->plugin_name, plugin_dir_url( __FILE__ ) . 'js/interactive-discounts-public.js', array( 'jquery', 'winwheel' ), $this->version, true );
        wp_localize_script( $this->plugin_name, 'id_wheel_ajax', array(
            'ajax_url' => admin_url( 'admin-ajax.php' ),
            'nonce'    => wp_create_nonce( 'id-wheel-nonce' ),
            'segments' => !empty($this->options['segments']) ? $this->options['segments'] : $this->get_default_segments(),
            'settings' => [
                'enable_email_collection' => isset($this->options['enable_email_collection']) && $this->options['enable_email_collection'] == 1,
                'email_title' => isset($this->options['email_title']) ? $this->options['email_title'] : __( 'Want a Discount?', 'interactive-discounts' ),
                'email_subtitle' => isset($this->options['email_subtitle']) ? $this->options['email_subtitle'] : __( 'Enter your email to spin the wheel!', 'interactive-discounts' ),
                'email_button_text' => isset($this->options['email_button_text']) ? $this->options['email_button_text'] : __( 'Try my luck!', 'interactive-discounts' ),
            ],
            'l10n'     => [
                'want_a_discount' => __( 'Want a Discount?', 'interactive-discounts' ),
                'spin_to_win' => __( 'Spin the wheel to win a coupon!', 'interactive-discounts' ),
                'canvas_unsupported' => __( 'Sorry, your browser doesn\'t support canvas. Please try another.', 'interactive-discounts' ),
                'spin_button_text' => __( 'Spin the Wheel!', 'interactive-discounts' ),
                'error_message' => __( 'Something went wrong. Please try again.', 'interactive-discounts' )
            ]
        ) );
    }

    public function add_popup_container() {
        if ( !isset($this->options['enable_wheel']) || $this->options['enable_wheel'] != 1 ) return;
        echo '<div id="id-wheel-popup-wrapper"></div>';
    }

    private function get_default_segments() {
        return [
            ['fillStyle' => '#eae56f', 'text' => '10% Off'], ['fillStyle' => '#89f26e', 'text' => 'Try Again'],
            ['fillStyle' => '#7de6ef', 'text' => '$5 Off'], ['fillStyle' => '#e7706f', 'text' => '20% Off'],
            ['fillStyle' => '#eae56f', 'text' => 'No Luck'], ['fillStyle' => '#89f26e', 'text' => '$10 Off'],
        ];
    }

    public function generate_coupon_ajax_handler() {
        check_ajax_referer( 'id-wheel-nonce', 'nonce' );
        $segment_index = isset($_POST['segment_index']) ? absint($_POST['segment_index']) : -1;
        $segments = !empty($this->options['segments']) ? $this->options['segments'] : $this->get_default_segments();
        if ( $segment_index < 0 || !isset($segments[$segment_index]) ) {
            wp_send_json_error( [ 'message' => 'Invalid segment.' ] );
        }
        $won_segment = $segments[$segment_index];
        if ($won_segment['type'] === 'none') {
            wp_send_json_success( [ 'coupon_code' => null, 'message' => __( 'Better luck next time!', 'interactive-discounts' ) ] );
        }
        $coupon_code = 'WHEEL-' . strtoupper( wp_generate_password( 8, false ) );
        $amount = $won_segment['value'];
        $discount_type = $won_segment['type'];
        $coupon = array('post_title' => $coupon_code, 'post_status' => 'publish', 'post_author' => 1, 'post_type' => 'shop_coupon');
        $new_coupon_id = wp_insert_post( $coupon );
        update_post_meta( $new_coupon_id, 'discount_type', $discount_type );
        update_post_meta( $new_coupon_id, 'coupon_amount', $amount );
        update_post_meta( $new_coupon_id, 'individual_use', 'yes' );
        update_post_meta( $new_coupon_id, 'usage_limit', '1' );
        update_post_meta( $new_coupon_id, 'expiry_date', date('Y-m-d', strtotime('+1 day')) );
        wp_send_json_success( [ 'coupon_code' => $coupon_code, 'message' => __( 'Congratulations! Your coupon code is:', 'interactive-discounts' ) ] );
    }

    public function save_email_ajax_handler() {
        check_ajax_referer( 'id-wheel-nonce', 'nonce' );

        if ( !isset($_POST['email']) || !is_email($_POST['email']) ) {
            wp_send_json_error( [ 'message' => 'Invalid email.' ] );
        }

        global $wpdb;
        $table_name = $wpdb->prefix . 'id_collected_emails';

        $wpdb->insert(
            $table_name,
            array(
                'time' => current_time( 'mysql' ),
                'email' => sanitize_email($_POST['email']),
            )
        );

        wp_send_json_success();
    }
}
