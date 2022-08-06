$(function() {
    // Toggle class and show schedule
    $('#box-tel-div').toggleClass(
      'ld-pago-select', $(".ld-chbx-force:checked").val() == 'tel');
    $("#div_id_time").toggle($(".ld-chbx-force:checked").val() == 'tel');
});
