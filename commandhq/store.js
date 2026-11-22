/* CommandHQ — App Store link and launch offer switches.
 * ON LAUNCH DAY: set live to true and put the real App Store URL in url
 * (App Store Connect › App Information › Apple ID → https://apps.apple.com/app/id<AppleID>).
 * Until then every [data-store] button reads "Coming soon" and scrolls to pricing.
 * The launch offer banner and prices hide themselves after offerEnds.
 */
window.CHQ_STORE = {
  live: false,
  url: 'https://apps.apple.com/app/idXXXXXXXXXX',
  offerEnds: '2026-12-16T08:00:00Z',  // end of Dec 15, US Pacific
  // App Store Connect › Apps › CommandHQ › App Analytics › Campaigns: the "pt" provider token.
  // With it set, every store button carries a campaign (ct) naming its page and section,
  // so App Analytics shows downloads per button. Empty = plain links.
  pt: ''
};
/* Campaign name for one store button: page + section, e.g. "web-pricing-plans" (≤ 40 chars). */
window.chqCampaign = function (a) {
  if (a.getAttribute('data-store-ct')) return a.getAttribute('data-store-ct');
  var page = location.pathname.replace(/^\/commandhq\/?/, '').replace(/\/index\.html$/, '').replace(/\/$/, '').replace(/\//g, '-') || 'home';
  var sec = a.closest('section[id], header, footer, nav');
  var where = sec ? (sec.id || sec.tagName.toLowerCase()) : 'page';
  var card = a.closest('.price, .mini');   // a plan card: name the plan
  if (card) { var h = card.querySelector('h3') || card.querySelector('span'); if (h) where = (h.firstChild && h.firstChild.textContent || h.textContent).trim().split(/\s+/).slice(0, 2).join('-'); }
  return ('web-' + page + '-' + where).toLowerCase().replace(/[^a-z0-9-]/g, '').slice(0, 40);
};
document.addEventListener('DOMContentLoaded', function () {
  var s = window.CHQ_STORE;
  document.querySelectorAll('[data-store]').forEach(function (a) {
    var label = a.querySelector('[data-store-label]');
    if (s.live) {
      a.href = s.url + (s.pt ? (s.url.indexOf('?') < 0 ? '?' : '&') + 'pt=' + encodeURIComponent(s.pt) + '&ct=' + encodeURIComponent(window.chqCampaign(a)) + '&mt=8' : '');
      a.target = '_blank'; a.rel = 'noopener';
      if (label) label.textContent = a.getAttribute('data-live-label') || 'Download on the App Store';
    }
  });
  // Before launch, store buttons that point nowhere ("#") do nothing instead of jumping to the top.
  if (!s.live) document.querySelectorAll('a[data-store][href="#"]').forEach(function (a) {
    a.addEventListener('click', function (e) { e.preventDefault(); });
    a.setAttribute('aria-disabled', 'true');
  });
  if (Date.now() > Date.parse(s.offerEnds)) {
    document.querySelectorAll('[data-offer]').forEach(function (el) { el.hidden = true; });
    document.querySelectorAll('[data-after-offer]').forEach(function (el) { el.hidden = false; });
  }
});

/* Still images that turn into the video when clicked (no autoplaying tutorial clips). */
document.addEventListener('click', function (e) {
  var b = e.target.closest && e.target.closest('.media-frame.still .play-btn');
  if (!b) return;
  var f = b.parentElement, v = document.createElement('video');
  v.src = f.getAttribute('data-video'); v.controls = true; v.autoplay = true; v.playsInline = true;
  v.setAttribute('aria-label', (f.querySelector('img') || {}).alt || 'Video');
  f.classList.remove('still', 'bare'); f.innerHTML = ''; f.appendChild(v); v.play && v.play().catch(function () {});
});
/* A link to a FAQ entry (#faq-…) opens that answer. */
(function () {
  function openHash() { var id = location.hash.slice(1); if (!id) return; var d = document.getElementById(id); if (d && d.tagName === 'DETAILS') { d.open = true; d.classList.add('flash'); } }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', openHash); else openHash();
  window.addEventListener('hashchange', openHash);
})();
