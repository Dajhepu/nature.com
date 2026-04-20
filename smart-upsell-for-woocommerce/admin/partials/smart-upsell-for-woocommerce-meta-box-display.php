<?php
$offer_type = get_post_meta( $post->ID, '_offer_type', true );
$trigger_type = get_post_meta( $post->ID, '_trigger_type', true );
$trigger_product_id = get_post_meta( $post->ID, '_trigger_product', true );
$trigger_category_id = get_post_meta( $post->ID, '_trigger_category', true );
$upsell_product_id = get_post_meta( $post->ID, '_upsell_product', true );
$discount_type = get_post_meta( $post->ID, '_discount_type', true );
$discount_amount = get_post_meta( $post->ID, '_discount_amount', true );
?>
<table class="form-table">
    <tbody>
        <tr>
            <th><label for="offer_type"><?php esc_html_e( 'Offer Type', 'smart-upsell-for-woocommerce' ); ?></label></th>
            <td>
                <select name="offer_type" id="offer_type">
                    <option value="upsell" <?php selected( $offer_type, 'upsell' ); ?>><?php esc_html_e( 'Upsell', 'smart-upsell-for-woocommerce' ); ?></option>
                    <option value="cross-sell" <?php selected( $offer_type, 'cross-sell' ); ?>><?php esc_html_e( 'Cross-sell', 'smart-upsell-for-woocommerce' ); ?></option>
                </select>
            </td>
        </tr>
        <tr>
            <th><label for="trigger_type"><?php esc_html_e( 'Trigger Type', 'smart-upsell-for-woocommerce' ); ?></label></th>
            <td>
                <select name="trigger_type" id="trigger_type">
                    <option value="product" <?php selected( $trigger_type, 'product' ); ?>><?php esc_html_e( 'Specific Product', 'smart-upsell-for-woocommerce' ); ?></option>
                    <option value="category" <?php selected( $trigger_type, 'category' ); ?>><?php esc_html_e( 'Product Category', 'smart-upsell-for-woocommerce' ); ?></option>
                </select>
            </td>
        </tr>
        <tr class="trigger_product_field">
            <th><label for="trigger_product"><?php esc_html_e( 'Trigger Product', 'smart-upsell-for-woocommerce' ); ?></label></th>
            <td>
                <select class="wc-product-search" name="trigger_product" id="trigger_product" data-placeholder="<?php esc_attr_e( 'Search for a product…', 'smart-upsell-for-woocommerce' ); ?>" data-action="woocommerce_json_search_products_and_variations" data-multiple="false" style="width: 50%;">
                    <?php if ( $trigger_product_id && ( $product = wc_get_product( $trigger_product_id ) ) ) : ?>
                        <option value="<?php echo esc_attr( $trigger_product_id ); ?>" selected="selected"><?php echo esc_html( $product->get_formatted_name() ); ?></option>
                    <?php endif; ?>
                </select>
            </td>
        </tr>
        <tr class="trigger_category_field" style="display:none;">
            <th><label for="trigger_category"><?php esc_html_e( 'Trigger Category', 'smart-upsell-for-woocommerce' ); ?></label></th>
            <td>
                <select name="trigger_category" id="trigger_category">
                    <?php
                    $categories = get_terms( 'product_cat', [ 'hide_empty' => false ] );
                    foreach ( $categories as $category ) {
                        echo '<option value="' . esc_attr( $category->term_id ) . '" ' . selected( $trigger_category_id, $category->term_id, false ) . '>' . esc_html( $category->name ) . '</option>';
                    }
                    ?>
                </select>
            </td>
        </tr>
        <tr>
            <th><label for="upsell_product"><?php esc_html_e( 'Offer Product', 'smart-upsell-for-woocommerce' ); ?></label></th>
            <td>
                <select class="wc-product-search" name="upsell_product" id="upsell_product" data-placeholder="<?php esc_attr_e( 'Search for a product…', 'smart-upsell-for-woocommerce' ); ?>" data-action="woocommerce_json_search_products_and_variations" data-multiple="false" style="width: 50%;">
                    <?php if ( $upsell_product_id && ( $product = wc_get_product( $upsell_product_id ) ) ) : ?>
                        <option value="<?php echo esc_attr( $upsell_product_id ); ?>" selected="selected"><?php echo esc_html( $product->get_formatted_name() ); ?></option>
                    <?php endif; ?>
                </select>
            </td>
        </tr>
        <tr>
            <th><label for="discount_type"><?php esc_html_e( 'Discount Type', 'smart-upsell-for-woocommerce' ); ?></label></th>
            <td>
                <select name="discount_type" id="discount_type">
                    <option value="none" <?php selected( $discount_type, 'none' ); ?>><?php esc_html_e( 'None', 'smart-upsell-for-woocommerce' ); ?></option>
                    <option value="percentage" <?php selected( $discount_type, 'percentage' ); ?>><?php esc_html_e( 'Percentage', 'smart-upsell-for-woocommerce' ); ?></option>
                    <option value="fixed" <?php selected( $discount_type, 'fixed' ); ?>><?php esc_html_e( 'Fixed Amount', 'smart-upsell-for-woocommerce' ); ?></option>
                </select>
            </td>
        </tr>
        <tr>
            <th><label for="discount_amount"><?php esc_html_e( 'Discount Amount', 'smart-upsell-for-woocommerce' ); ?></label></th>
            <td><input type="number" name="discount_amount" id="discount_amount" value="<?php echo esc_attr( $discount_amount ); ?>" step="0.01" /></td>
        </tr>
    </tbody>
</table>
<script type="text/javascript">
    jQuery(document).ready(function($) {
        function toggleTriggerFields() {
            var triggerType = $('#trigger_type').val();
            if (triggerType === 'product') {
                $('.trigger_product_field').show();
                $('.trigger_category_field').hide();
            } else {
                $('.trigger_product_field').hide();
                $('.trigger_category_field').show();
            }
        }
        toggleTriggerFields();
        $('#trigger_type').on('change', toggleTriggerFields);
    });
</script>
