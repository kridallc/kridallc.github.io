#!/usr/bin/env python3
"""Build the CommandHQ video guide pages from commandhq/videos/catalog.json.

Run from the site root after every publish of the videos (the app repo's
scripts/videos_publish.py writes catalog.json; this script reads it):

    python3 _videos/build_pages.py

It writes, all generated (don't hand-edit; the next run overwrites them):
  commandhq/videos/<slug>/index.html   one page per guide: player, steps with times
                                       (the video's text version), JSON-LD VideoObject
                                       with "key moments" (Clip), related guides
  commandhq/videos/<slug>/<device>.vtt chapter track per clip, from its moments
  commandhq/videos/sitemap.xml         video sitemap for the guide pages
Pages of guides that left the catalog are removed (only folders this script made,
which carry a .generated marker).
"""
import html, json, os, re, shutil, sys
from datetime import date

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
VID = os.path.join(ROOT, 'commandhq', 'videos')
ORIGIN = 'https://kridallc.com'
DEV_NAME = {'iphone': 'iPhone', 'ipad': 'iPad', 'mac': 'Mac'}
DEV_ORDER = ['iphone', 'ipad', 'mac']
FALLBACK_THUMB = ORIGIN + '/commandhq/media/og.jpg'
e = html.escape


def slug(i):
    return re.sub(r'([a-z0-9])([A-Z])', r'\1-\2', i).replace('.', '-').lower()


def mmss(t):
    t = int(t or 0)
    return f'{t // 60}:{t % 60:02d}'


def iso_dur(t):
    t = int(round(t or 0))
    return f'PT{t // 60}M{t % 60}S' if t >= 60 else f'PT{t}S'


def vtt_time(t):
    ms = int(round(t * 1000))
    return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}.{ms % 1000:03d}'


def vtt(v):
    ms = [m for m in v.get('moments') or [] if m.get('t') is not None]
    out = ['WEBVTT', '']
    for i, m in enumerate(ms):
        end = ms[i + 1]['t'] if i + 1 < len(ms) else max(v.get('duration') or 0, m['t'] + 1)
        if end <= m['t']:
            end = m['t'] + 0.5
        out += [str(i + 1), f"{vtt_time(m['t'])} --> {vtt_time(end)}", m['text'].replace('-->', '→'), '']
    return '\n'.join(out)


def chrome(index_html):
    """Head stylesheet/scripts, nav and footer, taken from the videos page so they stay in step."""
    nav = re.search(r'  <nav>.*?</nav>\n', index_html, re.S).group(0)
    foot = re.search(r'  <footer[ >].*?</footer>\n', index_html, re.S).group(0)
    links = re.search(r'  <link rel="stylesheet".*?</script>\n  <script src="/commandhq/store\.js[^"]*"></script>\n', index_html, re.S).group(0)
    return nav, foot, links


CSS = """
    .gwrap { max-width: 1180px; margin: 0 auto; padding: 0 2rem 6rem; }
    .crumb { font-size: 0.85rem; color: var(--muted); margin-bottom: 0.6rem; }
    .crumb a { color: var(--muted); }
    .gdev { display: flex; gap: 0.45rem; flex-wrap: wrap; margin: 0 0 1rem; }
    .chip { font: 500 0.82rem/1 var(--sans); color: var(--muted); background: transparent; border: 1px solid var(--border-soft); border-radius: 999px; padding: 0.55rem 0.95rem; cursor: pointer; min-height: 36px; white-space: nowrap; text-decoration: none; display: inline-flex; align-items: center; }
    .chip:hover { color: var(--text); border-color: var(--border); }
    .chip[aria-pressed="true"] { color: var(--on-amber); background: linear-gradient(135deg, var(--btn-amber), var(--btn-gold)); border-color: transparent; font-weight: 600; }
    .chip:focus-visible, .step:focus-visible { outline: 2px solid var(--btn-amber); outline-offset: 2px; }
    .gplayer { display: grid; grid-template-columns: minmax(0, 1.75fr) minmax(280px, 1fr); gap: 1.4rem; align-items: start; }
    .gvid { background: #000; border-radius: 14px; overflow: hidden; border: 1px solid var(--border-soft); }
    .gvid video { width: 100%; aspect-ratio: 16/9; display: block; background: #000; }
    .gside h2, .gmore h2 { font-size: 0.72rem; font-family: var(--sans); text-transform: uppercase; letter-spacing: 0.12em; color: var(--amber); font-weight: 500; margin: 0 0 0.5rem; }
    .gside .note { font-size: 0.8rem; color: var(--muted2); margin: 0.5rem 0 0; }
    .steps { list-style: none; margin: 0; padding: 0; border: 1px solid var(--border-soft); border-radius: 12px; }
    .steps[hidden] { display: none; }
    .step { display: grid; grid-template-columns: 1.6rem 1fr auto; gap: 0.5rem; align-items: baseline; width: 100%; text-align: left; background: none; border: 0; border-bottom: 1px solid var(--border-soft); padding: 0.6rem 0.8rem; color: var(--muted); font: inherit; font-size: 0.88rem; line-height: 1.4; cursor: pointer; }
    .steps li:last-child .step { border-bottom: 0; }
    .step:hover { color: var(--text); background: var(--ghost); }
    .step .sn, .step .st { font-family: var(--sans); font-size: 0.72rem; color: var(--muted2); font-variant-numeric: tabular-nums; }
    .step[aria-current="step"] { color: var(--text); background: var(--amber-light); box-shadow: inset 3px 0 0 var(--btn-amber); }
    .step[aria-current="step"] .sn, .step[aria-current="step"] .st { color: var(--amber); }
    .gmore { margin-top: 2.6rem; display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; }
    .gmore ul { margin: 0 0 0 1.1rem; } .gmore li { color: var(--muted); font-size: 0.9rem; margin-bottom: 0.35rem; }
    .gmore .rel { list-style: none; margin: 0; } .gmore .rel a { color: var(--text); }
    .gcta { margin-top: 2.6rem; padding-top: 1.6rem; border-top: 1px solid var(--border-soft); display: flex; gap: 0.8rem; flex-wrap: wrap; align-items: center; }
    @media (max-width: 860px) { .gplayer, .gmore { grid-template-columns: 1fr; } .gwrap { padding: 0 1.25rem 5rem; } }
"""

