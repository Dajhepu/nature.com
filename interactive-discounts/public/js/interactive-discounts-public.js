(function( $ ) {
    'use strict';

    $(function() {

        const popupWrapper = $('#id-wheel-popup-wrapper');
        const settings = id_wheel_ajax.settings;
        const l10n = id_wheel_ajax.l10n;
        let theWheel;
        let emailFormSubmitted = false;

        // Don't show if the user has already won a coupon in this session
        if (sessionStorage.getItem('id_wheel_coupon_won')) {
            return;
        }

        function buildPopupHTML() {
            let emailFormHTML = '';
            if (settings.enable_email_collection) {
                emailFormHTML = `
                    <div id="id-email-form">
                        <h2>${settings.email_title}</h2>
                        <p>${settings.email_subtitle}</p>
                        <input type="email" id="id-wheel-email" placeholder="Enter your email..." required />
                        <button id="id-submit-email">${settings.email_button_text}</button>
                        <p class="email-error" style="color:red; display:none;">Please enter a valid email.</p>
                    </div>
                `;
            }

            const wheelHTML = `
                <div id="id-wheel-container" style="${settings.enable_email_collection ? 'display:none;' : ''}">
                    <h2>${l10n.want_a_discount}</h2>
                    <p>${l10n.spin_to_win}</p>
                    <div class="wheel-container">
                        <canvas id="id-wheel-canvas" width="400" height="400">
                            <p>${l10n.canvas_unsupported}</p>
                        </canvas>
                    </div>
                    <button id="spin_button">${l10n.spin_button_text}</button>
                    <div id="wheel-result"></div>
                </div>
            `;

            return `
                <div class="id-wheel-popup-content">
                    <span class="id-wheel-close-popup">&times;</span>
                    ${emailFormHTML}
                    ${wheelHTML}
                </div>
            `;
        }

        popupWrapper.html(buildPopupHTML());

        setTimeout(() => {
            popupWrapper.css('display', 'flex').hide().fadeIn();
        }, 2000);

        popupWrapper.on('click', '.id-wheel-close-popup', () => popupWrapper.fadeOut());
        popupWrapper.on('click', function(e) { if (e.target === this) popupWrapper.fadeOut(); });

        if (settings.enable_email_collection) {
            $('#id-submit-email').on('click', handleEmailSubmit);
        } else {
            initializeWheel();
        }

        function handleEmailSubmit() {
            const emailInput = $('#id-wheel-email');
            const email = emailInput.val();
            if (!validateEmail(email)) {
                $('.email-error').slideDown();
                return;
            }
            $('.email-error').slideUp();

            let data = {
                'action': 'save_email',
                'nonce': id_wheel_ajax.nonce,
                'email': email
            };

            $.post(id_wheel_ajax.ajax_url, data, function(response) {
                // We don't need to do anything on success, just proceed.
                emailFormSubmitted = true;
                $('#id-email-form').fadeOut(() => {
                    $('#id-wheel-container').fadeIn();
                    initializeWheel();
                });
            }).fail(function() {
                // If AJAX fails, still show the wheel
                emailFormSubmitted = true;
                $('#id-email-form').fadeOut(() => {
                    $('#id-wheel-container').fadeIn();
                    initializeWheel();
                });
            });
        }

        function initializeWheel() {
            let segments = id_wheel_ajax.segments;
            theWheel = new Winwheel({
                'numSegments'  : segments.length, 'outerRadius'  : 180, 'textFontSize' : 16,
                'segments'     : segments,
                'animation'    : {
                    'type'     : 'spinToStop', 'duration' : 5, 'spins'    : 8, 'callbackFinished' : handlePrize
                }
            });
             $('#spin_button').on('click', () => {
                theWheel.startAnimation();
                $('#spin_button').prop('disabled', true);
            });
        }

        function handlePrize(indicatedSegment) {
            let winningSegmentIndex = theWheel.getIndicatedSegmentNumber() - 1;
            let data = {
                'action': 'generate_coupon', 'nonce': id_wheel_ajax.nonce, 'segment_index': winningSegmentIndex
            };

            $.post(id_wheel_ajax.ajax_url, data, function(response) {
                let resultDiv = $('#wheel-result');
                if (response.success) {
                    let message = response.data.message;
                    if (response.data.coupon_code) {
                        message += ' <strong id="id-coupon-code">' + response.data.coupon_code + '</strong>';
                        sessionStorage.setItem('id_wheel_coupon_won', true);
                    }
                    resultDiv.html(message);
                } else {
                    resultDiv.html(l10n.error_message);
                }
                $('#spin_button').prop('disabled', false);
            });
        }

        function validateEmail(email) {
            const re = /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
            return re.test(String(email).toLowerCase());
        }
    });
})( jQuery );
