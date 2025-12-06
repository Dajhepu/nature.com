(function( $ ) {
    'use strict';

    $(function() {

        const popupWrapper = $('#id-wheel-popup-wrapper');
        const l10n = id_wheel_ajax.l10n;

        // Don't show if the user has already won a coupon in this session
        if (sessionStorage.getItem('id_wheel_coupon_won')) {
            return;
        }

        // Basic popup HTML structure
        const popupHTML = `
            <div class="id-wheel-popup-content">
                <span class="id-wheel-close-popup">&times;</span>
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

        // Inject the HTML into the wrapper
        popupWrapper.html(popupHTML);

        // Show popup after a delay (e.g., 2 seconds)
        setTimeout(() => {
            popupWrapper.css('display', 'flex').hide().fadeIn();
        }, 2000);

        // Close popup functionality
        popupWrapper.on('click', '.id-wheel-close-popup', closePopup);
        popupWrapper.on('click', function(e) {
            if (e.target === this) {
                closePopup();
            }
        });

        function closePopup() {
            popupWrapper.fadeOut();
        }

        // Prepare segments for Winwheel, now using colors from settings
        let segments = id_wheel_ajax.segments.map(segment => ({
            'fillStyle': segment.fillStyle,
            'text': segment.text
        }));

        // Create new wheel object specifying the parameters at creation time.
        let theWheel = new Winwheel({
            'numSegments'  : segments.length,
            'outerRadius'  : 180,
            'textFontSize' : 16,
            'segments'     : segments,
            'animation'    : {
                'type'     : 'spinToStop',
                'duration' : 5,
                'spins'    : 8,
                'callbackFinished' : alertPrize
            }
        });

        // Click handler for spin button.
        $('#spin_button').on('click', function() {
            theWheel.startAnimation();
            $(this).prop('disabled', true);
        });

        // Function to handle the prize alert.
        function alertPrize(indicatedSegment) {
            let winningSegmentIndex = theWheel.getIndicatedSegmentNumber() - 1;

            let data = {
                'action': 'generate_coupon',
                'nonce': id_wheel_ajax.nonce,
                'segment_index': winningSegmentIndex
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

    });

})( jQuery );
