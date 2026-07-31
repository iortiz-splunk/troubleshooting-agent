(function () {
  function initCodeTabs() {
    document.querySelectorAll('.code-tabs').forEach(function (root) {
      var nav = root.querySelector('.code-tabs__nav');
      var sources = root.querySelector('.code-tabs__sources');
      var panelsWrap = root.querySelector('.code-tabs__panels');
      if (!nav || !sources || !panelsWrap) return;

      var entries = Array.prototype.slice.call(sources.querySelectorAll('.code-tabs__source'));
      var defaultIndex = entries.findIndex(function (entry) {
        return entry.dataset.default === 'true';
      });
      if (defaultIndex < 0) defaultIndex = 0;

      entries.forEach(function (entry, index) {
        var title = entry.dataset.title || 'Tab ' + (index + 1);
        var isActive = index === defaultIndex;

        var tab = document.createElement('button');
        tab.type = 'button';
        tab.className = 'code-tabs__tab' + (isActive ? ' is-active' : '');
        tab.textContent = title;
        tab.setAttribute('role', 'tab');
        tab.setAttribute('aria-selected', String(isActive));

        var panel = document.createElement('div');
        panel.className = 'code-tabs__panel' + (isActive ? ' is-active' : '');
        panel.setAttribute('role', 'tabpanel');
        panel.hidden = !isActive;
        panel.innerHTML = entry.innerHTML;

        tab.addEventListener('click', function () {
          root.querySelectorAll('.code-tabs__tab').forEach(function (btn) {
            btn.classList.remove('is-active');
            btn.setAttribute('aria-selected', 'false');
          });
          root.querySelectorAll('.code-tabs__panel').forEach(function (p) {
            p.classList.remove('is-active');
            p.hidden = true;
          });
          tab.classList.add('is-active');
          tab.setAttribute('aria-selected', 'true');
          panel.classList.add('is-active');
          panel.hidden = false;
        });

        nav.appendChild(tab);
        panelsWrap.appendChild(panel);
      });

      sources.remove();
    });
  }

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    var textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'absolute';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    return Promise.resolve();
  }

  function initCopyButtons() {
    document.querySelectorAll('.code-block__copy').forEach(function (button) {
      if (button.dataset.bound === 'true') return;
      button.dataset.bound = 'true';

      button.addEventListener('click', function () {
        var block = button.closest('.code-block');
        if (!block) return;
        var code = block.querySelector('code');
        var text = code ? code.innerText : block.querySelector('pre').innerText;
        copyText(text).then(function () {
          var original = button.innerHTML;
          button.classList.add('is-copied');
          button.innerHTML = 'Copied';
          window.setTimeout(function () {
            button.classList.remove('is-copied');
            button.innerHTML = original;
          }, 1600);
        });
      });
    });
  }

  function initImageLightbox() {
    var triggers = document.querySelectorAll('[data-lightbox-trigger]');
    if (!triggers.length) return;

    var lightbox = document.getElementById('image-lightbox');
    if (!lightbox) {
      lightbox = document.createElement('div');
      lightbox.id = 'image-lightbox';
      lightbox.className = 'lightbox';
      lightbox.hidden = true;
      lightbox.setAttribute('role', 'dialog');
      lightbox.setAttribute('aria-modal', 'true');
      lightbox.setAttribute('aria-label', 'Expanded image');
      lightbox.innerHTML =
        '<button type="button" class="lightbox__backdrop" aria-label="Close expanded image"></button>' +
        '<button type="button" class="lightbox__close" aria-label="Close">&times;</button>' +
        '<figure class="lightbox__panel">' +
        '<img class="lightbox__img" alt="" />' +
        '<figcaption class="lightbox__caption"></figcaption>' +
        '</figure>';
      document.body.appendChild(lightbox);
    }

    var backdrop = lightbox.querySelector('.lightbox__backdrop');
    var closeBtn = lightbox.querySelector('.lightbox__close');
    var panelImg = lightbox.querySelector('.lightbox__img');
    var panelCaption = lightbox.querySelector('.lightbox__caption');
    var lastFocus = null;

    function closeLightbox() {
      lightbox.hidden = true;
      document.body.classList.remove('lightbox-open');
      if (lastFocus && typeof lastFocus.focus === 'function') {
        lastFocus.focus();
      }
    }

    function openLightbox(trigger) {
      var figure = trigger.closest('figure');
      var img = trigger.querySelector('img');
      if (!img) return;

      lastFocus = trigger;
      panelImg.src = img.currentSrc || img.src;
      panelImg.alt = img.alt || '';

      var caption = figure ? figure.querySelector('figcaption') : null;
      if (caption && caption.textContent.trim()) {
        panelCaption.innerHTML = caption.innerHTML;
        panelCaption.hidden = false;
      } else {
        panelCaption.textContent = '';
        panelCaption.hidden = true;
      }

      lightbox.hidden = false;
      document.body.classList.add('lightbox-open');
      closeBtn.focus();
    }

    triggers.forEach(function (trigger) {
      if (trigger.dataset.lightboxBound === 'true') return;
      trigger.dataset.lightboxBound = 'true';
      trigger.addEventListener('click', function () {
        openLightbox(trigger);
      });
    });

    backdrop.addEventListener('click', closeLightbox);
    closeBtn.addEventListener('click', closeLightbox);

    document.addEventListener('keydown', function (event) {
      if (lightbox.hidden) return;
      if (event.key === 'Escape') {
        event.preventDefault();
        closeLightbox();
      }
    });
  }

  function init() {
    initCodeTabs();
    initCopyButtons();
    initImageLightbox();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
