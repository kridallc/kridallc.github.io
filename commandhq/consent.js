/* CommandHQ — analytics consent (EU/UK-friendly).
 *
 * - Google Consent Mode v2 defaults: analytics denied for EEA/UK/CH visitors
 *   (Google applies this by visitor IP), granted elsewhere. Ads storage is
 *   always denied — this site runs no ads.
 * - Visitors whose browser time zone is in Europe see a banner and Google
 *   Analytics is NOT loaded until they choose "Accept".
 * - Everyone else gets analytics by default and can opt out any time from
 *   the "Cookie settings" link in the footer.
 * - The choice is remembered for 12 months (localStorage), then asked again.
 */
(function () {
  var GA_ID = 'G-F8CX00NGGY';
  var KEY = 'chq-consent-v1';
  var MAX_AGE = 365 * 24 * 60 * 60 * 1000;
  var REGIONS = ['AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','GR','HU','IE','IT','LV','LT','LU',
                 'MT','NL','PL','PT','RO','SK','SI','ES','SE','IS','LI','NO','GB','CH'];

  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  window.gtag = gtag;

  var denyAll = { ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied' };
  gtag('consent', 'default', Object.assign({ analytics_storage: 'denied', region: REGIONS, wait_for_update: 500 }, denyAll));
  gtag('consent', 'default', Object.assign({ analytics_storage: 'granted' }, denyAll));

  var tz = '';
  try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ''; } catch (e) {}
  var inEurope = /^Europe\//.test(tz) || /^Atlantic\/(Reykjavik|Canary|Madeira|Azores|Faroe)$/.test(tz);

  function readChoice() {
    try {
      var raw = JSON.parse(localStorage.getItem(KEY) || 'null');
      if (raw && (raw.v === 'granted' || raw.v === 'denied') && Date.now() - raw.t < MAX_AGE) return raw.v;
    } catch (e) {}
    return null;
  }
  function saveChoice(v) {
    try { localStorage.setItem(KEY, JSON.stringify({ v: v, t: Date.now() })); } catch (e) {}
  }

  var loaded = false;
  function loadGA() {
    if (loaded) return;
    loaded = true;
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
    document.head.appendChild(s);
    gtag('js', new Date());
    gtag('config', GA_ID);
  }
  function clearGaCookies() {
    document.cookie.split(';').forEach(function (c) {
      var name = c.split('=')[0].trim();
      if (!/^_ga/.test(name)) return;
      var host = location.hostname;
      ['', '; domain=' + host, '; domain=.' + host.replace(/^www\./, '')].forEach(function (d) {
        document.cookie = name + '=; Max-Age=0; path=/' + d;
      });
    });
  }

  var choice = readChoice();
  // Global Privacy Control: treat the browser's GPC signal as an opt-out unless the visitor later chooses Accept.
  var gpc = false; try { gpc = navigator.globalPrivacyControl === true; } catch (e) {}
  if (!choice && gpc) choice = 'denied';
  if (choice === 'granted') { gtag('consent', 'update', { analytics_storage: 'granted' }); loadGA(); }
  else if (choice === 'denied') { gtag('consent', 'update', { analytics_storage: 'denied' }); }
  else if (!inEurope) { loadGA(); }

  /* ---------- Banner ---------- */
  var css = ''
    + '.chq-consent{position:fixed;left:50%;bottom:16px;transform:translateX(-50%);z-index:100001;width:min(640px,calc(100% - 32px));'
    + 'background:var(--surface-1,#141A33);border:1px solid rgba(254,143,8,0.35);border-radius:14px;padding:1rem 1.15rem;'
    + 'box-shadow:0 20px 60px rgba(0,0,0,0.55);backdrop-filter:blur(14px);color:#e8f0fe;font-family:"DM Sans",system-ui,sans-serif;'
    + 'display:flex;gap:1rem;align-items:center;flex-wrap:wrap;animation:crIn .3s ease}'
    + '.chq-consent p{flex:1 1 280px;margin:0;font-size:.84rem;line-height:1.55;color:var(--muted,#a9b8d6)}'
    + '.chq-consent p strong{color:var(--text,#e8f0fe);font-weight:600}'
    + '.chq-consent a{color:#FE8F08;text-decoration:none}.chq-consent a:hover{text-decoration:underline}'
    + '.chq-consent .chq-btns{display:flex;gap:.5rem;flex:0 0 auto}'
    + '.chq-consent button{font:500 .72rem/1 -apple-system,BlinkMacSystemFont,system-ui,sans-serif;text-transform:uppercase;letter-spacing:.05em;'
    + 'min-height:44px;padding:.8rem 1.2rem;border-radius:9px;cursor:pointer;border:1.5px solid #FE8F08;transition:background .18s,color .18s}'
    + '.chq-consent .chq-accept{background:#FE8F08;color:#090D1F}.chq-consent .chq-accept:hover{background:#e57e00;border-color:#e57e00}'
    + '.chq-consent .chq-decline{background:transparent;color:#FE8F08}.chq-consent .chq-decline:hover{background:rgba(254,143,8,.1)}'
    + '.chq-consent button:focus-visible{outline:2px solid #e8f0fe;outline-offset:2px}'
    + '@keyframes crIn{from{opacity:0;transform:translate(-50%,12px)}to{opacity:1;transform:translate(-50%,0)}}'
    + '@media (max-width:520px){.chq-consent .chq-btns{width:100%}.chq-consent button{flex:1}}'
    + '@media (prefers-reduced-motion:reduce){.chq-consent{animation:none}}';

  function showBanner() {
    if (document.getElementById('chqConsent')) return;
    if (!document.getElementById('chqConsentCss')) {
      var st = document.createElement('style'); st.id = 'chqConsentCss'; st.textContent = css; document.head.appendChild(st);
    }
    var current = readChoice();
    var box = document.createElement('div');
    box.className = 'chq-consent'; box.id = 'chqConsent';
    box.setAttribute('role', 'dialog'); box.setAttribute('aria-live', 'polite'); box.setAttribute('aria-label', 'Cookie preferences');
    box.innerHTML = '<p><strong>Analytics cookies?</strong> We use Google Analytics to see how visitors use this website. '
      + 'The CommandHQ app itself collects nothing. The site works the same either way. '
      + '<a href="/commandhq/privacy/#website">Privacy policy</a>'
      + (current ? ' · Current choice: ' + (current === 'granted' ? 'accepted' : 'declined') : '') + '</p>'
      + '<div class="chq-btns"><button type="button" class="chq-decline">Decline</button>'
      + '<button type="button" class="chq-accept">Accept</button></div>';
    document.body.appendChild(box);
    box.querySelector('.chq-accept').addEventListener('click', function () {
      saveChoice('granted'); gtag('consent', 'update', { analytics_storage: 'granted' }); loadGA(); box.remove();
    });
    box.querySelector('.chq-decline').addEventListener('click', function () {
      saveChoice('denied'); gtag('consent', 'update', { analytics_storage: 'denied' }); clearGaCookies(); box.remove();
    });
  }
  window.crOpenConsent = showBanner;

  function wire() {
    document.querySelectorAll('[data-consent-open]').forEach(function (el) {
      el.addEventListener('click', function (e) { e.preventDefault(); showBanner(); });
    });
    if (!choice && inEurope) showBanner();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wire);
  else wire();
})();

