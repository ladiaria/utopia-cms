$(document).ready(function(){
    // Toggle class and show step label if "web" option is selected
    $('#chkbx-web-div').toggleClass(
      'ld-pago-select', $(".ld-chbx-force:checked").val() == 'web');
    $(".ld-subscription-step").toggle(
      $(".ld-chbx-force:checked").val() == 'web');

    // Toggle class and show schedule if "tel"
    $('#box-tel-div').toggleClass(
      'ld-pago-select', $(".ld-chbx-force:checked").val() == 'tel');
    $("#div_id_time").toggle($(".ld-chbx-force:checked").val() == 'tel');

    // Also add change events for the things above
    $(".ld-chbx-force").change(function(){
      $(".ld-subscription-step").toggle(this.value == 'web');
      $('#chkbx-web-div').toggleClass('ld-pago-select', this.value == 'web');
      $('#box-tel-div').toggleClass('ld-pago-select', $(".ld-chbx-force:checked").val() == 'tel');
      $("#div_id_time").toggle(this.value == 'tel');
    });
    

    /* Fix Chrome select drop down close on first click.
     * Needed for materialize css v0.100.2 (fixed in v1.0.0 and higher)
     * https://github.com/InfomediaLtd/angular2-materialize/issues/444#issuecomment-497063955
     */
    $(document).on("click",".select-wrapper",(e) => e.stopPropagation());
});
