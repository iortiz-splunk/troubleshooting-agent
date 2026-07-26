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

  function init() {
    initCodeTabs();
    initCopyButtons();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