/* Site events for Google Analytics. They only reach Google when analytics is
 * allowed (see above); otherwise they stay in this page. No personal data:
 * guide ids, devices, button places, FAQ titles and search words only.
 *   video_start / video_progress (25, 50, 75) / video_complete — every <video>
 *   video_step     — a step clicked in a guide's step list
 *   search         — words typed in the video search (GA's own "search_term")
 *   video_filter   — device switch / area menu on the videos page
 *   store_click    — any App Store / "Coming soon" button, with its place
 *   social_click   — a footer social icon
 *   faq_open       — a FAQ question opened
 */
(function () {
  function send(name, p) { try { window.gtag('event', name, p || {}); } catch (e) {} }
  function info(v) {
    var s = (v.currentSrc || v.getAttribute('src') || '').split('?')[0];
    var m = s.match(/\/(iphone|ipad|mac|watch|duo)\/([a-zA-Z-]+)\/([^\/]+)\.(mp4|webm|mov)$/);
    return m ? { video_id: m[3], video_device: m[1], video_lang: m[2] }
             : { video_id: s.split('/').pop() || 'unknown', video_device: '', video_lang: '' };
  }
  var state = {};
  function st(v) { var k = (v.currentSrc || v.getAttribute('src') || '').split('?')[0]; return state[k] || (state[k] = { started: false, q: {} }); }
  document.addEventListener('play', function (e) {
    var v = e.target; if (!v || v.tagName !== 'VIDEO') return;
    var s = st(v); if (s.started) return; s.started = true; send('video_start', info(v));
  }, true);
  document.addEventListener('timeupdate', function (e) {
    var v = e.target; if (!v || v.tagName !== 'VIDEO' || !v.duration || !isFinite(v.duration)) return;
    var s = st(v), pct = v.currentTime / v.duration * 100;
    [25, 50, 75].forEach(function (q) {
      if (pct >= q && !s.q[q]) { s.q[q] = true; var p = info(v); p.percent = q; send('video_progress', p); }
    });
  }, true);
  document.addEventListener('ended', function (e) {
    var v = e.target; if (!v || v.tagName !== 'VIDEO') return;
    var s = st(v); if (s.done) return; s.done = true; send('video_complete', info(v));
  }, true);

  document.addEventListener('click', function (e) {
    var t = e.target && e.target.closest ? e.target : null; if (!t) return;
    var a = t.closest('[data-store]');
    if (a) {
      send('store_click', {
        placement: window.chqCampaign ? window.chqCampaign(a) : location.pathname,
        button_text: (a.textContent || '').trim().slice(0, 60),
        store_live: !!(window.CHQ_STORE && window.CHQ_STORE.live)
      });
      return;
    }
    var so = t.closest('a[rel~="me"]');
    if (so) { send('social_click', { network: (so.getAttribute('aria-label') || so.href || '').replace(/^CommandHQ on /, '').slice(0, 40) }); return; }
    var step = t.closest('.step');
    if (step) {
      var box = step.closest('dialog, .gvid, main') || document, v = box.querySelector('video') || document.querySelector('video');
      var p = v ? info(v) : {}; var all = step.parentNode ? Array.prototype.indexOf.call(step.parentNode.children, step) : -1;
      p.step = all + 1; send('video_step', p); return;
    }
    var seg = t.closest('.seg button');
    if (seg) { send('video_filter', { filter: 'device', value: (seg.getAttribute('data-d') || seg.textContent || '').trim().slice(0, 30) }); }
  }, true);

  document.addEventListener('change', function (e) {
    if (e.target && e.target.id === 'areas') send('video_filter', { filter: 'area', value: String(e.target.value).slice(0, 40) });
  }, true);

  var timer = null, last = '';
  document.addEventListener('input', function (e) {
    if (!e.target || e.target.id !== 'q') return;
    clearTimeout(timer);
    timer = setTimeout(function () {
      var q = String(e.target.value || '').trim().toLowerCase().slice(0, 80);
      if (q.length < 2 || q === last) return; last = q;
      var c = document.getElementById('count');
      send('search', { search_term: q, results: c ? (c.textContent || '').trim().slice(0, 60) : '' });
    }, 1500);
  }, true);

  document.addEventListener('toggle', function (e) {
    var d = e.target; if (!d || d.tagName !== 'DETAILS' || !d.open) return;
    var s = d.querySelector('summary'); send('faq_open', { question: (s ? s.textContent : d.id || '').trim().slice(0, 100) });
  }, true);
})();

