#!/usr/bin/env python3
"""
CommandHQ website translations: English pages are the source of truth.

  python3 _i18n/i18n.py extract            # English pages -> _i18n/catalog/en.json (run after any copy change)
  python3 _i18n/i18n.py status             # per language: translated / missing / out of date
  python3 _i18n/i18n.py translate de       # fill missing + out-of-date strings by machine (needs ANTHROPIC_API_KEY)
  python3 _i18n/i18n.py build              # write /commandhq/<lang>/... for every language in config.json
  python3 _i18n/i18n.py pseudo             # preview build at /commandhq/xx/ with every string bracketed ⟦…⟧ (finds untranslatable text)
  python3 _i18n/i18n.py check              # self-test: English rebuilt from its own catalog is byte-identical

How it works
- Each page is split into "segments": the smallest runs of visible text (with their inline tags such as
  <strong>, <em>, <a>) inside block elements, plus translatable attributes (alt, title, aria-label,
  placeholder, meta description / og / twitter text). Scripts, styles and SVG are never touched.
- A segment's key is a hash of its English text. Identical text (nav, footer) is translated once.
- Translations live in _i18n/translations/<lang>.json as {key: {"text", "src", "status"}}.
  "src" is the English it was translated from: if the English changes, the key changes, so the old
  translation is simply no longer used and the new text shows as missing until translated.
  status: "machine" (from `translate`) or "reviewed" (a person checked it; `translate` never overwrites those).
- A missing translation falls back to English, so a build never breaks.
- With no languages in config.json, `build` changes nothing: the English site is exactly as written.
Standard library only (Python 3.8+).
"""
import hashlib, html, json, os, re, sys, urllib.request
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, "config.json"), encoding="utf-8"))
ROOT = os.path.normpath(os.path.join(HERE, CFG["site_root"]))
BASE = CFG["base"]                      # "commandhq"
PAGES = CFG["pages"]                    # paths relative to /<base>/
CATALOG = os.path.join(HERE, "catalog", "en.json")
TRDIR = os.path.join(HERE, "translations")

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
OPAQUE = {"script", "style", "svg", "noscript", "template", "canvas", "video", "audio", "iframe", "picture", "img", "input", "select", "textarea", "code", "pre", "kbd"}
INLINE = {"a", "strong", "em", "b", "i", "span", "s", "small", "sup", "sub", "u", "mark", "abbr", "time", "br", "q", "cite", "dfn", "bdi", "bdo", "data", "wbr"}
ATTRS = ("alt", "title", "aria-label", "placeholder")
META_NAMES = {"description", "twitter:title", "twitter:description"}
META_PROPS = {"og:title", "og:description", "og:image:alt"}
NO_TRANSLATE = "data-no-i18n"           # put on any element to keep it as is (brand names, code)

def key_of(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]

def has_words(text):
    t = re.sub(r"<[^>]+>|&[a-z#0-9]+;", " ", text)
    return re.search(r"[A-Za-z]{2,}", t) is not None

class Node:
    __slots__ = ("tag", "attrs", "start", "inner_start", "inner_end", "end", "children", "parent", "raw_start_tag")
    def __init__(self, tag, attrs, start, inner_start, parent, raw):
        self.tag, self.attrs, self.start, self.inner_start = tag, dict(attrs), start, inner_start
        self.inner_end = self.end = None
        self.children, self.parent, self.raw_start_tag = [], parent, raw

class Text:
    __slots__ = ("start", "end", "parent")
    def __init__(self, s, e, p): self.start, self.end, self.parent = s, e, p

