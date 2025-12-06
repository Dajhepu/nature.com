<?php
if ( ! defined( 'ABSPATH' ) ) exit;
?>
<div id="smart-upsell-popup" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); z-index: 100000; align-items: center; justify-content: center;">
    <div class="smart-upsell-popup-content" style="background: #fff; padding: 30px; border-radius: 5px; text-align: center; max-width: 400px; position: relative;">
        <button class="close-popup" style="position: absolute; top: 10px; right: 10px; border: none; background: transparent; font-size: 20px; cursor: pointer;">&times;</button>
        <h2 class="popup-title"></h2>
        <div class="product" style="margin: 20px 0;">
            <?php echo $product->get_image('woocommerce_thumbnail'); ?>
            <h3><?php echo esc_html($product->get_name()); ?></h3>
            <p class="price"><?php echo $price_html; ?></p>
        </div>
        <button class="add-to-cart-upsell" data-product-id="<?php echo esc_attr( $product_id ); ?>" data-rule-id="<?php echo esc_attr( $rule_id ); ?>"><?php echo esc_html__( 'Add to Cart & Save!', 'smart-upsell-for-woocommerce' ); ?></button>
    </div>
</div>
