/* "Everything connected": one task through the app. Tabs + auto-advance while in view.
   No auto-advance with reduced motion; stops for good once the visitor picks a step. */
(function () {
  var box = document.querySelector('.jbox'); if (!box) return;
  var tabs = [].slice.call(box.querySelectorAll('.jstep'));
  var panels = tabs.map(function (t) { return document.getElementById(t.getAttribute('aria-controls')); });
  var cur = 0, timer = null, user = false, visible = false;
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var DWELL = 5200, ZOOM_AT = 900, MAXZ = 1.7, zt = null;
  // Guided zoom: show the whole screen first, then ease in on the ringed detail.
  function zoomTo(k) {
    clearTimeout(zt);
    panels.forEach(function (p) { var z = p.querySelector('.jz'); if (z) { z.classList.add('still'); z.style.transform = ''; void z.offsetWidth; z.classList.remove('still'); } });
    if (reduce) return;
    var z = panels[k].querySelector('.jz'), r = panels[k].querySelector('.ring'); if (!z || !r) return;
    var f = function (v) { return parseFloat(v) / 100; };
    var l = f(r.style.left), t = f(r.style.top), w = f(r.style.width), h = f(r.style.height);
    var sc = Math.min(MAXZ, 0.9 / w, 0.9 / h); if (!(sc >= 1.15)) return;
    var cl = function (v) { return Math.max(1 - sc, Math.min(0, v)); };
    var tx = cl(0.5 - (l + w / 2) * sc), ty = cl(0.5 - (t + h / 2) * sc);
    zt = setTimeout(function () { z.style.transform = 'translate(' + (tx * 100).toFixed(2) + '%,' + (ty * 100).toFixed(2) + '%) scale(' + sc.toFixed(3) + ')'; }, ZOOM_AT);
  }
  function show(i, focus, keepZoom) {
    cur = (i + tabs.length) % tabs.length;
    tabs.forEach(function (t, k) {
      var on = k === cur;
      t.setAttribute('aria-selected', on ? 'true' : 'false');
      t.tabIndex = on ? 0 : -1;
      t.classList.remove('run');
      panels[k].hidden = !on;
    });
    if (focus) tabs[cur].focus();
    var img = panels[cur].querySelector('img'); if (img) img.loading = 'eager';
    var nxt = panels[(cur + 1) % panels.length].querySelector('img'); if (nxt) nxt.loading = 'eager';
    if (!user && !reduce && visible) { void tabs[cur].offsetWidth; tabs[cur].classList.add('run'); }
    if (!keepZoom) zoomTo(cur);
    if (window.innerWidth < 760) tabs[cur].scrollIntoView({ block: 'nearest', inline: 'center', behavior: reduce ? 'auto' : 'smooth' });
  }
  function tick() { clearTimeout(timer); if (user || reduce || !visible) return; timer = setTimeout(function () { show(cur + 1); tick(); }, DWELL); }
  function pick(i) { user = true; clearTimeout(timer); box.classList.add('picked'); show(i); }
  tabs.forEach(function (t, i) {
    t.addEventListener('click', function () { pick(i); });
    t.addEventListener('keydown', function (e) {
      var k = e.key;
      if (k === 'ArrowDown' || k === 'ArrowRight') { e.preventDefault(); user = true; clearTimeout(timer); box.classList.add('picked'); show(cur + 1, true); }
      else if (k === 'ArrowUp' || k === 'ArrowLeft') { e.preventDefault(); user = true; clearTimeout(timer); box.classList.add('picked'); show(cur - 1, true); }
      else if (k === 'Home') { e.preventDefault(); pick(0); tabs[0].focus(); }
      else if (k === 'End') { e.preventDefault(); pick(tabs.length - 1); tabs[tabs.length - 1].focus(); }
    });
  });
  box.addEventListener('mouseenter', function () { clearTimeout(timer); tabs[cur].classList.add('paused'); });
  box.addEventListener('mouseleave', function () { tabs[cur].classList.remove('paused'); if (!user) { show(cur, false, true); tick(); } });
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (es) {
      es.forEach(function (e) { var was = visible; visible = e.isIntersecting && e.intersectionRatio > 0.35; if (visible && !was) { show(cur); tick(); } else if (!visible) clearTimeout(timer); });
    }, { threshold: [0, 0.35, 0.6] }).observe(box);
  }
  // Full-size view: click or tap a screenshot. Native <dialog> closes with Esc; backdrop or image click closes too.
  var lb = box.querySelector('.jlb'), lbImg = lb && lb.querySelector('img');
  function big(img) { var u = img.currentSrc || img.src; return u.replace(/(-2400)?\.webp(\?.*)?$/, '-2400.webp'); }
  panels.forEach(function (p, k) {
    var b = p.querySelector('.jopen'); if (!b) return;
    b.addEventListener('click', function () {
      var img = p.querySelector('img'); user = true; clearTimeout(timer); box.classList.add('picked');
      if (!lb || typeof lb.showModal !== 'function') { window.open(big(img), '_blank', 'noopener'); return; }
      lbImg.src = big(img); lbImg.alt = img.alt; lb.showModal();
    });
  });
  if (lb) {
    lb.addEventListener('click', function (e) { if (e.target === lb || e.target === lbImg) lb.close(); });
    lb.querySelector('.jlb-x').addEventListener('click', function () { lb.close(); });
  }
  // warm the rest once the page is idle
  (window.requestIdleCallback || function (f) { setTimeout(f, 2500); })(function () { panels.forEach(function (p) { var i = p.querySelector('img'); if (i) i.loading = 'eager'; }); });
})();
