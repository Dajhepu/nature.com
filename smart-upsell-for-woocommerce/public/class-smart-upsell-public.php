<?php
/**
 * The public-facing functionality of the plugin.
 *
 * @link       https://example.com
 * @since      1.0.0
 *
 * @package    Smart_Upsell_For_Woocommerce
 * @subpackage Smart_Upsell_For_Woocommerce/public
 */

/**
 * The public-facing functionality of the plugin.
 *
 * Defines the plugin name, version, and two examples hooks for how to
 * enqueue the public-facing stylesheet and JavaScript.
 *
 * @package    Smart_Upsell_For_Woocommerce
 * @subpackage Smart_Upsell_For_Woocommerce/public
 * @author     Jules <jules@example.com>
 */
class Smart_Upsell_Public {

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
     * @param      string    $plugin_name       The name of the plugin.
     * @param      string    $version    The version of this plugin.
     */
    public function __construct( $plugin_name, $version ) {

        $this->plugin_name = $plugin_name;
        $this->version = $version;

    }

    /**
     * Register the stylesheets for the public-facing side of the site.
     *
     * @since    1.0.0
     */
    public function enqueue_styles() {

        wp_enqueue_style( $this->plugin_name, plugin_dir_url( __FILE__ ) . '../assets/css/smart-upsell-public.css', array(), $this->version, 'all' );

    }

    /**
     * Register the JavaScript for the public-facing side of the site.
     *
     * @since    1.0.0
     */
    public function enqueue_scripts() {

        wp_enqueue_script( $this->plugin_name, plugin_dir_url( __FILE__ ) . '../assets/js/smart-upsell-public.js', array( 'jquery' ), $this->version, false );

        wp_localize_script( $this->plugin_name, 'smart_upsell_ajax', array(
            'ajax_url' => admin_url( 'admin-ajax.php' ),
            'nonce'    => wp_create_nonce( 'smart-upsell-nonce' )
        ) );

    }

