(function($) {
  $(function() {
        setTimeout(function() {
            $('#subscribe-footer').fadeOut();
        }, 15000); // <-- time in milliseconds
        if (Cookies.get('suscribite-ladiaria') != '1') {
          $('#subscribe-footer').show();
        }
        $('#subscribe-footer .close').click(function(){
          var in4hours = new Date(new Date().getTime() + 480 * 60 * 1000);
          Cookies.set('suscribite-ladiaria', '1', { expires: in4hours});
          $('#subscribe-footer').fadeOut();
        });
  }); // end of document ready
})(jQuery); // end of jQuery name space
