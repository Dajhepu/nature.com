(function( $ ) {
    'use strict';

    $(function() {

        // Add Segment
        $('#add_segment_button').on('click', function() {
            let segmentRepeater = $('#segment_repeater');
            let newSegment = segmentRepeater.find('.segment-template').clone();

            newSegment.removeClass('segment-template').show();
            updateSegmentIndexes(); // Update indexes before appending
            segmentRepeater.append(newSegment);
        });

        // Remove Segment
        $('#segment_repeater').on('click', '.remove_segment_button', function() {
            $(this).closest('.segment-row').remove();
            updateSegmentIndexes();
        });

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

        // Initial call to set names correctly on page load
        updateSegmentIndexes();

    });

})( jQuery );