SCRIPT = r"""
  <script>
  (function () {
    var vid = document.getElementById('gvideo'), clips = JSON.parse(document.getElementById('gclips').textContent), cur = null;
    var pick = function () {
      var p = new URLSearchParams(location.search), d = p.get('d'), ua = navigator.userAgent || '';
      if (clips[d]) return d;
      var g = /iPhone|iPod/.test(ua) || (/Android/.test(ua) && /Mobile/.test(ua)) ? 'iphone' : (/iPad/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1) || /Android/.test(ua)) ? 'ipad' : 'mac';
      return clips[g] ? g : Object.keys(clips)[0];
    };
    function show(d, t, play) {
      cur = d; var c = clips[d];
      document.querySelectorAll('[data-dev]').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.dev === d)); });
      document.querySelectorAll('.steps').forEach(function (l) { l.hidden = l.dataset.list !== d; });
      document.getElementById('gdevname').textContent = c.name + ' · ' + c.dur;
      [].slice.call(vid.querySelectorAll('track')).forEach(function (x) { x.remove(); });
      var tk = document.createElement('track'); tk.kind = 'chapters'; tk.srclang = 'en'; tk.label = 'Steps'; tk.src = c.vtt; vid.appendChild(tk);
      if (c.poster) vid.poster = c.poster; else vid.removeAttribute('poster');
      vid.src = c.src;
      if (t) seek(t, play);
      var q = new URLSearchParams(location.search); q.set('d', d); if (!t) q.delete('t');
      history.replaceState(null, '', '?' + q.toString());
    }
    function seek(t, play) {
      var go = function () { try { vid.currentTime = Math.max(0, t - 0.3); } catch (e) {} if (play !== false) { var p = vid.play(); if (p && p.catch) p.catch(function () {}); } };
      if (vid.readyState >= 1) go(); else vid.addEventListener('loadedmetadata', go, { once: true });
    }
    document.querySelectorAll('[data-dev]').forEach(function (b) { b.onclick = function () { show(b.dataset.dev, 0); }; });
    document.querySelectorAll('.step').forEach(function (b) { b.onclick = function () { seek(parseFloat(b.dataset.t)); }; });
    vid.addEventListener('timeupdate', function () {
      var list = document.querySelector('.steps[data-list="' + cur + '"]'); if (!list) return;
      var rows = list.querySelectorAll('.step'), t = vid.currentTime + 0.05, i = -1;
      rows.forEach(function (r, j) { if (parseFloat(r.dataset.t) <= t) i = j; });
      rows.forEach(function (r, j) { if (j === i) r.setAttribute('aria-current', 'step'); else r.removeAttribute('aria-current'); });
    });
    var t0 = parseFloat(new URLSearchParams(location.search).get('t')) || 0;
    show(pick(), t0, false);
  })();
  </script>
"""