class Tree(HTMLParser):
    """Builds an element tree with exact source offsets (no character-reference conversion)."""
    def __init__(self, src):
        super().__init__(convert_charrefs=False)
        self.src = src
        self.lines = [0]
        for m in re.finditer("\n", src): self.lines.append(m.end())
        self.root = Node("#root", [], 0, 0, None, "")
        self.cur = self.root
        self.feed(src); self.close()
        self.root.inner_end = self.root.end = len(src)

    def off(self):
        ln, col = self.getpos(); return self.lines[ln - 1] + col

    def handle_starttag(self, tag, attrs):
        s = self.off(); raw = self.get_starttag_text()
        n = Node(tag, attrs, s, s + len(raw), self.cur, raw)
        self.cur.children.append(n)
        if tag in VOID: n.inner_end = n.end = n.inner_start
        else: self.cur = n

    def handle_startendtag(self, tag, attrs):
        s = self.off(); raw = self.get_starttag_text()
        n = Node(tag, attrs, s, s + len(raw), self.cur, raw); n.inner_end = n.end = n.inner_start
        self.cur.children.append(n)

    def handle_endtag(self, tag):
        s = self.off()
        m = re.compile(r"</\s*%s\s*>" % re.escape(tag), re.I).match(self.src, s)
        e = m.end() if m else s
        node = self.cur
        while node is not self.root and node.tag != tag: node = node.parent
        if node is self.root: return                      # stray end tag
        while self.cur is not node:                        # implicitly closed elements
            self.cur.inner_end = self.cur.end = s; self.cur = self.cur.parent
        node.inner_end, node.end = s, e
        self.cur = node.parent

    def _text(self, length):
        s = self.off(); self.cur.children.append(Text(s, s + length, self.cur))
    def handle_data(self, d): self._text(len(d))
    def handle_entityref(self, n): self._text(len(n) + 2)
    def handle_charref(self, n): self._text(len(n) + 3)
    def handle_comment(self, d): pass

def is_inline_pure(n):
    """An inline element whose whole content is text/inline (no opaque or block inside)."""
    if isinstance(n, Text): return True
    if n.tag not in INLINE or NO_TRANSLATE in n.attrs: return False
    return all(is_inline_pure(c) for c in n.children)

def segments(src):
    """Yield (start, end, text, kind) for every translatable piece of the page."""
    tree = Tree(src); out = []

    def flush(run):
        if not run: return
        # side-by-side elements with no text between them (card fields, label + value) are separate strings
        meaningful = [c for c in run if not (isinstance(c, Text) and not src[c.start:c.end].strip())]
        if len(meaningful) > 1 and all(isinstance(c, Node) for c in meaningful):
            for c in meaningful: flush([c])
            return
        s, e = run[0].start, run[-1].end
        # trim surrounding whitespace
        while s < e and src[s].isspace(): s += 1
        while e > s and src[e - 1].isspace(): e -= 1
        # a run that is exactly one inline element: descend into it
        while True:
            el = [c for c in run if not (isinstance(c, Text) and not src[c.start:c.end].strip())]
            if len(el) == 1 and isinstance(el[0], Node) and el[0].start == s and el[0].end == e and el[0].children:
                run = el[0].children; s, e = run[0].start, run[-1].end
                while s < e and src[s].isspace(): s += 1
                while e > s and src[e - 1].isspace(): e -= 1
            else: break
        text = src[s:e]
        if text and has_words(text): out.append((s, e, text, "text"))

    def walk(n):
        if isinstance(n, Text) or n.tag in OPAQUE or NO_TRANSLATE in n.attrs: return
        run = []
        for c in n.children:
            if is_inline_pure(c): run.append(c)
            else:
                flush(run); run = []
                walk(c)
        flush(run)

    def attrs(n):
        if isinstance(n, Text): return
        if n.tag not in ("script", "style") and NO_TRANSLATE not in n.attrs:
            names = list(ATTRS)
            if n.tag == "meta" and (n.attrs.get("name") in META_NAMES or n.attrs.get("property") in META_PROPS):
                names.append("content")
            for a in names:
                if a in n.attrs and n.attrs[a]:
                    m = re.search(r'\s%s\s*=\s*(["\'])(.*?)\1' % re.escape(a), n.raw_start_tag, re.S | re.I)
                    if m and has_words(m.group(2)):
                        s = n.start + m.start(2); out.append((s, s + len(m.group(2)), m.group(2), "attr:" + a))
        for c in n.children: attrs(c)

    walk(tree.root); attrs(tree.root)
    out.sort(key=lambda x: x[0])
    # drop overlaps (an attribute inside a text segment is translated with that segment's markup intact)
    clean, last = [], -1
    for seg in out:
        if seg[0] >= last: clean.append(seg); last = seg[1]
    return clean

def page_path(p): return os.path.join(ROOT, BASE, p)
def read(p): return open(p, encoding="utf-8").read()

