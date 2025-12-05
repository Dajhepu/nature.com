<?php
if ( ! defined( 'ABSPATH' ) ) exit;
?>
<div class="smart-cross-sell-product" style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 15px; border: 1px solid #eee; padding: 10px;">
    <div style="display: flex; align-items: center;">
        <?php echo $product->get_image('woocommerce_gallery_thumbnail'); ?>
        <div style="margin-left: 15px;">
            <h4><?php echo esc_html($product->get_name()); ?></h4>
            <p class="price" style="margin: 0;"><?php echo $price_html; ?></p>
        </div>
    </div>
    <button class="add-to-order-cross-sell" data-product-id="<?php echo esc_attr( $product_id ); ?>" data-rule-id="<?php echo esc_attr( $rule_id ); ?>"><?php echo esc_html__( 'Add to Order', 'smart-upsell-for-woocommerce' ); ?></button>
</div>
