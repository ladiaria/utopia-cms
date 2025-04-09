document.addEventListener('DOMContentLoaded', function () {
  django.jQuery(function($) {
    // update position labels for inlines
    window.update_pos_labels = function(child, selector='.has_original', update_field='position') {
      $.each($('tr' + selector, $(child).closest('tbody')), function(i, row) {
        const position = i + 1;
        $("td.field-" + update_field + " p", $(row)).text(position);
        // also update the sortable hidden value (no problem if sortableadmin2 also tries to update it)
        $("input._reorder_", $(row)).val(position);
      });
    }
    // handler for "click" event on sortable2 up-down buttons
    $("span.sort i").on('click', function(event) {
      update_pos_labels(event.target);
    });
  });
});