    /**
     * Add inline styles to the head.
     *
     * @since    1.0.0
     */
    public function add_inline_styles() {
        $options = get_option( 'smart_upsell_settings' );
        $bg_color = isset( $options['popup_bg_color'] ) ? $options['popup_bg_color'] : '#ffffff';
        $button_color = isset( $options['popup_button_color'] ) ? $options['popup_button_color'] : '#0073aa';

        $custom_css = "
            #smart-upsell-popup .smart-upsell-popup-content {
                background-color: {$bg_color};
            }
            #smart-upsell-popup .add-to-cart-upsell {
                background-color: {$button_color};
                color: #fff;
            }
        ";
        wp_add_inline_style( $this->plugin_name, $custom_css );
    }

    /**
     * AJAX handler for getting an upsell offer.
     *
     * @since    1.0.0
     */
    public function get_upsell_offer_ajax_handler() {
        check_ajax_referer( 'smart-upsell-nonce', 'nonce' );

        if ( ! isset( $_POST['product_id'] ) ) {
            wp_send_json_error();
        }

        $product_id = absint( $_POST['product_id'] );

        $product_categories = wc_get_product_term_ids( $product_id, 'product_cat' );

        $args = array(
            'post_type'      => 'smart_upsell_rule',
            'posts_per_page' => 1,
            'meta_query'     => array(
                'relation' => 'AND',
                array(
                    'key'     => '_offer_type',
                    'value'   => 'upsell',
                    'compare' => '=',
                ),
                array(
                    'relation' => 'OR',
                    array(
                        'key'     => '_trigger_product',
                        'value'   => $product_id,
                        'compare' => '=',
                    ),
                    array(
                        'key'     => '_trigger_category',
                        'value'   => $product_categories,
                        'compare' => 'IN',
                    ),
                    'key'     => '_trigger_product',
                    'value'   => $product_id,
                    'compare' => '=',
                ),
            ),
        );

        $rules = new WP_Query( $args );

        if ( $rules->have_posts() ) {
            $rules->the_post();
            $upsell_product_id = get_post_meta( get_the_ID(), '_upsell_product', true );
            $product = wc_get_product( $upsell_product_id );

            if ( $product ) {
                $discount_type = get_post_meta( get_the_ID(), '_discount_type', true );
                $discount_amount = get_post_meta( get_the_ID(), '_discount_amount', true );
                $price_html = $product->get_price_html();

                if ( 'none' !== $discount_type && ! empty( $discount_amount ) ) {
                    $price = $product->get_price();
                    if ( 'percentage' === $discount_type ) {
                        $new_price = $price - ( $price * ( $discount_amount / 100 ) );
                    } else {
                        $new_price = $price - $discount_amount;
                    }
                    $price_html = wc_format_sale_price( $price, $new_price );
                }

                ob_start();
                wc_get_template(
                    'popup-template.php',
                    array(
                        'product'    => $product,
                        'product_id' => $upsell_product_id,
                        'rule_id'    => get_the_ID(),
                        'price_html' => $price_html,
                    ),
                    'smart-upsell-for-woocommerce/',
                    plugin_dir_path( __FILE__ ) . 'partials/templates/'
                );
                $html = ob_get_clean();

                $options = get_option( 'smart_upsell_settings' );
                $popup_title = isset( $options['popup_title'] ) ? $options['popup_title'] : __( 'Don\'t miss this exclusive offer!', 'smart-upsell-for-woocommerce' );

                $response = array(
                    'product_id' => $upsell_product_id,
                    'rule_id'    => get_the_ID(),
                    'html'       => $html,
                    'title'      => $popup_title,
                );
                wp_send_json_success( $response );
            }
        }

        wp_send_json_error();
    }

    /**
     * AJAX handler for adding upsell to cart.
     *
     * @since    1.0.0
     */
    public function add_upsell_to_cart_ajax_handler() {
        check_ajax_referer( 'smart-upsell-nonce', 'nonce' );

        if ( ! isset( $_POST['product_id'] ) || ! isset( $_POST['rule_id'] ) ) {
            wp_send_json_error();
        }

        $product_id = absint( $_POST['product_id'] );
        $rule_id = absint( $_POST['rule_id'] );

        $this->record_event( $rule_id, 'click' );

        WC()->cart->add_to_cart( $product_id, 1, 0, array(), array( 'smart_upsell_rule_id' => $rule_id ) );
        WC()->cart->add_to_cart( $product_id );

        wp_send_json_success();

        wp_die();
    }

    /**
     * Apply the discount to the cart item.
     *
     * @since    1.0.0
     * @param    object    $cart    The cart object.
     */
    public function apply_discount( $cart ) {
        if ( is_admin() && ! defined( 'DOING_AJAX' ) ) {
            return;
        }

        foreach ( $cart->get_cart() as $cart_item ) {
            if ( isset( $cart_item['smart_upsell_rule_id'] ) ) {
                $rule_id = $cart_item['smart_upsell_rule_id'];
                $discount_type = get_post_meta( $rule_id, '_discount_type', true );
                $discount_amount = get_post_meta( $rule_id, '_discount_amount', true );

                if ( 'none' !== $discount_type && ! empty( $discount_amount ) ) {
                    $price = $cart_item['data']->get_price();
                    if ( 'percentage' === $discount_type ) {
                        $new_price = $price - ( $price * ( $discount_amount / 100 ) );
                    } else {
                        $new_price = $price - $discount_amount;
                    }
                    $cart_item['data']->set_price( $new_price );
                }
            }
        }
    }

    /**
     * Track the conversion.
     *
     * @since    1.0.0
     * @param    int    $order_id    The order ID.
     */
    public function track_conversion( $order_id ) {
        $order = wc_get_order( $order_id );
        $items = $order->get_items();

        foreach ( $items as $item ) {
            $rule_id = wc_get_order_item_meta( $item->get_id(), '_smart_upsell_rule_id', true );
            if ( $rule_id ) {
                $current_revenue = get_post_meta( $rule_id, '_revenue', true );
                if ( empty( $current_revenue ) ) {
                    $current_revenue = 0;
                }
                update_post_meta( $rule_id, '_revenue', $current_revenue + $item->get_total() );
            }
        }
    }

    /**
     * Add custom meta to order item.
     *
     * @since 1.0.0
     * @param WC_Order_Item_Product $item
     * @param string $cart_item_key
     * @param array $values
     * @param WC_Order $order
     */
    public function add_custom_meta_to_order_item( $item, $cart_item_key, $values, $order ) {
        if ( isset( $values['smart_upsell_rule_id'] ) ) {
            $item->add_meta_data( '_smart_upsell_rule_id', $values['smart_upsell_rule_id'], true );
        }
    }

    /**
     * Display cross-sell products on the checkout page.
     *
     * @since    1.0.0
     */
    public function display_cross_sell_products() {
        if ( ! is_checkout() ) {
            return;
        }

        $cart = WC()->cart->get_cart();
        $cross_sell_products = array();

        foreach ( $cart as $cart_item ) {
            $product_id = $cart_item['product_id'];
            $product_categories = wc_get_product_term_ids( $product_id, 'product_cat' );

            $args = array(
                'post_type'      => 'smart_upsell_rule',
                'posts_per_page' => -1,
                'meta_query'     => array(
                    'relation' => 'AND',
                    array(
                        'key'     => '_offer_type',
                        'value'   => 'cross-sell',
                        'compare' => '=',
                    ),
                    array(
                        'relation' => 'OR',
                        array(
                            'key'     => '_trigger_product',
                            'value'   => $product_id,
                            'compare' => '=',
                        ),
                        array(
                            'key'     => '_trigger_category',
                            'value'   => $product_categories,
                            'compare' => 'IN',
                        ),
                        'key'     => '_trigger_product',
                        'value'   => $product_id,
                        'compare' => '=',
                    ),
                ),
            );

            $rules = new WP_Query( $args );

            if ( $rules->have_posts() ) {
                while ( $rules->have_posts() ) {
                    $rules->the_post();
                    $cross_sell_product_id = get_post_meta( get_the_ID(), '_upsell_product', true );
                    if ( ! in_array( $cross_sell_product_id, $cross_sell_products ) ) {
                        $cross_sell_products[] = get_the_ID();
                    }
                }
            }

            wp_reset_postdata();
        }

        if ( empty( $cross_sell_products ) ) {
            return;
        }

        echo '<div class="smart-cross-sell-container">';
        echo '<h2>' . esc_html__( 'You might also like...', 'smart-upsell-for-woocommerce' ) . '</h2>';
        foreach ( $cross_sell_products as $rule_id ) {
            $product_id = get_post_meta( $rule_id, '_upsell_product', true );
            $product_id = get_post_meta( $rule_id, '_cross_sell_product', true );
            $product = wc_get_product( $product_id );
            if ( $product ) {
                echo '<div class="smart-cross-sell-product">';
                echo $product->get_image();
                echo '<h3>' . $product->get_name() . '</h3>';
                echo '<p class="price">' . $product->get_price_html() . '</p>';
                echo '<button class="add-to-order-cross-sell" data-product-id="' . esc_attr( $product_id ) . '" data-rule-id="' . esc_attr( $rule_id ) . '">' . esc_html__( 'Add to Order', 'smart-upsell-for-woocommerce' ) . '</button>';
                echo '</div>';
                $this->record_event( $rule_id, 'impression' );
            }
        }
        echo '</div>';
    }

    /**
     * AJAX handler for adding cross-sell to order.
     *
     * @since    1.0.0
     */
    public function add_cross_sell_to_order_ajax_handler() {
        check_ajax_referer( 'smart-upsell-nonce', 'nonce' );

        if ( ! isset( $_POST['product_id'] ) || ! isset( $_POST['rule_id'] ) ) {
            wp_send_json_error();
        }

        $product_id = absint( $_POST['product_id'] );
        $rule_id = absint( $_POST['rule_id'] );

        $this->record_event( $rule_id, 'click' );

        WC()->cart->add_to_cart( $product_id, 1, 0, array(), array( 'smart_upsell_rule_id' => $rule_id ) );
        WC()->cart->add_to_cart( $product_id );

        wp_send_json_success();

        wp_die();
    }

    /**
     * Record an event in the stats table.
     *
     * @since    1.0.0
     * @param    int      $offer_id      The offer ID.
     * @param    string   $event_type    The event type (e.g., 'impression', 'click').
     */
    private function record_event( $offer_id, $event_type ) {
        global $wpdb;

        $table_name = $wpdb->prefix . 'smart_upsell_stats';

        $wpdb->insert(
            $table_name,
            array(
                'time'       => current_time( 'mysql' ),
                'offer_id'   => $offer_id,
                'event_type' => $event_type,
            )
        );
    }

}
