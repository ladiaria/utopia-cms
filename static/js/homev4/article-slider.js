/**
 * Article slider for homev4.
 *
 * Finds every [data-slider] container and, if it has more than PAGE_SIZE
 * articles, wraps them in a sliding track and injects prev/next buttons.
 * Clicking a button animates the track horizontally to reveal the next group.
 *
 * On mobile (≤ MOBILE_BREAKPOINT) the slider is not initialized and all
 * articles are shown vertically via CSS.
 */
(function () {
  'use strict';

  var PAGE_SIZE = 3;
  var MOBILE_BREAKPOINT = 767;

  function initSlider(container) {
    var articles = Array.prototype.slice.call(container.querySelectorAll(':scope > article'));
    if (articles.length <= PAGE_SIZE) return;

    var currentPage = 0;
    var totalPages = Math.ceil(articles.length / PAGE_SIZE);
    var track = null;
    var nav = null;
    var prevBtn = null;
    var nextBtn = null;
    var active = false;

    function setWidths() {
      var gap = parseFloat(window.getComputedStyle(track).columnGap) || 0;
      var articleWidth = (container.offsetWidth - gap * (PAGE_SIZE - 1)) / PAGE_SIZE;
      articles.forEach(function (article) {
        article.style.width = articleWidth + 'px';
        article.style.flexShrink = '0';
        article.style.height = '';
      });
    }

    function setHeight() {
      articles.forEach(function (article) { article.style.height = ''; });
      var maxHeight = articles.reduce(function (max, article) {
        return Math.max(max, article.offsetHeight);
      }, 0);
      articles.forEach(function (article) {
        article.style.height = maxHeight + 'px';
      });
    }

    function goToPage(page, animate) {
      if (!animate) {
        track.style.transition = 'none';
        track.offsetHeight; // eslint-disable-line no-unused-expressions
      }
      var gap = parseFloat(window.getComputedStyle(track).columnGap) || 0;
      track.style.transform = 'translateX(-' + (page * (container.offsetWidth + gap)) + 'px)';
      if (!animate) {
        requestAnimationFrame(function () {
          requestAnimationFrame(function () {
            track.style.transition = '';
          });
        });
      }
      prevBtn.style.visibility = page === 0 ? 'hidden' : '';
      nextBtn.style.visibility = page === totalPages - 1 ? 'hidden' : '';
      setHeight();
      currentPage = page;
    }

    function setup() {
      track = document.createElement('div');
      track.className = 'article-slider__track';
      articles.forEach(function (article) {
        track.appendChild(article);
      });
      container.insertBefore(track, container.firstChild);

      nav = document.createElement('div');
      nav.className = 'article-slider__nav';

      prevBtn = document.createElement('button');
      prevBtn.className = 'article-slider__btn article-slider__btn--prev';
      prevBtn.setAttribute('aria-label', 'Artículos anteriores');
      prevBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="5" height="9" fill="none" viewBox="0 0 5 9"><path stroke="#000" stroke-linecap="round" stroke-linejoin="round" d="m4.5.5-4 4 4 4"/></svg>';
      prevBtn.addEventListener('click', function () { goToPage(currentPage - 1, true); });

      nextBtn = document.createElement('button');
      nextBtn.className = 'article-slider__btn article-slider__btn--next';
      nextBtn.setAttribute('aria-label', 'Artículos siguientes');
      nextBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="5" height="9" fill="none" viewBox="0 0 5 9"><path stroke="#000" stroke-linecap="round" stroke-linejoin="round" d="m.5 8.5 4-4-4-4"/></svg>';
      nextBtn.addEventListener('click', function () { goToPage(currentPage + 1, true); });

      nav.appendChild(prevBtn);
      nav.appendChild(nextBtn);
      container.appendChild(nav);

      active = true;
      setWidths();
      goToPage(0, false);

      if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(setHeight);
      }
      articles.forEach(function (article) {
        Array.prototype.forEach.call(article.querySelectorAll('img'), function (img) {
          if (!img.complete) img.addEventListener('load', setHeight);
        });
      });
    }

    function destroy() {
      articles.forEach(function (article) {
        article.style.width = '';
        article.style.height = '';
        article.style.flexShrink = '';
        container.insertBefore(article, track);
      });
      container.removeChild(track);
      container.removeChild(nav);
      track = null;
      nav = null;
      prevBtn = null;
      nextBtn = null;
      currentPage = 0;
      active = false;
    }

    window.addEventListener('resize', function () {
      if (window.innerWidth <= MOBILE_BREAKPOINT) {
        if (active) destroy();
      } else {
        if (!active) {
          setup();
        } else {
          setWidths();
          goToPage(currentPage, false);
        }
      }
    });

    if (window.innerWidth > MOBILE_BREAKPOINT) {
      setup();
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    var sliders = document.querySelectorAll('[data-slider]');
    Array.prototype.forEach.call(sliders, initSlider);
  });
})();
