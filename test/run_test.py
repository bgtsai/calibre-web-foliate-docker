"""無頭瀏覽器冒煙測試：模擬 Calibre-Web 的 read_book 頁面（含相同 CSP），
載入 patch 後的 read.html + cwfm-reader.js，確認書能打開、沒有錯誤。
用法：python3 run_test.py <patched read.html> <cwfm-reader.js> <browser>
"""
import http.server, io, json, os, sys, threading, zipfile
import jinja2
from playwright.sync_api import sync_playwright

TPL, JS, BROWSER = sys.argv[1], sys.argv[2], sys.argv[3]
BOOK_ID = 9252
CSP = ("default-src 'self' 'unsafe-inline' 'unsafe-eval'; font-src 'self' data: blob: ; "
       "img-src 'self' data: blob: ; style-src-elem 'self' blob: 'unsafe-inline'; object-src 'none';")


def make_epub():
    buf = io.BytesIO()
    z = zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED)  # 實際 EPUB 內文是壓縮的，要測到解壓縮路徑
    z.writestr(zipfile.ZipInfo('mimetype'), 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
    z.writestr('META-INF/container.xml', '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/c.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
    z.writestr('OEBPS/c.opf', '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="id">cwfm-test</dc:identifier><dc:title>測試書名</dc:title><dc:language>zh-TW</dc:language><meta property="dcterms:modified">2026-10-07T00:00:00Z</meta></metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="c1" href="c1.xhtml" media-type="application/xhtml+xml"/><item id="c2" href="c2.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="c1"/><itemref idref="c2"/></spine></package>')
    z.writestr('OEBPS/nav.xhtml', '<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><body><nav epub:type="toc"><ol><li><a href="c1.xhtml">第一章</a></li><li><a href="c2.xhtml">第二章</a></li></ol></nav></body></html>')
    for i in (1, 2):
        paras = ''.join(f'<p>第{i}章第{n}段：天地玄黃，宇宙洪荒。日月盈昃，辰宿列張。</p>' for n in range(1, 120))
        z.writestr(f'OEBPS/c{i}.xhtml', f'<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"><head><title>c{i}</title></head><body><h1>第{i}章</h1>{paras}</body></html>')
    z.close()
    return buf.getvalue()


env = jinja2.Environment(extensions=['jinja2.ext.i18n'])
env.install_null_translations()
html = env.from_string(open(TPL, encoding='utf-8').read()).render(
    url_for=lambda ep, **kw: '/static/' + kw['filename'] if ep == 'static' else '/' + ep,
    csrf_token=lambda: 'test-csrf', g=type('G', (), {'google_site_verification': ''})(),
    title='測試書名', bookid=BOOK_ID, book_format='epub', bookmark=None,
    current_user=type('U', (), {'is_authenticated': True})()).encode('utf-8')
EPUB = make_epub()
JSB = open(JS, 'rb').read()
hits = []


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def send(self, code, body=b'', ctype='text/plain'):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Security-Policy', CSP)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        p = self.path.split('?')[0]
        hits.append(('GET', self.path))
        if p == f'/read/{BOOK_ID}/epub': self.send(200, html, 'text/html; charset=utf-8')
        elif p == '/static/js/cwfm/cwfm-reader.js': self.send(200, JSB, 'text/javascript')
        elif p == f'/show/{BOOK_ID}/epub/file.epub': self.send(200, EPUB, 'application/epub+zip')
        else: self.send(404, b'not found')

    def do_POST(self):
        hits.append(('POST', self.path))
        self.rfile.read(int(self.headers.get('Content-Length', 0)))
        self.send(200, b'')


srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{srv.server_address[1]}/read/{BOOK_ID}/epub'

with sync_playwright() as p:
    b = getattr(p, BROWSER).launch()
    ctx = b.new_context(viewport={'width': 1200, 'height': 800})
    page = ctx.new_page()
    import os
    if os.environ.get('FS_TEST'):
        # 模擬 iPadOS 15：只有 webkit 前綴的全螢幕 API
        page.add_init_script('''delete Element.prototype.requestFullscreen; delete Document.prototype.exitFullscreen;
          delete Document.prototype.fullscreenElement; delete Document.prototype.fullscreenEnabled;
          window.__fsEvents = 0; document.addEventListener('fullscreenchange', () => window.__fsEvents++);''')
    if os.environ.get('DELETE_APIS'):
        # 模擬 iOS 15.3：把舊 Safari 沒有的內建函式刪掉，確認代用品有補上
        page.add_init_script('''for (const [o,k] of [[Array.prototype,'at'],[String.prototype,'at'],[Object.getPrototypeOf(Int8Array.prototype),'at'],
          [Array.prototype,'findLast'],[Array.prototype,'findLastIndex'],[Object,'hasOwn'],[Object,'groupBy'],[Map,'groupBy'],
          [Promise,'withResolvers'],[Promise,'try'],[URL,'parse'],[Map.prototype,'getOrInsertComputed'],[window,'DecompressionStream'],[window,'CompressionStream']]) { try { delete o[k]; } catch(e){} }
          window.__deleted = typeof [].at + typeof Object.groupBy;''')
    logs = []
    page.on('console', lambda m: logs.append(f'{m.type}: {m.text}'[:200]))
    page.on('pageerror', lambda e: logs.append(f'PAGEERROR: {e}'[:300]))
    if os.environ.get('NAV_TEST'):
        page.add_init_script('''localStorage.setItem('cwfm-settings', JSON.stringify({cursorAutoHideEnabled:true,cursorAutoHideDelaySeconds:1,themeName:'old_gold'}));''')
    page.goto(url)
    page.wait_for_timeout(int(__import__("os").environ.get("WAIT","6000")))
    if os.environ.get('FS_TEST'):
        before = page.evaluate("[typeof Element.prototype.webkitRequestFullscreen, !!document.webkitFullscreenElement]")
        page.click('button[aria-label="全螢幕"], button[aria-label="Fullscreen"]', force=True)
        page.wait_for_timeout(1500)
        r_fs = page.evaluate("({webkitFS: !!document.webkitFullscreenElement, std: !!document.fullscreenElement, events: window.__fsEvents})")
        print('FS', before, json.dumps(r_fs))
    r = page.evaluate('''() => {
        const v = document.querySelector('foliate-view');
        const out = {view: !!v, title: v && v.book && v.book.metadata && v.book.metadata.title,
                     sections: v && v.book && v.book.sections.length,
                     boot: window.__cwfmBoot && window.__cwfmBoot.bookId,
                     ls: Object.keys(localStorage), deleted: window.__deleted,
                     badge: ([...document.querySelectorAll('button')].find(b=>/^⚠/.test(b.textContent))||{}).textContent || null,
                     panel: ((document.querySelector('pre')||{}).textContent||'').split('\\n\\n').slice(1).join(' || ').slice(0,600)};
        try { out.text = v.renderer.getContents()[0].doc.body.innerText.slice(0, 30); } catch (e) { out.text = 'ERR ' + e.message; }
        return out; }''')
    if os.environ.get('COLOR_TEST'):
        q = lambda: page.evaluate("(()=>{const s=window.__cwfm.settings;const d=document.querySelector('foliate-view').renderer.getContents()[0].doc;return [s.activeColorTheme,s.customTextColor,s.customBackgroundColor,s.customTextColorEnabled,document.documentElement.dataset.cwfmScheme,getComputedStyle(d.body).backgroundColor]})()")
        r_c = {'init': q()}
        page.emulate_media(color_scheme='dark'); page.wait_for_timeout(500); r_c['sysdark'] = q()
        page.evaluate("(()=>{const s=window.__cwfm.settings;s.customBackgroundColorEnabled=false;})()")
        print('COLOR', json.dumps(r_c))
    if os.environ.get('NAV_TEST'):
        page.mouse.move(600,400); page.wait_for_timeout(1800)
        st = "(()=>{const v=document.querySelector('foliate-view');const cs=v.renderer.getContents().map(c=>c.index+':'+(c.doc.getElementById('cwfm-cursor-autohide-style')||{}).textContent+':'+getComputedStyle(c.doc.body).backgroundColor);return [document.documentElement.dataset.cwfmScheme,cs, (document.getElementById('cwfm-cursor-autohide-style')||{}).textContent]})()"
        print('NAV before', page.evaluate(st))
        page.evaluate("document.querySelector('foliate-view').goTo(1)"); page.wait_for_timeout(50); print('NAV 50ms', page.evaluate(st))
        page.wait_for_timeout(1500); print('NAV after', page.evaluate(st))
    if os.environ.get('SAFE_AFTER'):
        # 模擬當掉：直接關掉分頁（不跑任何收尾），再用安全模式開同一頁看上一次紀錄
        page.close()
        n0 = len(hits)
        sp = ctx.new_page()
        sp.goto(url + '?cwfm=safe'); sp.wait_for_timeout(2500)
        r['safe_text'] = sp.evaluate("(document.querySelector('pre')||{}).textContent||''")[:1500]
        r['safe_requests'] = [h[1] for h in hits[n0:] if 'cwfm' in h[1] or '/show/' in h[1]]
        sp.screenshot(path=os.environ.get('OUT','.')+'/safe.png')
        page = sp
    page.screenshot(path=os.environ.get('OUT', '.') + f'/shot_{BROWSER}.png')
    b.close()

print('RESULT', json.dumps(r, ensure_ascii=False))
print('REQUESTS', [h for h in hits if not h[1].startswith('/static/css')])
errs = [l for l in logs if l.startswith(('error', 'PAGEERROR'))]
print('ERRORS', len(errs)); [print('  ', l) for l in errs[:15]]
