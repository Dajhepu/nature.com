(function( $ ) {
    'use strict';

    $(function() {
        console.log('Smart Upsell Script yuklandi');
        console.log('AJAX URL:', smart_upsell_ajax.ajax_url);
        console.log('Nonce:', smart_upsell_ajax.nonce);

        // WooCommerce "added_to_cart" eventini tinglash
        $( document.body ).on( 'added_to_cart', function( event, fragments, cart_hash, $button ) {
            console.log('=== ADDED TO CART EVENT TRIGGERED ===');
            console.log('Event:', event);
            console.log('Button:', $button);

            // Remove any existing popups first
            $('#smart-upsell-popup').remove();

            // Theme compatibility: Find product ID from data attribute first, then from value attribute.
            var product_id = $button.data('product_id');
            if ( ! product_id ) {
                product_id = $button.val();
            }

            if ( ! product_id ) {
                product_id = $button.attr('value');
            }

            console.log('Final Product ID:', product_id);

            if (!product_id) {
                console.warn('Product ID topilmadi!');
                return;
            }

            var data = {
                'action': 'get_upsell_offer',
                'nonce': smart_upsell_ajax.nonce,
                'product_id': product_id
            };

            console.log('AJAX request yuborilmoqda:', data);

            $.post( smart_upsell_ajax.ajax_url, data, function( response ) {
                console.log('AJAX response:', response);

                if ( response.success ) {
                    console.log('Success! HTML qo\'shilmoqda...');
                    $('body').append(response.data.html);
                    $('#smart-upsell-popup .popup-title').text(response.data.title);
                    $('#smart-upsell-popup').css('display', 'flex');
                    console.log('Popup ko\'rsatildi');
                } else {
                    console.warn('Server error yoki upsell topilmadi');
                }
            }).fail(function(xhr, status, error) {
                console.error('AJAX xatosi:', status, error);
                console.error('Response:', xhr.responseText);
            });
        });

        // Popup yopish
        $( document ).on( 'click', '#smart-upsell-popup .close-popup', function(e) {
            e.preventDefault();
            console.log('Popup yopilmoqda...');
            $('#smart-upsell-popup').remove();
        });

        // Upsell qo'shish
        $( document ).on( 'click', '#smart-upsell-popup .add-to-cart-upsell', function(e) {
            e.preventDefault();
            var $thisbutton = $(this);
            console.log('Upsell mahsulot qo\'shilmoqda...');
            $thisbutton.text('Adding...').prop('disabled', true);

            var data = {
                'action': 'add_offer_to_cart',
                'nonce': smart_upsell_ajax.nonce,
                'product_id': $thisbutton.data('product-id'),
                'rule_id': $thisbutton.data('rule-id')
            };

            console.log('Add to cart request:', data);

            $.post( smart_upsell_ajax.ajax_url, data, function( response ) {
                console.log('Add to cart response:', response);
                if (response.success) {
                    $('#smart-upsell-popup').remove();
                    $(document.body).trigger('wc_fragment_refresh');
                    console.log('Mahsulot muvaffaqiyatli qo\'shildi!');
                } else {
                    $thisbutton.text('Add to Cart & Save!').prop('disabled', false);
                    console.error('Mahsulot qo\'shishda xatolik');
                }
            }).fail(function(xhr, status, error) {
                console.error('AJAX xatosi:', status, error);
                $thisbutton.text('Add to Cart & Save!').prop('disabled', false);
            });
        });

        // Cross-sell qo'shish
        $( document ).on( 'click', '.smart-cross-sell-product .add-to-order-cross-sell', function(e) {
            e.preventDefault();
            var $thisbutton = $(this);
            console.log('Cross-sell mahsulot qo\'shilmoqda...');
            $thisbutton.text('Adding...').prop('disabled', true);

            var data = {
                'action': 'add_offer_to_cart',
                'nonce': smart_upsell_ajax.nonce,
                'product_id': $thisbutton.data('product-id'),
                'rule_id': $thisbutton.data('rule-id')
            };

            $.post( smart_upsell_ajax.ajax_url, data, function( response ) {
                console.log('Cross-sell response:', response);
                if (response.success) {
                    $(document.body).trigger('update_checkout');
                    $thisbutton.closest('.smart-cross-sell-product').fadeOut(300, function() { $(this).remove(); });
                } else {
                     $thisbutton.text('Add to Order').prop('disabled', false);
                }
            });
        });

        // Test uchun manual trigger
        console.log('Manual test uchun: smartUpsellTest() funksiyasini chaqiring');
        window.smartUpsellTest = function() {
            var $button = $('.single_add_to_cart_button').first();
            console.log('Test button:', $button);
            $(document.body).trigger('added_to_cart', [null, null, $button]);
        };
    });

})( jQuery );
