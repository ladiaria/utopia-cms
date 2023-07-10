// override some parts from django default js
// TODO: describe the purpose of this custom script (seems needed to open popups on inlines' raw_id_fields)

function dismissRelatedLookupPopupCustom(win, chosenId) {
    var name = windowname_to_id(win.name);
    var elem = opener.document.getElementById(name);
    if (elem){
        if (elem.className.indexOf('vManyToManyRawIdAdminField') !== -1 && elem.value) {
            elem.value += ',' + chosenId;
        } else {
            elem.value = chosenId;
        }
    }
    win.close();
}

$(document).ready(function() {
    $("a[data-popup-opener]").click(function(event) {
        event.preventDefault();
        dismissRelatedLookupPopupCustom(window, $(this).data("popup-opener"));
    });
    $('body').on('click', '.related-lookup', function(e) {
            e.preventDefault();
            var event = $.Event('django:lookup-related');
            $(this).trigger(event);
            if (!event.isDefaultPrevented()) {
                last_clicked_inline = $(this);
                showRelatedObjectLookupPopup(this);
            }
        });
});