def page(g, cat, nav, foot, links, related):
    base = cat.get('videoBase', '')
    s = slug(g['id'])
    url = f'{ORIGIN}/commandhq/videos/{s}/'
    devs = [d for d in DEV_ORDER if d in g['devs']]
    first = g['devs'][devs[0]]
    thumb = (base + first['poster']) if first.get('poster') else FALLBACK_THUMB
    updated = cat.get('updated') or date.today().isoformat()

    ld = []
    for d in devs:
        v = g['devs'][d]
        ms = [m for m in v.get('moments') or [] if m.get('t') is not None]
        obj = {
            '@context': 'https://schema.org', '@type': 'VideoObject',
            'name': f"{g['title']} on {DEV_NAME[d]} | CommandHQ",
            'description': g['summary'],
            'thumbnailUrl': [(base + v['poster']) if v.get('poster') else FALLBACK_THUMB],
            'uploadDate': updated + 'T12:00:00-07:00', 'duration': iso_dur(v.get('duration')),
            'contentUrl': base + v['src'], 'embedUrl': f'{url}?d={d}', 'inLanguage': 'en',
            'publisher': {'@type': 'Organization', 'name': 'Krida LLC', 'url': ORIGIN + '/'},
        }
        if ms:
            obj['hasPart'] = [{
                '@type': 'Clip', 'name': m['text'], 'startOffset': int(m['t']),
                'endOffset': int(ms[i + 1]['t']) if i + 1 < len(ms) else int(round(v.get('duration') or m['t'] + 1)),
                'url': f"{url}?d={d}&t={int(m['t'])}",
            } for i, m in enumerate(ms)]
        ld.append(obj)
    ld.append({'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': 'CommandHQ', 'item': ORIGIN + '/commandhq/'},
        {'@type': 'ListItem', 'position': 2, 'name': 'Video guides', 'item': ORIGIN + '/commandhq/videos/'},
        {'@type': 'ListItem', 'position': 3, 'name': g['title'], 'item': url}]})

    clips = {d: {'name': DEV_NAME[d], 'dur': mmss(g['devs'][d].get('duration')), 'src': base + g['devs'][d]['src'],
                 'poster': (base + g['devs'][d]['poster']) if g['devs'][d].get('poster') else '',
                 'vtt': f'/commandhq/videos/{s}/{d}.vtt'} for d in devs}

    lists = []
    for d in devs:
        v = g['devs'][d]
        ms = [m for m in v.get('moments') or [] if m.get('t') is not None]
        rows = ''.join(
            f'<li><button type="button" class="step" data-t="{m["t"]}" aria-label="Step {i + 1}: {e(m["text"])}, at {mmss(m["t"])}">'
            f'<span class="sn" aria-hidden="true">{i + 1}</span><span aria-hidden="true">{e(m["text"])}</span>'
            f'<span class="st" aria-hidden="true">{mmss(m["t"])}</span></button></li>' for i, m in enumerate(ms))
        if not ms:
            rows = ''.join(f'<li><span class="step">{e(x)}</span></li>' for x in v.get('steps') or [])
        hidden = '' if d == devs[0] else ' hidden'
        lists.append(f'<ol class="steps" data-list="{d}" aria-label="Steps on {DEV_NAME[d]}"{hidden}>{rows}</ol>')

    scen = ''.join(f'<li>{e(x)}</li>' for x in g['scenarios'])
    rel = ''.join(f'<li><a href="/commandhq/videos/{slug(r["id"])}/">{e(r["title"])}</a></li>' for r in related)
    devbtns = ''.join(f'<button type="button" class="chip" data-dev="{d}" aria-pressed="{str(d == devs[0]).lower()}">{DEV_NAME[d]}</button>' for d in devs)
    first_v = g['devs'][devs[0]]
    poster_attr = f' poster="{e(base + first_v["poster"])}"' if first_v.get('poster') else ''
    ld_json = json.dumps(ld, ensure_ascii=False, indent=1).replace('</', '<\\/')
    clips_json = json.dumps(clips, ensure_ascii=False).replace('</', '<\\/')
    title = f"{g['title']} — CommandHQ video guide"
    desc = f"{g['summary']} A short video on {', '.join(DEV_NAME[d] for d in devs[:-1]) + ' and ' + DEV_NAME[devs[-1]] if len(devs) > 1 else DEV_NAME[devs[0]]}, with each step and its time."

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <!-- Generated by _videos/build_pages.py from videos/catalog.json. Don't edit; rerun the script. -->
  <title>{e(title)}</title>
  <meta name="description" content="{e(desc)}" />
  <link rel="canonical" href="{url}" />
  <link rel="icon" type="image/png" href="/commandhq/media/icon-180.png" />
  <link rel="apple-touch-icon" href="/commandhq/media/icon-180.png" />
  <meta property="og:type" content="video.other" />
  <meta property="og:url" content="{url}" />
  <meta property="og:title" content="{e(title)}" />
  <meta property="og:description" content="{e(g['summary'])}" />
  <meta property="og:image" content="{e(thumb)}" />
  <meta name="twitter:card" content="summary_large_image" />
{links}  <style>{CSS}  </style>
  <script type="application/ld+json">
{ld_json}
  </script>
