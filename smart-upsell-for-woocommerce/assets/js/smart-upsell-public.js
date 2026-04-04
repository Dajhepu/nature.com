(function( $ ) {
    'use strict';

    $(function() {
        $( document.body ).on( 'added_to_cart', function( fragments, cart_hash, $button ) {
            // Remove any existing popups first
            $('#smart-upsell-popup').remove();

            var product_id = $button.data('product_id');
            if (!product_id) return;

            var data = {
                'action': 'get_upsell_offer',
                'nonce': smart_upsell_ajax.nonce,
                'product_id': product_id
            };

            $.post( smart_upsell_ajax.ajax_url, data, function( response ) {
                if ( response.success ) {
                    $('body').append(response.data.html);
                    $('#smart-upsell-popup .popup-title').text(response.data.title);
                    $('#smart-upsell-popup').show();
                }
            });
        });

        $( document ).on( 'click', '#smart-upsell-popup .close-popup', function(e) {
            e.preventDefault();
            $('#smart-upsell-popup').remove();
        });

        $( document ).on( 'click', '#smart-upsell-popup .add-to-cart-upsell', function(e) {
            e.preventDefault();
            var $thisbutton = $(this);
            $thisbutton.text('Adding...').prop('disabled', true);

            var data = {
                'action': 'ajax_add_to_cart',
                'nonce': smart_upsell_ajax.nonce,
                'product_id': $thisbutton.data('product-id'),
                'rule_id': $thisbutton.data('rule-id')
            };

            $.post( smart_upsell_ajax.ajax_url, data, function( response ) {
                if (response.success) {
                    $('#smart-upsell-popup').remove();
                    $(document.body).trigger('wc_fragment_refresh');
                } else {
                    $thisbutton.text('Add to Cart & Save!').prop('disabled', false);
                }
            });
        });

        $( document ).on( 'click', '.smart-cross-sell-product .add-to-order-cross-sell', function(e) {
            e.preventDefault();
            var $thisbutton = $(this);
            $thisbutton.text('Adding...').prop('disabled', true);

            var data = {
                'action': 'ajax_add_to_cart',
                'nonce': smart_upsell_ajax.nonce,
                'product_id': $thisbutton.data('product-id'),
                'rule_id': $thisbutton.data('rule-id')
            };

            $.post( smart_upsell_ajax.ajax_url, data, function( response ) {
                if (response.success) {
                    $(document.body).trigger('update_checkout');
                    $thisbutton.closest('.smart-cross-sell-product').fadeOut(300, function() { $(this).remove(); });
                } else {
                     $thisbutton.text('Add to Order').prop('disabled', false);
                }
            });
        });
    });

})( jQuery );
