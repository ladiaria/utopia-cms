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
        return "⚠️ Esta página está siendo editada por <strong>" + userName + "</strong>. Por favor espera hasta que termine o el bloqueo expire.";
      } else {
        return "✓ Ahora puedes editar esta página. <a href='" + window.location.pathname + "'>Recargar página aquí</a>";
      }
    }

    function positionBannerAtTop() {
      $('div.submit-row').css({
        position: 'fixed',
        top: '0',
        left: '0',
        right: '0',
        zIndex: '10000',
        margin: '0',
        padding: '15px 20px',
        fontSize: '14px',
        fontWeight: 'bold',
        textAlign: 'center',
        boxShadow: '0 2px 8px rgba(0,0,0,0.2)'
      });
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
              submitRow.html('<p style="padding:10px;margin:0;">' + translatedMessage + '</p>');
              positionBannerAtTop();
            });
          } else if (submitRow.hasClass('unlocked')) {
            preventAutoScroll(function() {
              const translatedMessage = translateMessage(submitRow.html(), false);
              submitRow.html('<p style="padding:10px;margin:0;">' + translatedMessage + '</p>');
              positionBannerAtTop();
            });
          } else {
            // Lock released — restore normal submit-row positioning.
            submitRow.css({
              position: '', top: '', left: '', right: '', zIndex: '',
              margin: '', padding: '', fontSize: '', fontWeight: '',
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