</head>
<body>
{nav}
  <header class="page-intro">
    <p class="crumb"><a href="/commandhq/videos/">Video guides</a> › {e(g['area'])}</p>
    <h1>{e(g['title'])}</h1>
    <p class="sub">{e(g['summary'])}</p>
  </header>

  <main class="gwrap">
    <div class="gdev" role="group" aria-label="Device">{devbtns}</div>
    <div class="gplayer">
      <div class="gvid"><video id="gvideo" controls playsinline preload="metadata"{poster_attr} src="{e(base + first_v['src'])}"></video></div>
      <div class="gside">
        <h2>Steps <span id="gdevname" style="text-transform:none;letter-spacing:0;color:var(--muted2)"></span></h2>
        {''.join(lists)}
        <p class="note">The videos have music and no narration. These steps are their text version: select one to play from that moment.</p>
      </div>
    </div>
    <div class="gmore">
      <div>{'<h2>When you’d use it</h2><ul>' + scen + '</ul>' if scen else ''}</div>
      <div>{'<h2>More in ' + e(g['area']) + '</h2><ul class="rel">' + rel + '</ul>' if rel else ''}</div>
    </div>
    <div class="gcta">
      <a href="/commandhq/pricing/" class="btn btn-primary" data-store data-live-label="Get CommandHQ"><span data-store-label>Coming soon</span></a>
      <a href="/commandhq/videos/" class="chip">All video guides</a>
      <a href="/commandhq/features/" class="chip">See all features</a>
    </div>
  </main>

{foot}  <script type="application/json" id="gclips">{clips_json}</script>{SCRIPT}</body>
</html>
"""


def main():
    cat = json.load(open(os.path.join(VID, 'catalog.json'), encoding='utf-8'))
    index_html = open(os.path.join(VID, 'index.html'), encoding='utf-8').read()
    nav, foot, links = chrome(index_html)
    guides, by = [], {}
    for v in cat['videos']:
        g = by.get(v['id'])
        if not g:
            g = by[v['id']] = {'id': v['id'], 'title': v['title'], 'area': v['area'], 'summary': v.get('summary', ''),
                               'scenarios': v.get('scenarios') or [], 'devs': {}}
            guides.append(g)
        g['devs'][v['device']] = v

    made = set()
    for g in guides:
        s = slug(g['id'])
        if s in made:
            sys.exit(f'slug clash: {s}')
        made.add(s)
        d = os.path.join(VID, s)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, '.generated'), 'w').write('build_pages.py\n')
        same = [x for x in guides if x['area'] == g['area'] and x['id'] != g['id']]
        i = [x['id'] for x in guides].index(g['id'])
        related = sorted(same, key=lambda x: abs([y['id'] for y in guides].index(x['id']) - i))[:6]
        open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(page(g, cat, nav, foot, links, related))
        for dev, v in g['devs'].items():
            open(os.path.join(d, f'{dev}.vtt'), 'w', encoding='utf-8').write(vtt(v))

    for name in os.listdir(VID):  # remove pages of guides no longer in the catalog
        p = os.path.join(VID, name)
        if os.path.isdir(p) and name not in made and os.path.exists(os.path.join(p, '.generated')):
            shutil.rmtree(p)

    updated = cat.get('updated') or date.today().isoformat()
    base = cat.get('videoBase', '')
    urls = []
    for g in guides:
        s = slug(g['id'])
        vids = []
        for d in [x for x in DEV_ORDER if x in g['devs']]:
            v = g['devs'][d]
            th = (base + v['poster']) if v.get('poster') else FALLBACK_THUMB
            vids.append(f"""    <video:video>
      <video:thumbnail_loc>{e(th)}</video:thumbnail_loc>
      <video:title>{e(g['title'] + ' on ' + DEV_NAME[d])}</video:title>
      <video:description>{e(g['summary'])}</video:description>
      <video:content_loc>{e(base + v['src'])}</video:content_loc>
      <video:duration>{int(round(v.get('duration') or 0))}</video:duration>
      <video:publication_date>{updated}</video:publication_date>
      <video:family_friendly>yes</video:family_friendly>
    </video:video>""")
        urls.append(f"  <url>\n    <loc>{ORIGIN}/commandhq/videos/{s}/</loc>\n    <lastmod>{updated}</lastmod>\n" + '\n'.join(vids) + '\n  </url>')
    open(os.path.join(VID, 'sitemap.xml'), 'w', encoding='utf-8').write(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!-- Generated by _videos/build_pages.py. Don\'t edit; rerun the script. -->\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">\n'
        + '\n'.join(urls) + '\n</urlset>\n')
    print(f'{len(guides)} guide pages, {sum(len(g["devs"]) for g in guides)} chapter files, sitemap with {len(guides)} pages')


if __name__ == '__main__':
    main()
