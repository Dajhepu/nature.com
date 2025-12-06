(function( $ ) {
    'use strict';
    $(function() {
        function initializeColorPicker( context ) {
            $('.color-picker', context).wpColorPicker();
        }
        function updateSegmentIndexes() {
            $('#segment_repeater .segment-row').not('.segment-template').each(function(index) {
                $(this).find('input, select').each(function() {
                    let name = $(this).attr('name');
                    if (name) {
                        name = name.replace(/\[\d*\]/, '[' + index + ']');
                        $(this).attr('name', name);
                    }
                });
            });
        }
        $('#add_segment_button').on('click', function() {
            let segmentRepeater = $('#segment_repeater');
            let newSegment = $('.segment-template').clone();
            newSegment.removeClass('segment-template').show();
            segmentRepeater.append(newSegment);
            initializeColorPicker(newSegment);
            updateSegmentIndexes();
        });
        $('#segment_repeater').on('click', '.remove_segment_button', function(e) {
            e.preventDefault();
            $(this).closest('.segment-row').remove();
            updateSegmentIndexes();
        });
        initializeColorPicker(document);
        updateSegmentIndexes();
    });
})( jQuery );
