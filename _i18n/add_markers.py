import re,sys,os
root=sys.argv[1]
pages=["index.html","features/index.html","pricing/index.html","support/index.html","videos/index.html","privacy/index.html","terms/index.html","press/index.html"]
for p in pages:
    f=os.path.join(root,"commandhq",p); s=open(f,encoding="utf-8").read()
    if "<!-- i18n:alternates -->" not in s:
        s=s.replace("</head>","  <!-- i18n:alternates --><!-- /i18n:alternates -->\n</head>",1)
    if "<!-- i18n:switcher -->" not in s:
        i=s.rfind("</footer>")
        assert i>0, p
        s=s[:i]+"<!-- i18n:switcher --><!-- /i18n:switcher -->\n"+s[i:]
    if p=="index.html":
        s=s.replace('srcset="media/f/','srcset="/commandhq/media/f/').replace('src="media/f/','src="/commandhq/media/f/')
    open(f,"w",encoding="utf-8").write(s); print("ok",p)
