# CommandHQ website translations

The English pages under `/commandhq/` stay the source of truth. Keep editing them exactly as now. This folder turns them into translated copies at `/commandhq/<lang>/` when, and only when, languages are switched on.

## Every day (English only, now)

You don't need to do anything. With `"languages": []` in `config.json`, the English site is untouched.

Optionally, after copy changes, run:

```
python3 _i18n/i18n.py extract     # refresh catalog/en.json (all English strings)
python3 _i18n/i18n.py check       # self-test: must say OK
```

## Adding a language (after launch)

1. Add the code to `config.json`, e.g. `"languages": ["de"]`. The codes match the app: de, fr, es, it, nl, pl, pt-BR, ja, ko, zh-Hans, zh-Hant.
2. Run:
   ```
   python3 _i18n/i18n.py extract
   export ANTHROPIC_API_KEY=…                 # a website-only key
   python3 _i18n/i18n.py translate de         # only new or changed strings are sent
   python3 _i18n/i18n.py build                # writes /commandhq/de/…, adds hreflang + language switcher
   python3 _i18n/i18n.py status
   ```
3. Have a native speaker check the strings that matter most: the headline, hero, pricing and CTA. Set those entries in `translations/de.json` to `"status": "reviewed"`; `translate` never overwrites reviewed strings.
4. Commit `_i18n/` and `commandhq/de/`, then push.

## When the English changes later

Run `extract → translate <lang> → build` for each language. Each string's key is a hash of its English text, so changed sentences are re-translated automatically and unchanged ones are kept. Until a string is translated, it shows in English; the build never breaks.

## Checking coverage

`python3 _i18n/i18n.py pseudo` builds a preview at `/commandhq/xx/` where every translatable string is wrapped in ⟦…⟧. Anything you see without brackets won't be translated. `xx/` is git-ignored; don't publish it.

Put `data-no-i18n` on any element that must never be translated (a code sample, a keyboard shortcut).

## What it does on the pages

- Two markers per page:
  - `<!-- i18n:alternates -->` in `<head>`: hreflang links for search engines
  - `<!-- i18n:switcher -->` before `</footer>`: a language switcher
  Both stay empty while the site is English-only.
- Translated pages get `<html lang>` set, and their internal page links point to the same language. Images, CSS and JS stay shared.

## Known limits (to handle when a language is switched on)

- **Videos page:** its list is built in JavaScript from `videos/catalog.json`. Titles and summaries need a per-language catalog (Xcode can export one from the app's own localized strings), and the page needs to load it.
- **FAQ structured data:** the JSON-LD for search results stays in English on translated pages. Regenerate it from the translated FAQ when Support is translated.
- **Legal pages:** Terms and Privacy should carry a "convenience translation; the English version governs" note.
- **Screenshots:** translated pages use the English screenshots until localized ones exist. Xcode's lineup tests already run in every language.
- **Wording that must be rewritten, not translated:** the headline "Which of your deadlines are likely to slip?" needs a native copywriter for each market.
