<?php
/**
 * Upsell Popup Template
 *
 * @package    Smart_Upsell_For_Woocommerce
 * @subpackage Smart_Upsell_For_Woocommerce/public/partials/templates
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit; // Exit if accessed directly.
}

?>
<div id="smart-upsell-popup" style="display:none;">
    <div class="smart-upsell-popup-content">
        <h2 class="popup-title"></h2>
        <div class="product">
            <?php echo $product->get_image(); ?>
            <h3><?php echo $product->get_name(); ?></h3>
            <p class="price"><?php echo $price_html; ?></p>
        </div>
        <button class="add-to-cart-upsell" data-product-id="<?php echo esc_attr( $product_id ); ?>" data-rule-id="<?php echo esc_attr( $rule_id ); ?>"><?php echo esc_html__( 'Add to Cart', 'smart-upsell-for-woocommerce' ); ?></button>
        <button class="close-popup"><?php echo esc_html__( 'No, thanks', 'smart-upsell-for-woocommerce' ); ?></button>
    </div>
</div>
