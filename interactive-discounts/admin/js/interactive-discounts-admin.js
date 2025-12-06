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
                        // Regex to find and replace the index in the name attribute
                        name = name.replace(/\[\d*\]/, '[' + index + ']');
                        $(this).attr('name', name);
                    }
                });
            });
        }

        // Add Segment
        $('#add_segment_button').on('click', function() {
            let segmentRepeater = $('#segment_repeater');
            let newSegment = segmentRepeater.find('.segment-template').clone();

            newSegment.removeClass('segment-template').show();
            segmentRepeater.append(newSegment);

            // Re-initialize color picker for the new segment and update indexes
            initializeColorPicker(newSegment);
            updateSegmentIndexes();
        });

        // Remove Segment - using event delegation for dynamically added elements
        $('#segment_repeater').on('click', '.remove_segment_button', function(e) {
            e.preventDefault();
            $(this).closest('.segment-row').remove();
            updateSegmentIndexes();
        });

        // Initial setup on page load
        initializeColorPicker(document);
        updateSegmentIndexes();

    });

})( jQuery );
