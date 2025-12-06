<?php
/**
 * The public-facing functionality of the plugin.
 */
class Smart_Upsell_Public {

    private $plugin_name;
    private $version;

    public function __construct( $plugin_name, $version ) {
        $this->plugin_name = $plugin_name;
        $this->version = $version;
    }

    public function enqueue_styles() {
        wp_enqueue_style( $this->plugin_name, plugin_dir_url( __FILE__ ) . '../assets/css/smart-upsell-public.css', [], $this->version, 'all' );
    }

    public function enqueue_scripts() {
        wp_enqueue_script( $this->plugin_name, plugin_dir_url( __FILE__ ) . '../assets/js/smart-upsell-public.js', [ 'jquery' ], $this->version, false );
        wp_localize_script( $this->plugin_name, 'smart_upsell_ajax', [ 'ajax_url' => admin_url( 'admin-ajax.php' ), 'nonce' => wp_create_nonce( 'smart-upsell-nonce' ) ] );
    }

    public function add_inline_styles() {
        $options = get_option( 'smart_upsell_settings', [] );
        $bg_color = !empty( $options['popup_bg_color'] ) ? $options['popup_bg_color'] : '#ffffff';
        $button_color = !empty( $options['popup_button_color'] ) ? $options['popup_button_color'] : '#0073aa';
        $custom_css = "
            #smart-upsell-popup .smart-upsell-popup-content { background-color: {$bg_color}; }
            #smart-upsell-popup .add-to-cart-upsell, .smart-cross-sell-product .add-to-order-cross-sell { background-color: {$button_color}; color: #fff; border: none; padding: 10px 15px; cursor: pointer; }
        ";
        wp_add_inline_style( $this->plugin_name, $custom_css );
    }

    public function get_upsell_offer_ajax_handler() {
        check_ajax_referer( 'smart-upsell-nonce', 'nonce' );
        $product_id = isset( $_POST['product_id'] ) ? absint( $_POST['product_id'] ) : 0;
        if ( !$product_id ) wp_send_json_error();

        $product_categories = wc_get_product_term_ids( $product_id, 'product_cat' );
        $args = $this->get_query_args( 'upsell', $product_id, $product_categories );
        $rules = new WP_Query( $args );

        if ( $rules->have_posts() ) {
            $rules->the_post();
            $rule_id = get_the_ID();
            $upsell_product_id = get_post_meta( $rule_id, '_upsell_product', true );
            if ( $product = wc_get_product( $upsell_product_id ) ) {
                $price_html = $this->get_discounted_price_html( $product, $rule_id );

                ob_start();
                wc_get_template( 'popup-template.php', [ 'product' => $product, 'product_id' => $upsell_product_id, 'rule_id' => $rule_id, 'price_html' => $price_html ], 'smart-upsell-for-woocommerce/', plugin_dir_path( __FILE__ ) . 'partials/templates/' );
                $html = ob_get_clean();

                $options = get_option( 'smart_upsell_settings', [] );
                $popup_title = !empty( $options['popup_title'] ) ? $options['popup_title'] : __( 'Don\'t miss this exclusive offer!', 'smart-upsell-for-woocommerce' );

                wp_send_json_success( [ 'rule_id' => $rule_id, 'html' => $html, 'title' => $popup_title ] );
            }
        }
        wp_reset_postdata();
        wp_send_json_error();
    }

    public function add_offer_to_cart_ajax_handler() {
        check_ajax_referer( 'smart-upsell-nonce', 'nonce' );
        $product_id = isset( $_POST['product_id'] ) ? absint( $_POST['product_id'] ) : 0;
        $rule_id = isset( $_POST['rule_id'] ) ? absint( $_POST['rule_id'] ) : 0;
        if ( !$product_id || !$rule_id ) wp_send_json_error();

        $this->record_event( $rule_id, 'click' );
        WC()->cart->add_to_cart( $product_id, 1, 0, [], [ 'smart_upsell_rule_id' => $rule_id ] );
        wp_send_json_success();
    }

    public function apply_discount( $cart ) {
        if ( ( is_admin() && ! defined( 'DOING_AJAX' ) ) ) return;
        foreach ( $cart->get_cart() as $cart_item ) {
            if ( isset( $cart_item['smart_upsell_rule_id'] ) ) {
                $rule_id = $cart_item['smart_upsell_rule_id'];
                $product = $cart_item['data'];
                $discounted_price = $this->get_discounted_price( $product, $rule_id );
                if ( $discounted_price !== null ) {
                    $product->set_price( $discounted_price );
                }
            }
        }
    }