def cmd_extract():
    cat = {}
    for p in PAGES:
        for s, e, text, kind in segments(read(page_path(p))):
            k = key_of(text)
            ent = cat.setdefault(k, {"en": text, "kind": kind, "pages": []})
            if p not in ent["pages"]: ent["pages"].append(p)
    os.makedirs(os.path.dirname(CATALOG), exist_ok=True)
    json.dump(dict(sorted(cat.items(), key=lambda kv: (kv[1]["pages"][0], kv[0]))), open(CATALOG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    words = sum(len(re.sub(r"<[^>]+>", " ", v["en"]).split()) for v in cat.values())
    print(f"catalog: {len(cat)} unique strings, ~{words} words, from {len(PAGES)} pages -> {os.path.relpath(CATALOG, ROOT)}")

def load_tr(lang):
    f = os.path.join(TRDIR, f"{lang}.json")
    return json.load(open(f, encoding="utf-8")) if os.path.exists(f) else {}

def cmd_status():
    cat = json.load(open(CATALOG, encoding="utf-8"))
    langs = CFG["languages"] or ["(none yet)"]
    for lang in CFG["languages"]:
        tr = load_tr(lang)
        done = [k for k in cat if k in tr]
        rev = [k for k in done if tr[k].get("status") == "reviewed"]
        unused = [k for k in tr if k not in cat]
        print(f"{lang}: {len(done)}/{len(cat)} translated ({len(rev)} reviewed), {len(cat)-len(done)} missing, {len(unused)} old entries no longer used")
    if not CFG["languages"]: print("No languages configured; English only. Catalog has", len(cat), "strings.")

def localize_links(src, lang):
    # /commandhq/<page>  ->  /commandhq/<lang>/<page>  for pages we translate; assets stay where they are
    pages = {"/%s/%s" % (BASE, p.replace("index.html", "")) for p in PAGES}
    def rep(m):
        url = m.group(2); path = url.split("#")[0].split("?")[0]
        if path in pages:
            return m.group(1) + "/%s/%s/%s" % (BASE, lang, url[len(BASE) + 2:]) + m.group(3)
        return m.group(0)
    return re.sub(r'(href=")(/%s/[^"]*)(")' % BASE, rep, src)

def alternates_block(page):
    rel = page.replace("index.html", "")
    lines = ['<link rel="alternate" hreflang="en" href="%s/%s/%s">' % (CFG["origin"], BASE, rel)]
    for l in CFG["languages"]:
        lines.append('<link rel="alternate" hreflang="%s" href="%s/%s/%s/%s">' % (l, CFG["origin"], BASE, l, rel))
    lines.append('<link rel="alternate" hreflang="x-default" href="%s/%s/%s">' % (CFG["origin"], BASE, rel))
    return "\n  ".join(lines)

def switcher_block(page, current):
    rel = page.replace("index.html", "")
    items = [("en", "English", "/%s/%s" % (BASE, rel))] + [(l, CFG["language_names"].get(l, l), "/%s/%s/%s" % (BASE, l, rel)) for l in CFG["languages"]]
    links = " · ".join(('<strong lang="%s">%s</strong>' if c == current else '<a href="%s" hreflang="%s" lang="%s">%s</a>') %
                       ((c, n) if c == current else (u, c, c, n)) for c, n, u in items)
    return '<p class="lang-switch">%s</p>' % links

def set_block(src, name, content):
    return re.sub(r"(<!-- i18n:%s -->).*?(<!-- /i18n:%s -->)" % (name, name), lambda m: m.group(1) + content + m.group(2), src, flags=re.S)

def render(src, page, lang, lookup):
    """Replace segments (from the end so offsets stay valid)."""
    out = src
    for s, e, text, kind in reversed(segments(src)):
        t = lookup(text)
        if t is None or t == text: continue
        if kind.startswith("attr:"): t = t.replace('"', "&quot;")
        out = out[:s] + t + out[e:]
    out = re.sub(r'<html lang="[^"]*"', '<html lang="%s"' % lang, out, count=1)
    out = localize_links(out, lang)
    return out

def cmd_build(pseudo=False):
    langs = ["xx"] if pseudo else CFG["languages"]
    multi = bool(CFG["languages"])
    # English pages: only the marked blocks change (empty when there are no other languages)
    for p in PAGES:
        f = page_path(p); src = read(f)
        new = set_block(src, "alternates", ("\n  " + alternates_block(p) + "\n  ") if multi else "")
        new = set_block(new, "switcher", switcher_block(p, "en") if multi else "")
        if new != src: open(f, "w", encoding="utf-8").write(new); print("updated", os.path.relpath(f, ROOT))
    for lang in langs:
        tr = {} if pseudo else load_tr(lang)
        def lookup(text, tr=tr):
            if pseudo: return "⟦" + text + "⟧"
            ent = tr.get(key_of(text)); return ent["text"] if ent and ent.get("src") == text else None
        missing = 0
        for p in PAGES:
            src = read(page_path(p))
            out = render(src, p, lang, lookup)
            if not pseudo:
                out = set_block(out, "alternates", "\n  " + alternates_block(p) + "\n  ")
                out = set_block(out, "switcher", switcher_block(p, lang))
                missing += sum(1 for _, _, t, _ in segments(src) if lookup(t) is None)
            dst = os.path.join(ROOT, BASE, lang, p)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, "w", encoding="utf-8").write(out)
        print(f"built /{BASE}/{lang}/ ({len(PAGES)} pages)" + ("" if pseudo else f", {missing} strings still in English"))

def cmd_check():
    bad = 0
    for p in PAGES:
        src = read(page_path(p))
        out = src
        for s, e, text, kind in reversed(segments(src)): out = out[:s] + text + out[e:]
        if out != src: bad += 1; print("MISMATCH", p)
        segs = segments(src)
        print(f"{p}: {len(segs)} segments")
    print("self-test:", "OK" if not bad else f"{bad} pages differ")

def cmd_translate(lang):
    """Machine-translate missing / out-of-date strings with Claude. Never overwrites status=reviewed."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key: sys.exit("Set ANTHROPIC_API_KEY first (export ANTHROPIC_API_KEY=...).")
    cat = json.load(open(CATALOG, encoding="utf-8")); tr = load_tr(lang)
    todo = [(k, v["en"]) for k, v in cat.items() if not (k in tr and tr[k].get("src") == v["en"])]
    todo = [(k, s) for k, s in todo if not (k in tr and tr[k].get("status") == "reviewed")]
    if not todo: print(f"{lang}: nothing to translate"); return
    name = CFG["language_names"].get(lang, lang)
    gloss = CFG.get("glossary", {})
    system = (f"You translate the marketing website of CommandHQ, a native Apple project-management app, from English into {name} ({lang}). "
              "Write like a professional native copywriter for this market: natural, concise, confident, never literal or stiff. "
              "Rules: keep every HTML tag, attribute and entity exactly as given (translate only human-readable text); "
              "keep product and platform names in English (CommandHQ, Krida LLC, iPhone, iPad, Mac, Apple Watch, iCloud, App Store, Apple Intelligence, Ollama, Anthropic, OpenAI, Gantt, Kanban); "
              "keep numbers, prices, dates and units correct for the locale; use the formal or informal address that Apple uses for this language; "
              f"glossary (English -> {name}): {json.dumps(gloss.get(lang, {}), ensure_ascii=False)}. "
              "Answer with a JSON object mapping each id to its translation, nothing else.")
    batch = 40
    for i in range(0, len(todo), batch):
        chunk = dict(todo[i:i + batch])
        body = {"model": CFG.get("model", "claude-sonnet-5-5"), "max_tokens": 8000, "system": system,
                "messages": [{"role": "user", "content": json.dumps(chunk, ensure_ascii=False)}]}
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                     headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        resp = json.load(urllib.request.urlopen(req, timeout=300))
        txt = "".join(b.get("text", "") for b in resp.get("content", []))
        txt = txt[txt.find("{"): txt.rfind("}") + 1]
        got = json.loads(txt)
        for k, en in chunk.items():
            if k in got and isinstance(got[k], str):
                tr[k] = {"text": got[k], "src": en, "status": "machine"}
        os.makedirs(TRDIR, exist_ok=True)
        json.dump(tr, open(os.path.join(TRDIR, f"{lang}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"{lang}: {min(i + batch, len(todo))}/{len(todo)}")
    print("Done. Review important strings and set their status to \"reviewed\".")

if __name__ == "__main__":
    a = sys.argv[1:] or ["help"]
    if a[0] == "extract": cmd_extract()
    elif a[0] == "status": cmd_status()
    elif a[0] == "build": cmd_build()
    elif a[0] == "pseudo": cmd_build(pseudo=True)
    elif a[0] == "check": cmd_check()
    elif a[0] == "translate" and len(a) > 1: cmd_translate(a[1])
    else: print(__doc__)
