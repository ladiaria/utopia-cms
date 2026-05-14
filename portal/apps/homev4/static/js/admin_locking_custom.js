/**
 * Custom enhancement for django-admin-locking
 * - Translates lock messages from English to Spanish
 * - Moves the lock banner to a fixed position at the top of the page
 * - Prevents automatic scroll to bottom when fields are disabled
 */
window.addEventListener("load", function() {
  (function($) {

    function translateMessage(originalMessage, isLocked) {
      if (isLocked) {
        // Extract username from the library's English format: "...by FirstName LastName &lt;<a href=..."
        let userName = originalMessage.match(/by (.+?)\s+&lt;/);
        userName = userName ? userName[1].trim() : 'otro usuario';
        return "<strong>" + userName + "</strong> está editando esta página. Podrás editarla cuando finalice o cuando expire el bloqueo.";
      } else {
        return "✓ Ya podés editar esta página. <a href='" + window.location.pathname + "' style='font-weight:bold;text-decoration:underline;'>Recargar para editar</a>";
      }
    }

    var BASE_BANNER_CSS = {
      position: 'fixed',
      top: '0',
      left: '0',
      right: '0',
      zIndex: '10000',
      margin: '0',
      padding: '0',
      textAlign: 'center',
      boxShadow: '0 2px 8px rgba(0,0,0,0.2)'
    };

    function applyBannerStyle(submitRow, isLocked) {
      var extra = isLocked
        ? { background: '#c62828', color: '#fff' }
        : { background: '#c8e6c9', color: '#1b5e20' };
      submitRow.css(Object.assign({}, BASE_BANNER_CSS, extra));
    }

    // Restore scroll position after the library disables fields (which triggers browser auto-scroll).
    function preventAutoScroll(callback) {
      const scrollPos = window.scrollY;
      callback();
      setTimeout(function() { window.scrollTo(0, scrollPos); }, 10);
    }

    const observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(mutation) {
        if (mutation.attributeName === 'class') {
          const submitRow = $('div.submit-row');

          if (submitRow.hasClass('locked')) {
            preventAutoScroll(function() {
              const translatedMessage = translateMessage(submitRow.html(), true);
              submitRow.html('<p style="padding:16px 24px;margin:0;font-size:16px;">' + translatedMessage + '</p>');
              applyBannerStyle(submitRow, true);
            });
          } else if (submitRow.hasClass('unlocked')) {
            preventAutoScroll(function() {
              const translatedMessage = translateMessage(submitRow.html(), false);
              submitRow.html('<p style="padding:14px 24px;margin:0;font-size:15px;">' + translatedMessage + '</p>');
              applyBannerStyle(submitRow, false);
            });
          } else {
            // Lock released — restore normal submit-row positioning.
            submitRow.css({
              position: '', top: '', left: '', right: '', zIndex: '',
              margin: '', padding: '', background: '', color: '',
              textAlign: '', boxShadow: ''
            });
          }
        }
      });
    });

    const submitRow = document.querySelector('div.submit-row');
    if (submitRow) {
      observer.observe(submitRow, { attributes: true });
    }

  })(django.jQuery);
});
