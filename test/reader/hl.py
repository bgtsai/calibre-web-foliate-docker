"""v1.79 功能測試：閱讀進度、預覽網址、書籤、搜尋、匯出、跳轉紀錄保存、CSRF 重試。
用法：python3 ft179.py <patched read.html> <reader.js> <browser>
"""
import http.server, io, json, os, sys, threading, zipfile, re, urllib.parse
import jinja2
from playwright.sync_api import sync_playwright

TPL, JS, BROWSER = sys.argv[1], sys.argv[2], sys.argv[3]
BOOK_ID = 9252
CSP = ("default-src 'self' 'unsafe-inline' 'unsafe-eval'; font-src 'self' data: blob: ; "
       "img-src 'self' data: blob: ; style-src-elem 'self' blob: 'unsafe-inline'; object-src 'none';")


def make_epub():
    buf = io.BytesIO()
    z = zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED)
    z.writestr(zipfile.ZipInfo('mimetype'), 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
    z.writestr('META-INF/container.xml', '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/c.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
    z.writestr('OEBPS/c.opf', '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="id">cwfm-test</dc:identifier><dc:title>測試書名</dc:title><dc:creator>某作者</dc:creator><dc:language>zh-TW</dc:language><meta property="dcterms:modified">2026-10-07T00:00:00Z</meta></metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="c1" href="c1.xhtml" media-type="application/xhtml+xml"/><item id="c2" href="c2.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="c1"/><itemref idref="c2"/></spine></package>')
    z.writestr('OEBPS/nav.xhtml', '<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><body><nav epub:type="toc"><ol><li><a href="c1.xhtml">第一章</a></li><li><a href="c2.xhtml">第二章</a></li></ol></nav></body></html>')
    for i in (1, 2):
        paras = ''.join(f'<p>第{i}章第{n}段：天地玄黃，宇宙洪荒。日月盈昃，辰宿列張。{"門前有ＡＢＣ。" if n % 17 == 0 else ""}</p>' for n in range(1, 120))
        z.writestr(f'OEBPS/c{i}.xhtml', f'<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"><head><title>c{i}</title></head><body><h1>第{i}章</h1>{paras}</body></html>')
    z.close()
    return buf.getvalue()


EPUB = make_epub()
JSB = open(JS, 'rb').read()
TPLSRC = open(TPL, encoding='utf-8').read()
env = jinja2.Environment(extensions=['jinja2.ext.i18n'])
env.install_null_translations()
STATE = {'bookmark': None, 'bookmarks': {}, 'navhist': None, 'fail400': 0, 'csrf': 'tok-1'}
hits = []


def render():
    return env.from_string(TPLSRC).render(
        url_for=lambda ep, **kw: '/static/' + kw['filename'] if ep == 'static' else '/cwfm/api/' if ep == 'cwfm_api.base' else '/' + ep,
        csrf_token=lambda: STATE['csrf'], g=type('G', (), {'google_site_verification': ''})(),
        title='測試書名', bookid=BOOK_ID, book_format='epub', bookmark=(type('B', (), {'bookmark_key': STATE['bookmark']})() if STATE['bookmark'] else None),
        current_user=type('U', (), {'is_authenticated': True})()).encode('utf-8')


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def send(self, code, body=b'', ctype='text/plain'):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Security-Policy', CSP)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def body(self):
        return self.rfile.read(int(self.headers.get('Content-Length', 0))).decode('utf-8')

    def do_GET(self):
        p = self.path.split('?')[0]
        hits.append(('GET', self.path))
        if p == f'/read/{BOOK_ID}/epub': self.send(200, render(), 'text/html; charset=utf-8')
        elif p == '/static/js/cwfm/cwfm-reader.js': self.send(200, JSB, 'text/javascript')
        elif p == f'/show/{BOOK_ID}/epub/file.epub': self.send(200, EPUB, 'application/epub+zip')
        elif p == f'/cwfm/api/book/{BOOK_ID}':
            self.send(200, json.dumps({'bookmarks': list(STATE['bookmarks'].values()), 'navhist': STATE['navhist']}).encode(), 'application/json')
        else: self.send(404, b'not found')

    def do_PUT(self):
        b = self.body()
        hits.append(('PUT', self.path, self.headers.get('X-CSRFToken')))
        m = re.match(rf'/cwfm/api/book/{BOOK_ID}/bookmark/([\w-]+)$', self.path)
        if m: STATE['bookmarks'][m.group(1)] = json.loads(b)
        elif self.path == f'/cwfm/api/book/{BOOK_ID}/navhist': STATE['navhist'] = json.loads(b)
        self.send(200, b'{"ok":true}', 'application/json')

    def do_DELETE(self):
        hits.append(('DELETE', self.path))
        m = re.match(rf'/cwfm/api/book/{BOOK_ID}/bookmark/([\w-]+)$', self.path)
        if m: STATE['bookmarks'].pop(m.group(1), None)
        self.send(200, b'{"ok":true}', 'application/json')

    def do_POST(self):
        b = self.body()
        tok = self.headers.get('X-CSRFToken')
        hits.append(('POST', self.path, tok))
        if self.path == f'/ajax/bookmark/{BOOK_ID}/epub':
            if STATE['fail400'] and tok != STATE['csrf']:
                STATE['fail400'] -= 1
                self.send(400, b'<h1>400 Bad Request</h1>', 'text/html'); return
            STATE['bookmark'] = urllib.parse.parse_qs(b).get('bookmark', [''])[0] or None
        self.send(200, b'')


srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f'http://127.0.0.1:{srv.server_address[1]}'
URL = f'{BASE}/read/{BOOK_ID}/epub'
results = []


def check(name, ok, info=''):
    results.append(bool(ok))
    print(("OK  " if ok else "FAIL") + ' ' + name + (' ' + str(info) if info else ''))


FIRST = "(()=>{const r=document.querySelector('foliate-view').renderer;const v=r.getVisibleRange();return v?v.toString().replace(/\\s/g,'').slice(0,12):''})()"
VIEW = "document.querySelector('foliate-view')"


with sync_playwright() as p:
    b = getattr(p, BROWSER).launch()
    ctx = b.new_context(viewport={'width': 1100, 'height': 780})
    pg = ctx.new_page()
    pg.add_init_script("localStorage.setItem('cwfm-settings', %s)" % json.dumps(json.dumps({'flow': 'paginated', 'maxColumnCount': 1})))
    pg.goto(URL); pg.wait_for_timeout(3500)
    for i in range(3): pg.evaluate(f"{VIEW}.renderer.next()"); pg.wait_for_timeout(400)
    pg.set_viewport_size({'width': 1000, 'height': 760}); pg.wait_for_timeout(1500)
    pg.evaluate(f"""(()=>{{const c={VIEW}.renderer.getContents()[0];const d=c.doc;const ps=[...d.querySelectorAll('p')];const vis=ps.filter(e=>{{const r=e.getBoundingClientRect();return r.left>=0&&r.left<d.defaultView.innerWidth}});const p=vis[3];
      const tn=p.firstChild;const r=d.createRange();r.setStart(tn,5);r.setEnd(tn,20);const s=d.getSelection();s.removeAllRanges();s.addRange(r);d.dispatchEvent(new Event('selectionchange'));}})()""")
    pg.wait_for_timeout(200)
    pg.click('button[aria-label="加入書籤"], button[aria-label="Add bookmark"]'); pg.wait_for_timeout(300)
    pg.fill('.cwfm-bm-dialog textarea', 'n'); pg.click('.cwfm-bm-dialog .cwfm-ok-primary'); pg.wait_for_timeout(800)
    pg.evaluate(f"{VIEW}.goTo(1)"); pg.wait_for_timeout(800)
    pg.set_viewport_size({'width': 1100, 'height': 780}); pg.wait_for_timeout(1500)
    pg.click('button[aria-label="目錄"], button[aria-label="Table of Contents"]', force=True); pg.wait_for_timeout(400)
    pg.click('.cwfm-bm-row[data-type="note"] .cwfm-bm-name'); pg.wait_for_timeout(2000)
    print('HL', pg.evaluate(f"""(()=>{{const v={VIEW};const c=v.renderer.getContents()[0];const g=c.overlayer.element.querySelector('g rect');
      const bm=JSON.parse(localStorage.getItem('cwfm-bookdata-9252')).bookmarks.find(b=>b.note);
      const r=v.resolveCFI(bm.cfi).anchor(c.doc).getClientRects()[0];return g?[Math.round(+g.getAttribute('x')),Math.round(+g.getAttribute('y')),Math.round(r.left),Math.round(r.top)]:null}})()"""))
    b.close()
