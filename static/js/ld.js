(function ($) {

  function dismissPaywallSnackbar() {
    $('.js-ld-snackbar').removeClass('ld-snackbar--active');
    setTimeout(function () { $('.js-ld-snackbar').remove(); }, 1000); // Fallback
  }

  // Mobile share overlay
  function bindMobileShare() {
    $('.js-nav-menu__share').on('click', function (event) {
      $('#article-share-full').toggleClass('active');
      event.preventDefault();
    });
    $('#article-share-full .modal-close').on('click', function () {
      $('#article-share-full').removeClass('active');
    });
  }

  // DOM Ready
  $(function () {
    // Detect touch screen and enable scrollbar if necessary
    function is_touch_device() {
      try {
        document.createEvent('TouchEvent');
        return true;
      } catch (e) {
        return false;
      }
    }

    $('.modal').modal({
      dismissible: true, // Modal can be dismissed by clicking outside of the modal
      opacity: .5, // Opacity of modal background
      inDuration: 300, // Transition in duration
      outDuration: 200, // Transition out duration
      startingTop: '4%', // Starting top style attribute
      endingTop: '10%' // Ending top style attribute
    });

    $('.js-ld-main-menu-toggle').on('click', function () {
      if ($('body').hasClass('main-menu-open')) {
        $('.js-ld-main-menu').removeClass('active');
        $('body').removeClass('main-menu-open');
        return false;
      } else {
        $('.js-ld-main-menu').addClass('active');
        $('body').addClass('main-menu-open');
        return false;
      }
    });

    // Esc key to close main menu
    $(document).keyup(function (e) {
      if (e.keyCode === 27) {
        $('.js-ld-main-menu').removeClass('active');
        $('body').removeClass('main-menu-open');
      }
    });

    $('.alert-close').on("click", function () {
      $(".alert-box").fadeOut("slow", function () { });
    });

    var isMobile = false; //initiate as false
    // device detection
    if (/(android|bb\d+|meego).+mobile|avantgo|bada\/|blackberry|blazer|compal|elaine|fennec|hiptop|iemobile|ip(hone|od)|ipad|iris|kindle|Android|Silk|lge |maemo|midp|mmp|netfront|opera m(ob|in)i|palm( os)?|phone|p(ixi|re)\/|plucker|pocket|psp|series(4|6)0|symbian|treo|up\.(browser|link)|vodafone|wap|windows (ce|phone)|xda|xiino/i.test(navigator.userAgent) ||
      /1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\-(n|u)|c55\/|capi|ccwa|cdm\-|cell|chtm|cldc|cmd\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\-s|devi|dica|dmob|do(c|p)o|ds(12|\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\-|_)|g1 u|g560|gene|gf\-5|g\-mo|go(\.w|od)|gr(ad|un)|haie|hcit|hd\-(m|p|t)|hei\-|hi(pt|ta)|hp( i|ip)|hs\-c|ht(c(\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\-(20|go|ma)|i230|iac( |\-|\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\/)|klon|kpt |kwc\-|kyo(c|k)|le(no|xi)|lg( g|\/(k|l|u)|50|54|\-[a-w])|libw|lynx|m1\-w|m3ga|m50\/|ma(te|ui|xo)|mc(01|21|ca)|m\-cr|me(rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\-2|po(ck|rt|se)|prox|psio|pt\-g|qa\-a|qc(07|12|21|32|60|\-[2-7]|i\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\-|oo|p\-)|sdk\/|se(c(\-|0|1)|47|mc|nd|ri)|sgh\-|shar|sie(\-|m)|sk\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\-|v\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\-|tdg\-|tel(i|m)|tim\-|t\-mo|to(pl|sh)|ts(70|m\-|m3|m5)|tx\-9|up(\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|yas\-|your|zeto|zte\-/i.test(navigator.userAgent.substr(0, 4))) isMobile = true;

    if ($('select').material_select) $('select').material_select();

    $('.js-close-ld-snackbar').on('click', function () {
      dismissPaywallSnackbar();
    });

    // Trigger modals
    $('.js-modal-trigger').on('click', function () {
      var modalID = $(this).data('trigger');
      $(modalID).addClass('active');
    });

    $('.js-modal-close').on('click', function () {
      $('ld-modal').removeClass('active');
    });

    $(document).keyup(function (e) {
      if (e.keyCode === 27) {
        $('ld-modal').removeClass('active');
      }
    });

    // Dismiss alerts.
    $('body').on('click', '.js-dismiss-message', function () {
      $(this).parent().remove();
    });

    bindMobileShare();

    function loadComments() {
      $.getScript($('#coral_talk_stream').attr('data-talk-url') + 'assets/js/embed.js', function () {
        var coral_options = {
          id: 'coral_talk_stream',
          autoRender: true,
          rootURL: $('#coral_talk_stream').attr('data-talk-url'),
          storyID: $('#coral_talk_stream').attr('data-article-id'),
          storyURL: $('#coral_talk_stream').attr('data-article-url'),
          accessToken: $('#coral_talk_stream').attr('data-talk-auth-token'),
          events: function (events) {
            events.on("loginPrompt", function () {
              location.href = $('#coral_talk_stream').attr('data-login-url');
            });
          }
        };
        if (coral_options.accessToken) {
          coral_options.bodyClassName = 'logged-in';
        }
        Coral.createStreamEmbed(coral_options);
        $('.talk-login').addClass('active');
      });
    }
    $('#coral_talk_stream button.authorized').on('click', function () {
      loadComments();
    });
    // Load comments if coming from AMP version
    if (window.location.hash === '#comentarios') {
      loadComments();
    }

    $('.ld-audio__audio').on('play', function (event) {
      var audio = $(this)[0];
      if ($('.ld-audio__overlay').length > 0) {
        audio.pause();
        event.preventDefault();
        $('.ld-audio__overlay').addClass('active');
        console.log('Audio forbidden.');
      }
    });

    $('.ld-audio__overlay-close-btn').on('click', function () {
      $('.ld-audio__overlay').removeClass('active');
    });

    // toggle password visibility
    $(".toggle-password").on("click", function () {
      $(this).toggleClass("visibility-on");
      var id = $(this).data("toggle");
      var input = $(id);
      if (input.attr("type") == "password") {
        input.attr("type", "text");
      } else {
        input.attr("type", "password");
      }
    });

    // show more article tags
    $('.article-tags > .expand').on("click", function () {
      $('.article-tags .more-tags').removeClass('hidden');
      $(this).hide();
      return false;
    });

    // faq component behavior
    $('.ld-collapsible').addClass('js');
    $('.ld-collapsible > li > .collapsible-header').on("click", function () {
      $(this).parent('li').toggleClass('active');
      $(this).next('.collapsible-body').slideToggle();
    });
  }) // end of document ready

})(jQuery) // end of jQuery name space
