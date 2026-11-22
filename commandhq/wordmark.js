/* CommandHQ particle wordmark (home page footer).
 * Ported from the kridallc.com "Krida LLC" footer: the word is drawn on a hidden canvas,
 * sampled into a grid of tiny points, and the points scatter from the cursor (or finger)
 * and spring back home. "Command" uses the light text colour, "HQ" the brand amber.
 */
(function () {
  function init() {
    var canvas = document.getElementById('chqParticles');
    if (!canvas) return;
    var ctx = canvas.getContext('2d');
    var container = canvas.parentElement;
    var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var particles = [];
    var mouse = { x: -9999, y: -9999 };
    var dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    var W = 0, H = 0;
    var LIGHT, AMBER;
    function readColors() { var cs = getComputedStyle(document.documentElement); LIGHT = cs.getPropertyValue('--dot-light').trim() || 'rgba(214,222,246,0.88)'; AMBER = cs.getPropertyValue('--dot-hq').trim() || 'rgba(254,160,40,0.95)'; }
    readColors();
    if (window.matchMedia) { var mq = window.matchMedia('(prefers-color-scheme: light)'); (mq.addEventListener ? mq.addEventListener('change', readColors) : mq.addListener(readColors)); }

    function build() {
      W = container.clientWidth;
      H = canvas.clientHeight || 180;
      if (!W || !H) return;
      canvas.width = W * dpr; canvas.height = H * dpr;
      var off = document.createElement('canvas');
      off.width = W * dpr; off.height = H * dpr;
      var o = off.getContext('2d');
      var fontSize = Math.min(H * 0.6, W * 0.15);
      function setFont() { o.font = "800 " + (fontSize * dpr) + "px -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Inter', 'Helvetica Neue', Arial, sans-serif"; }
      setFont();
      var w1 = o.measureText('Command').width, w2 = o.measureText('HQ').width;
      var maxWidth = W * dpr * 0.92;
      if (w1 + w2 > maxWidth) { fontSize *= maxWidth / (w1 + w2); setFont(); w1 = o.measureText('Command').width; w2 = o.measureText('HQ').width; }
      var x0 = (W * dpr - (w1 + w2)) / 2, cy = (H * dpr) / 2;
      o.textBaseline = 'middle'; o.textAlign = 'left';
      o.fillStyle = '#ffffff'; o.fillText('Command', x0, cy);
      o.fillStyle = '#ff0000'; o.fillText('HQ', x0 + w1, cy);   // red marks the amber part; only used for sampling
      var data = o.getImageData(0, 0, W * dpr, H * dpr).data;
      particles = [];
      var fixedStep = Math.max(3, Math.round(4 * dpr));
      var proportionalStep = Math.max(2, Math.floor(fontSize * dpr * 0.05));
      var step = Math.min(fixedStep, proportionalStep);
      for (var y = 0; y < H * dpr; y += step) {
        for (var x = 0; x < W * dpr; x += step) {
          var i = (y * (W * dpr) + x) * 4;
          if (data[i + 3] > 120) {
            var px = x / dpr, py = y / dpr;
            particles.push({ hx: px, hy: py, x: px, y: py, vx: 0, vy: 0, hq: data[i + 1] < 128 });
          }
        }
      }
    }

    build();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(build);

    canvas.addEventListener('mousemove', function (e) { var r = canvas.getBoundingClientRect(); mouse.x = e.clientX - r.left; mouse.y = e.clientY - r.top; });
    canvas.addEventListener('mouseleave', function () { mouse.x = -9999; mouse.y = -9999; });
    function touch(e) { var r = canvas.getBoundingClientRect(), t = e.touches[0]; mouse.x = t.clientX - r.left; mouse.y = t.clientY - r.top; }
    canvas.addEventListener('touchstart', touch, { passive: true });
    canvas.addEventListener('touchmove', touch, { passive: true });
    canvas.addEventListener('touchend', function () { mouse.x = -9999; mouse.y = -9999; });

    var visible = true;
    if ('IntersectionObserver' in window) new IntersectionObserver(function (es) { visible = es[0].isIntersecting; }).observe(canvas);

    function tick() {
      requestAnimationFrame(tick);
      if (!W || !H || !visible) return;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, W, H);
      var R = 55;
      for (var pass = 0; pass < 2; pass++) {
        ctx.fillStyle = pass ? AMBER : LIGHT;
        for (var i = 0; i < particles.length; i++) {
          var p = particles[i];
          if (p.hq !== !!pass) continue;
          if (!reduceMotion) {
            var dx = p.x - mouse.x, dy = p.y - mouse.y, d = Math.hypot(dx, dy);
            if (d < R) { var f = (R - d) / R, inv = 1 / (d || 1); p.vx += dx * inv * f * 3.2; p.vy += dy * inv * f * 3.2; }
            p.vx += (p.hx - p.x) * 0.06; p.vy += (p.hy - p.y) * 0.06;
            p.vx *= 0.82; p.vy *= 0.82; p.x += p.vx; p.y += p.vy;
          }
          ctx.fillRect(p.x, p.y, 1.6, 1.6);
        }
      }
    }
    tick();

    var t;
    window.addEventListener('resize', function () { clearTimeout(t); t = setTimeout(build, 250); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