    public function track_conversion( $order_id ) {
        if ( !$order = wc_get_order( $order_id ) ) return;
        foreach ( $order->get_items() as $item ) {
            $rule_id = wc_get_order_item_meta( $item->get_id(), '_smart_upsell_rule_id', true );
            if ( $rule_id ) {
                $this->record_event($rule_id, 'conversion');
                $current_revenue = get_post_meta( $rule_id, '_revenue', true );
                update_post_meta( $rule_id, '_revenue', floatval( $current_revenue ) + $item->get_total() );
            }
        }
    }

    public function add_custom_meta_to_order_item( $item, $cart_item_key, $values, $order ) {
        if ( isset( $values['smart_upsell_rule_id'] ) ) {
            $item->add_meta_data( '_smart_upsell_rule_id', $values['smart_upsell_rule_id'], true );
        }
    }

    public function display_cross_sell_products() {
        if ( ! is_checkout() || WC()->cart->is_empty() ) return;

        $cross_sell_rules = [];
        foreach ( WC()->cart->get_cart() as $cart_item ) {
            $product_id = $cart_item['product_id'];
            $product_categories = wc_get_product_term_ids( $product_id, 'product_cat' );
            $args = $this->get_query_args( 'cross-sell', $product_id, $product_categories );
            $rules = new WP_Query( $args );
            if ( $rules->have_posts() ) {
                 while ( $rules->have_posts() ) {
                    the_post();
                    $cross_sell_rules[get_the_ID()] = get_post_meta( get_the_ID(), '_upsell_product', true );
                }
            }
            wp_reset_postdata();
        }

        if ( empty( $cross_sell_rules ) ) return;

        echo '<div class="smart-cross-sell-container"><h2>' . esc_html__( 'You might also like...', 'smart-upsell-for-woocommerce' ) . '</h2>';
        foreach ( $cross_sell_rules as $rule_id => $product_id ) {
            if ( $product = wc_get_product( $product_id ) ) {
                $this->record_event( $rule_id, 'impression' );
                $price_html = $this->get_discounted_price_html($product, $rule_id);
                wc_get_template( 'cross-sell-item.php', [ 'product' => $product, 'product_id' => $product_id, 'rule_id' => $rule_id, 'price_html' => $price_html ], 'smart-upsell-for-woocommerce/', plugin_dir_path( __FILE__ ) . 'partials/templates/' );
            }
        }
        echo '</div>';
    }

    private function get_query_args($offer_type, $product_id, $categories) {
        return [
            'post_type' => 'smart_upsell_rule',
            'posts_per_page' => -1,
            'meta_query' => [
                'relation' => 'AND',
                [ 'key' => '_offer_type', 'value' => $offer_type, 'compare' => '=' ],
                [
                    'relation' => 'OR',
                    [ 'key' => '_trigger_product', 'value' => $product_id, 'compare' => '=' ],
                    [ 'key' => '_trigger_category', 'value' => $categories, 'compare' => 'IN' ]
                ]
            ]
        ];
    }

    private function get_discounted_price($product, $rule_id) {
        $discount_type = get_post_meta( $rule_id, '_discount_type', true );
        $discount_amount = get_post_meta( $rule_id, '_discount_amount', true );
        if ( 'none' !== $discount_type && ! empty( $discount_amount ) ) {
            $price = floatval($product->get_price());
            if ( 'percentage' === $discount_type ) return $price - ( $price * ( floatval($discount_amount) / 100 ) );
            if ( 'fixed' === $discount_type ) return $price - floatval($discount_amount);
        }
        return null;
    }

    private function get_discounted_price_html($product, $rule_id) {
        $new_price = $this->get_discounted_price($product, $rule_id);
        if ($new_price !== null) {
            return wc_format_sale_price( $product->get_price(), $new_price );
        }
        return $product->get_price_html();
    }

    private function record_event( $offer_id, $event_type ) {
        global $wpdb;
        $table_name = $wpdb->prefix . 'smart_upsell_stats';
        $wpdb->insert( $table_name, [ 'time' => current_time( 'mysql' ), 'offer_id' => $offer_id, 'event_type' => $event_type ] );
    }
}
