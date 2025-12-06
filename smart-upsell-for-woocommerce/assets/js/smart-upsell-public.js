(function( $ ) {
    'use strict';

    $(function() {
        console.log('Smart Upsell Script yuklandi');
        console.log('AJAX URL:', smart_upsell_ajax.ajax_url);
        console.log('Nonce:', smart_upsell_ajax.nonce);

        // Upsell popupni ko'rsatish funksiyasi
        function showUpsellPopup($button) {
            console.log('=== SHOWING UPSELL POPUP ===');

            var $popupWrapper = $('#smart-upsell-popup-wrapper');
            // Clear previous content
            $popupWrapper.html('').hide();

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
                    console.log('Success! HTML o\'rnatilmoqda...');
                    var $popupWrapper = $('#smart-upsell-popup-wrapper');
                    $popupWrapper.html(response.data.html);
                    $popupWrapper.find('.popup-title').text(response.data.title);
                    $popupWrapper.css('display', 'flex').hide().fadeIn(300); // Wrapper ko'rsatiladi
                    console.log('Popup ko\'rsatildi');
                } else {
                    console.warn('Upsell topilmadi yoki xato:', response.data);
                }
            }).fail(function(xhr, status, error) {
                console.error('AJAX xatosi:', status, error);
            });
        }

        // METOD 1: WooCommerce standart event
        $( document.body ).on( 'added_to_cart', function( event, fragments, cart_hash, $button ) {
            console.log('METHOD 1: added_to_cart event triggered');
            if ($button) showUpsellPopup($button);
        });

        // METHOD 6: Block Theme Support
        document.body.addEventListener('wc-blocks_added_to_cart', function(event) {
            console.log('METHOD 6: wc-blocks_added_to_cart event triggered');

            // For block themes, the product ID is not in the event.
            // We need to find it in the page's form.
            var $form = $('form.cart');
            var product_id = $form.find('input[name="add-to-cart"]').val() ||
                             $form.find('button[name="add-to-cart"]').val();

            if (product_id) {
                 // We don't have a real button, so we create a fake one to pass the ID.
                var $fakeButton = $('<button>').data('product_id', product_id);
                showUpsellPopup($fakeButton);
            } else {
                console.warn('Block theme event fired, but could not find product ID in the form.');
            }
        });

        // METOD 3: Direct button click listener (ASOSIY YECHIM)
        var lastClickedButton = null;
        var addToCartInProgress = false;

        $(document).on('click', '.single_add_to_cart_button, .add_to_cart_button', function(e) {
            var $button = $(this);
            console.log('METHOD 3: Add to cart button clicked');

            // Button ma'lumotlarini saqlaymiz
            lastClickedButton = $button;
            addToCartInProgress = true;

            console.log('Button saqlab qo\'yildi:', {
                'product_id': $button.data('product_id') || $button.val(),
                'class': $button.attr('class')
            });
        });

        // METOD 4: AJAX Complete listener (MAIN SOLUTION)
        $(document).ajaxComplete(function(event, xhr, settings) {
            // Faqat WooCommerce add-to-cart AJAX so'rovlarini tutamiz
            if (settings.data && typeof settings.data === 'string' &&
                (settings.data.indexOf('action=woocommerce_add_to_cart') > -1 ||
                 settings.data.indexOf('add-to-cart=') > -1)) {

                console.log('METHOD 4: WooCommerce AJAX add-to-cart complete');

                // Response success bo'lganini tekshiramiz
                try {
                    var response = JSON.parse(xhr.responseText);
                    if (response && !response.error) {
                        console.log('Cart muvaffaqiyatli yangilandi');

                        // Biroz kutamiz (cart yangilanishi uchun)
                        setTimeout(function() {
                            if (lastClickedButton && addToCartInProgress) {
                                console.log('Upsell popup ko\'rsatilmoqda...');
                                showUpsellPopup(lastClickedButton);
                                addToCartInProgress = false;
                            }
                        }, 500);
                    }
                } catch (e) {
                    // JSON parse error - maybe not JSON response
                    console.log('Response JSON emas, upsell ko\'rsatilmoqda...');
                    if (lastClickedButton && addToCartInProgress) {
                        setTimeout(function() {
                            showUpsellPopup(lastClickedButton);
                            addToCartInProgress = false;
                        }, 500);
                    }
                }
            }

            // URL parametridagi add-to-cart ni ham tekshiramiz
            if (settings.url && settings.url.indexOf('add-to-cart=') > -1) {
                console.log('METHOD 4b: URL-based add-to-cart detected');

                var urlParams = new URLSearchParams(settings.url.split('?')[1]);
                var product_id = urlParams.get('add-to-cart');

                if (product_id) {
                    console.log('Product ID URL dan olindi:', product_id);
                    var $fakeButton = $('<button>').data('product_id', product_id);

                    setTimeout(function() {
                        showUpsellPopup($fakeButton);
                    }, 500);
                }
            }
        });

        // METOD 5: Cart count o'zgarganda (alternative)
        var previousCartCount = $('.cart-contents-count').text();

        setInterval(function() {
            var currentCartCount = $('.cart-contents-count').text();
            if (currentCartCount !== previousCartCount && lastClickedButton) {
                console.log('METHOD 5: Cart count changed');
                previousCartCount = currentCartCount;

                if (addToCartInProgress) {
                    console.log('Upsell ko\'rsatilmoqda (cart count trigger)...');
                    showUpsellPopup(lastClickedButton);
                    addToCartInProgress = false;
                }
            }
        }, 500);

        // Popup yopish
        $(document).on('click', '#smart-upsell-popup-wrapper .close-popup, #smart-upsell-popup-wrapper', function(e) {
            if (e.target === this || $(this).hasClass('close-popup')) {
                e.preventDefault();
                console.log('Popup yopilmoqda...');
                $('#smart-upsell-popup-wrapper').fadeOut(300, function() {
                    $(this).html('').hide(); // Konteynerni tozalash va yashirish
                });
            }
        });

        // Popup ichki content bosilganda yopilmasligi uchun
        $(document).on('click', '#smart-upsell-popup-wrapper .smart-upsell-popup-content', function(e) {
            e.stopPropagation();
        });

        // Upsell qo'shish
        $(document).on('click', '#smart-upsell-popup-wrapper .add-to-cart-upsell', function(e) {
            e.preventDefault();
            var $thisbutton = $(this);
            $thisbutton.text('Adding...').prop('disabled', true);

            var data = {
                'action': 'add_offer_to_cart',
                'nonce': smart_upsell_ajax.nonce,
                'product_id': $thisbutton.data('product-id'),
                'rule_id': $thisbutton.data('rule-id')
            };

            $.post( smart_upsell_ajax.ajax_url, data, function( response ) {
                if (response.success) {
                    $('#smart-upsell-popup-wrapper').fadeOut(300, function() { $(this).html('').hide(); });
                    $(document.body).trigger('wc_fragment_refresh');
                } else {
                    $thisbutton.text('Add to Cart & Save!').prop('disabled', false);
                    alert('Error: Unable to add product to cart');
                }
            }).fail(function() {
                $thisbutton.text('Add to Cart & Save!').prop('disabled', false);
                alert('Connection error. Please try again.');
            });
        });

        // Cross-sell qo'shish
        $(document).on('click', '.smart-cross-sell-product .add-to-order-cross-sell', function(e) {
            e.preventDefault();
            var $thisbutton = $(this);
            $thisbutton.text('Adding...').prop('disabled', true);

            var data = {
                'action': 'add_offer_to_cart',
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

        // ESC tugmasi bilan yopish
        $(document).on('keydown', function(e) {
            if (e.key === 'Escape' || e.keyCode === 27) {
                $('#smart-upsell-popup-wrapper').fadeOut(300, function() { $(this).html('').hide(); });
            }
        });

        console.log('Barcha event listenerlar o\'rnatildi (6 ta method)');
    });

})( jQuery );
