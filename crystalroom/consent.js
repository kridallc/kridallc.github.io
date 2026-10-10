/* CrystalRoom — analytics consent (EU/UK-friendly).
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
  var KEY = 'cr-consent-v1';
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
  if (choice === 'granted') { gtag('consent', 'update', { analytics_storage: 'granted' }); loadGA(); }
  else if (choice === 'denied') { gtag('consent', 'update', { analytics_storage: 'denied' }); }
  else if (!inEurope) { loadGA(); }

  /* ---------- Banner ---------- */
  var css = ''
    + '.cr-consent{position:fixed;left:50%;bottom:16px;transform:translateX(-50%);z-index:100001;width:min(640px,calc(100% - 32px));'
    + 'background:rgba(12,18,40,0.97);border:1px solid rgba(56,189,248,0.3);border-radius:14px;padding:1rem 1.15rem;'
    + 'box-shadow:0 20px 60px rgba(0,0,0,0.55);backdrop-filter:blur(14px);color:#e8f0fe;font-family:"DM Sans",system-ui,sans-serif;'
    + 'display:flex;gap:1rem;align-items:center;flex-wrap:wrap;animation:crIn .3s ease}'
    + '.cr-consent p{flex:1 1 280px;margin:0;font-size:.84rem;line-height:1.55;color:#a9b8d6}'
    + '.cr-consent p strong{color:#e8f0fe;font-weight:500}'
    + '.cr-consent a{color:#38bdf8;text-decoration:none}.cr-consent a:hover{text-decoration:underline}'
    + '.cr-consent .cr-btns{display:flex;gap:.5rem;flex:0 0 auto}'
    + '.cr-consent button{font:500 .72rem/1 "JetBrains Mono",ui-monospace,monospace;text-transform:uppercase;letter-spacing:.05em;'
    + 'padding:.7rem 1.1rem;border-radius:9px;cursor:pointer;border:1.5px solid #38bdf8;transition:background .18s,color .18s}'
    + '.cr-consent .cr-accept{background:#38bdf8;color:#050818}.cr-consent .cr-accept:hover{background:#0ea5e9;border-color:#0ea5e9}'
    + '.cr-consent .cr-decline{background:transparent;color:#38bdf8}.cr-consent .cr-decline:hover{background:rgba(56,189,248,.1)}'
    + '.cr-consent button:focus-visible{outline:2px solid #e8f0fe;outline-offset:2px}'
    + '@keyframes crIn{from{opacity:0;transform:translate(-50%,12px)}to{opacity:1;transform:translate(-50%,0)}}'
    + '@media (max-width:520px){.cr-consent .cr-btns{width:100%}.cr-consent button{flex:1}}'
    + '@media (prefers-reduced-motion:reduce){.cr-consent{animation:none}}';

  function showBanner() {
    if (document.getElementById('crConsent')) return;
    if (!document.getElementById('crConsentCss')) {
      var st = document.createElement('style'); st.id = 'crConsentCss'; st.textContent = css; document.head.appendChild(st);
    }
    var current = readChoice();
    var box = document.createElement('div');
    box.className = 'cr-consent'; box.id = 'crConsent';
    box.setAttribute('role', 'dialog'); box.setAttribute('aria-live', 'polite'); box.setAttribute('aria-label', 'Cookie preferences');
    box.innerHTML = '<p><strong>Analytics cookies?</strong> We use Google Analytics to see how visitors use this website. '
      + 'The CrystalRoom app itself collects nothing. The site works the same either way. '
      + '<a href="/crystalroom/privacy/#website">Privacy policy</a>'
      + (current ? ' · Current choice: ' + (current === 'granted' ? 'accepted' : 'declined') : '') + '</p>'
      + '<div class="cr-btns"><button type="button" class="cr-decline">Decline</button>'
      + '<button type="button" class="cr-accept">Accept</button></div>';
    document.body.appendChild(box);
    box.querySelector('.cr-accept').addEventListener('click', function () {
      saveChoice('granted'); gtag('consent', 'update', { analytics_storage: 'granted' }); loadGA(); box.remove();
    });
    box.querySelector('.cr-decline').addEventListener('click', function () {
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
