(function( $ ) {
    'use strict';

    $(function() {
        // This initializes the WooCommerce product search select boxes.
        // It's sometimes necessary to manually trigger this if other scripts interfere.
        $( document.body ).trigger( 'wc-enhanced-select-init' );
    });

})( jQuery );
