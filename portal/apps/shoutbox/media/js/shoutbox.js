/* La Diaria 2.0 shoutbox */
$(document).ready(function(){
    // get_shouts();
    setInterval(get_shouts, 600000);
    $('#ishout').submit(function(){
        shout_this($('#message').val());
        $('#message').val('');
        return false;
    });
});
function shout_this(message) {
    $.ajax({
        type: 'POST',
        url: '/shout/',
        data: {message: message},
        success: function(msg){
            get_shouts();
        }
    });
}
function get_shouts() {
    $.ajax({
        type: 'POST',
        url: '/shout/list/',
        success: function(msg){
            $('#shoutbox').html(msg);
        }
    });
}
