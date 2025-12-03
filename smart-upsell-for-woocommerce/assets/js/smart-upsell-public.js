(function( $ ) {
    'use strict';

    $( document ).ready(function() {
        $( document.body ).on( 'added_to_cart', function( fragments, cart_hash, $button ) {
            var product_id = $button.data( 'product_id' );

            var data = {
                'action': 'get_upsell_offer',
                'nonce': smart_upsell_ajax.nonce,
                'product_id': product_id
            };

            $.post( smart_upsell_ajax.ajax_url, data, function( response ) {
                if ( response.success ) {
                    $( 'body' ).append( response.data.html );
                    $( '#smart-upsell-popup' ).show();
                }
            });
        });

        $( document ).on( 'click', '.close-popup', function() {
            $( '#smart-upsell-popup' ).remove();
        });

        $( document ).on( 'click', '.add-to-cart-upsell', function() {
            var $thisbutton = $( this );
            var data = {
                'action': 'add_upsell_to_cart',
                'nonce': smart_upsell_ajax.nonce,
                'product_id': $thisbutton.data( 'product-id' ),
                'rule_id': $thisbutton.data( 'rule-id' )
            };

            $.post( smart_upsell_ajax.ajax_url, data, function( response ) {
                $( '#smart-upsell-popup' ).remove();
                $( document.body ).trigger( 'wc_fragment_refresh' );
            });
        });

        $( document ).on( 'click', '.add-to-order-cross-sell', function() {
            var $thisbutton = $( this );
            var data = {
                'action': 'add_cross_sell_to_order',
                'nonce': smart_upsell_ajax.nonce,
                'product_id': $thisbutton.data( 'product-id' ),
                'rule_id': $thisbutton.data( 'rule-id' )
            };

            $.post( smart_upsell_ajax.ajax_url, data, function( response ) {
                $( document.body ).trigger( 'update_checkout' );
            });
        });
    });

})( jQuery );
