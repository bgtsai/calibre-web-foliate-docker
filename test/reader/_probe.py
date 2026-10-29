import sys, json
exec(open('ft180.py').read().split("with sync_playwright() as p:")[0])
seed = json.loads(sys.argv[4])
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 1100, 'height': 800})
    pg = ctx.new_page(); pg.add_init_script("localStorage.setItem('cwfm-settings', %s)" % json.dumps(json.dumps(seed)))
    pg.goto(URL); pg.mouse.move(550, 400)
    t = 0; first = None
    while t < 14000:
        pg.wait_for_timeout(250); t += 250
        if pg.evaluate("document.documentElement.classList.contains('cwfm-bars-hidden')"): first = t; break
    print('hidden at', first, 'ms', pg.evaluate("window.__cwfm.settings.autoHideToolbar"))
    b.close()
