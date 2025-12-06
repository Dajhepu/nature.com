(function( $ ) {
    'use strict';

    $(function() {
        console.log('Smart Upsell Script yuklandi');
        console.log('AJAX URL:', smart_upsell_ajax.ajax_url);
        console.log('Nonce:', smart_upsell_ajax.nonce);

        // Upsell popupni ko'rsatish funksiyasi
        function showUpsellPopup($button) {
            console.log('=== SHOWING UPSELL POPUP ===');
            console.log('Button:', $button);

            // Remove any existing popups first
            $('#smart-upsell-popup').remove();

            // Har xil usulda product ID topish
            var product_id = $button.data('product_id') ||
                           $button.attr('data-product_id') ||
                           $button.val() ||
                           $button.attr('value');

            // Agar hali ham topilmasa, closest form ichidan qidirish
            if (!product_id) {
                var $form = $button.closest('form.cart');
                if ($form.length) {
                    product_id = $form.find('input[name="add-to-cart"]').val() ||
                               $form.find('button[name="add-to-cart"]').val();
                }
            }

            console.log('Product ID topildi:', product_id);
            console.log('Button attributes:', {
                'data-product_id': $button.data('product_id'),
                'attr-data-product_id': $button.attr('data-product_id'),
                'val': $button.val(),
                'value attr': $button.attr('value'),
                'html': $button[0] ? $button[0].outerHTML : 'no element'
            });

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
                    $('#smart-upsell-popup').css('display', 'flex').hide().fadeIn(300);
                    console.log('Popup ko\'rsatildi');
                } else {
                    console.warn('Server error yoki upsell topilmadi:', response.data);
                }
            }).fail(function(xhr, status, error) {
                console.error('AJAX xatosi:', status, error);
                console.error('Response:', xhr.responseText);
            });
        }

        // METOD 1: WooCommerce standart event
        $( document.body ).on( 'added_to_cart', function( event, fragments, cart_hash, $button ) {
            console.log('METHOD 1: added_to_cart event triggered');
            if ($button) showUpsellPopup($button);
        });

        // METOD 2: Button click event (direct method for AJAX buttons)
        var triggeringButton = null;
        $(document).on('click', '.ajax_add_to_cart', function(e) {
            console.log('METHOD 2: AJAX Add to cart button clicked');
            triggeringButton = $(this);
        });

        // METOD 3: AJAX complete event (backup)
        $(document).ajaxComplete(function(event, xhr, settings) {
            if ( settings.url && ( settings.url.indexOf('add-to-cart') > -1 || (settings.data && settings.data.indexOf('add-to-cart') > -1) ) ) {
                console.log('METHOD 3: AJAX add-to-cart call detected');
                if (triggeringButton) {
                     setTimeout(function() {
                        showUpsellPopup(triggeringButton);
                        triggeringButton = null;
                    }, 500);
                }
            }
        });

        // Popup yopish
        $( document ).on( 'click', '#smart-upsell-popup', function(e) {
            if (e.target === this) {
                e.preventDefault();
                console.log('Popup yopilmoqda (overlay click)...');
                $(this).fadeOut(300, function() { $(this).remove(); });
            }
        });
         $( document ).on( 'click', '#smart-upsell-popup .close-popup', function(e) {
             e.preventDefault();
             console.log('Popup yopilmoqda (close button)...');
             $('#smart-upsell-popup').fadeOut(300, function() { $(this).remove(); });
        });

        // Popup ichki content bosilganda yopilmasligi uchun
        $(document).on('click', '#smart-upsell-popup .smart-upsell-popup-content', function(e) {
            e.stopPropagation();
        });

        // Upsell qo'shish
        $( document ).on( 'click', '#smart-upsell-popup .add-to-cart-upsell', function(e) {
            e.preventDefault();
            var $thisbutton = $(this);
            $thisbutton.text('Adding...').prop('disabled', true);
            var data = { 'action': 'add_offer_to_cart', 'nonce': smart_upsell_ajax.nonce, 'product_id': $thisbutton.data('product-id'), 'rule_id': $thisbutton.data('rule-id') };
            $.post( smart_upsell_ajax.ajax_url, data, function( response ) {
                if (response.success) {
                    $('#smart-upsell-popup').fadeOut(300, function() { $(this).remove(); });
                    $(document.body).trigger('wc_fragment_refresh');
                } else {
                    $thisbutton.text('Add to Cart & Save!').prop('disabled', false);
                    alert('Error: Could not add item to cart.');
                }
            }).fail(function() {
                $thisbutton.text('Add to Cart & Save!').prop('disabled', false);
                alert('Connection error. Please try again.');
            });
        });

        // Cross-sell qo'shish
        $( document ).on( 'click', '.smart-cross-sell-product .add-to-order-cross-sell', function(e) {
            e.preventDefault();
            var $thisbutton = $(this);
            $thisbutton.text('Adding...').prop('disabled', true);
            var data = { 'action': 'add_offer_to_cart', 'nonce': smart_upsell_ajax.nonce, 'product_id': $thisbutton.data('product-id'), 'rule_id': $thisbutton.data('rule-id') };
            $.post( smart_upsell_ajax.ajax_url, data, function( response ) {
                if (response.success) {
                    $(document.body).trigger('update_checkout');
                    $thisbutton.closest('.smart-cross-sell-product').fadeOut(300, function() { $(this).remove(); });
                } else {
                     $thisbutton.text('Add to Order').prop('disabled', false);
                }
            });
        });

        // ESC tugmasi bilan yopish
        $(document).on('keydown', function(e) {
            if (e.key === 'Escape' || e.keyCode === 27) {
                $('#smart-upsell-popup').fadeOut(300, function() { $(this).remove(); });
            }
        });

        console.log('Barcha event listenerlar o\'rnatildi');
    });

})( jQuery );
