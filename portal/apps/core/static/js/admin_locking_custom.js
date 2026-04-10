/**
 * Custom enhancement for django-admin-locking
 * - Moves the lock banner to the top (fixed position)
 * - Prevents automatic scroll when fields are disabled
 * - Ready for Spanish translation
 */
window.addEventListener("load", function() {
  (function($) {

    /**
     * Translate lock messages from English to Spanish
     * @param {string} originalMessage - The original English message from the library
     * @param {boolean} isLocked - True if page is locked, false if unlocked
     * @returns {string} The translated Spanish message
     */
    function translateMessage(originalMessage, isLocked) {
      if (isLocked) {
        // Extract username from English message format: "...by FirstName LastName &lt;<a href=..."
        let userName = originalMessage.match(/by (.+?)\s+&lt;/);
        userName = userName ? userName[1].trim() : 'otro usuario';
        return "⚠️ Esta página está siendo editada por <strong>" + userName + "</strong>. Por favor espera hasta que termine o el bloqueo expire.";
      } else {
        return "✓ Ahora puedes editar esta página. <a href='" + window.location.pathname + "'>Recargar página aqui</a>";
      }
    }

    // Move submit-row to top with fixed positioning
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

    // Prevent automatic scroll to bottom when fields are disabled
    function preventAutoScroll(callback) {
      const scrollPos = window.scrollY;
      callback();
      // Restore scroll position after browser potentially auto-scrolls
      setTimeout(function() {
        window.scrollTo(0, scrollPos);
      }, 10);
    }

    // Watch for class changes on submit-row
    const observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(mutation) {
        if (mutation.attributeName === 'class') {
          const submitRow = $('div.submit-row');

          if (submitRow.hasClass('locked')) {
            // Page is locked, translate message and position banner at top
            preventAutoScroll(function() {
              const originalMessage = submitRow.html();
              const translatedMessage = translateMessage(originalMessage, true);
              submitRow.html('<p style="padding:10px;margin:0;">' + translatedMessage + '</p>');
              positionBannerAtTop();
            });
          } else if (submitRow.hasClass('unlocked')) {
            // Page unlocked, translate message and position banner at top
            preventAutoScroll(function() {
              const originalMessage = submitRow.html();
              const translatedMessage = translateMessage(originalMessage, false);
              submitRow.html('<p style="padding:10px;margin:0;">' + translatedMessage + '</p>');
              positionBannerAtTop();
            });
          } else {
            // No lock, restore normal positioning
            submitRow.css({
              position: '',
              top: '',
              left: '',
              right: '',
              zIndex: '',
              margin: '',
              padding: '',
              fontSize: '',
              fontWeight: '',
              textAlign: '',
              boxShadow: ''
            });
          }
        }
      });
    });

    // Start observing the submit-row for class changes
    const submitRow = document.querySelector('div.submit-row');
    if (submitRow) {
      observer.observe(submitRow, { attributes: true });
    }

  })(django.jQuery);
});