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
    ctx = b.new_context(viewport={'width': 768, 'height': 1000}, locale='zh-TW', has_touch=True)
    errs = []

    def newpage(url, settings=None):
        pg = ctx.new_page()
        pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
        pg.on('console', lambda m: errs.append(m.text[:200]) if m.type == 'error' and 'lock initial anchor' not in m.text and '404' not in m.text else None)
        if settings is not None:
            pg.add_init_script("localStorage.setItem('cwfm-settings', %s)" % json.dumps(json.dumps(settings)))
        pg.goto(url)
        pg.wait_for_timeout(3500)
        pg.mouse.move(550, 400)
        return pg

    # 1. 開書、翻頁 → 閱讀進度立刻同步
    pg = newpage(URL, {'flow': 'paginated', 'maxColumnCount': 1})
    n0 = len([h for h in hits if h[0] == 'POST'])
    pg.evaluate(f"{VIEW}.renderer.next()"); pg.wait_for_timeout(500)
    pg.evaluate(f"{VIEW}.renderer.next()"); pg.wait_for_timeout(800)
    posts = [h for h in hits if h[0] == 'POST'][n0:]
    check('翻頁即時同步', len(posts) >= 1 and STATE['bookmark'] is not None, len(posts))
    synced = STATE['bookmark']
    first_a = pg.evaluate(FIRST)

    # 2. CSRF：token 失效 → 400 → 重取 token → 重送成功
    STATE['csrf'] = 'tok-2'; STATE['fail400'] = 1
    pg.evaluate(f"{VIEW}.renderer.next()"); pg.wait_for_timeout(1500)
    retried = [h for h in hits if h[0] == 'POST' and 'errlog' not in h[1]][-1]
    check('CSRF 400 自動重試', retried[2] == 'tok-2' and STATE['fail400'] == 0, retried)
    first_after = pg.evaluate(FIRST)
    synced2 = STATE['bookmark']

    # 3. 加書籤（沒選取）＝定位
    pg.click('button[aria-label="加入書籤"], button[aria-label="Add bookmark"]'); pg.wait_for_timeout(300)
    dlg = pg.locator('.cwfm-bm-dialog')
    check('書籤視窗出現', dlg.count() == 1)
    pg.click('.cwfm-bm-dialog .cwfm-ok-primary'); pg.wait_for_timeout(600)
    bms = list(STATE['bookmarks'].values())
    pg.wait_for_timeout(300)
    check('這頁有書籤→工具列書籤鈕變紅', pg.evaluate("document.querySelector('.cwfm-toolbar-top button[data-filled]')?.dataset.filled") == 'true')
    check('定位書籤存到伺服器', len(bms) == 1 and not bms[0].get('excerpt'), bms[:1])
    pos_bm = bms[0] if bms else {}

    # 4. 選取文字加書籤＋備註＝備註（附摘錄），內文有標示
    pg.evaluate(f"""(()=>{{const c={VIEW}.renderer.getContents()[0];const d=c.doc;const p=[...d.querySelectorAll('p')].find(e=>{{const r=e.getBoundingClientRect();return r.left>=0&&r.top>0&&r.left<d.defaultView.innerWidth}})||d.querySelector('p');
      const tn=p.firstChild;const r=d.createRange();r.setStart(tn,2);r.setEnd(tn,9);const s=d.getSelection();s.removeAllRanges();s.addRange(r);d.dispatchEvent(new Event('selectionchange'));}})()""")
    pg.wait_for_timeout(200)
    pg.keyboard.press('Control+m'); pg.wait_for_timeout(400)
    ex = pg.evaluate("(document.querySelector('.cwfm-bm-dexcerpt')||{}).textContent||''")
    pg.fill('.cwfm-bm-dialog textarea', '這是 $& 備註')
    pg.click('.cwfm-bm-dialog .cwfm-ok-primary'); pg.wait_for_timeout(800)
    note_bm = [x for x in STATE['bookmarks'].values() if x.get('note')]
    check('摘錄＋備註書籤', len(note_bm) == 1 and note_bm[0].get('excerpt'), (ex, note_bm[:1]))
    hl = pg.evaluate(f"(()=>{{const c={VIEW}.renderer.getContents()[0];return c.overlayer?c.overlayer.element.childElementCount:-1}})()")
    check('內文標示', hl >= 1, hl)

    # 5. 目錄混排、篩選、展開、點擊跳轉
    pg.click('button[aria-label="目錄"], button[aria-label="Table of Contents"]', force=True); pg.wait_for_timeout(400)
    rows = pg.evaluate("[...document.querySelectorAll('.cwfm-bm-row')].map(r=>r.dataset.type)")
    check('進度條沒有 ↩ ↪', pg.evaluate("!document.querySelector('.cwfm-toolbar .cwfm-nav-group')"))
    check('備註＋摘錄旗頭右側琥珀條', pg.evaluate("getComputedStyle(document.querySelector('.cwfm-bm-flag-both')).boxShadow.includes('inset')"))
    check('引號實心', pg.evaluate("!!document.querySelector('.cwfm-chip-toggle[data-key=excerpt] svg circle[fill=currentColor]')"))
    check('備註＋摘錄旗頭雙色、大小一致', pg.evaluate("(()=>{const f=[...document.querySelectorAll('.cwfm-bm-flag')].map(e=>Math.round(e.getBoundingClientRect().height));return document.querySelectorAll('.cwfm-bm-flag-both').length===1 && Math.max(...f)-Math.min(...f)<=2})()"))
    check('目錄裡的書籤', sorted(rows) == ['note', 'pos'], rows)
    pg.click('.cwfm-chip-toggle[data-key="pos"]'); pg.wait_for_timeout(200)
    vis = pg.evaluate("[...document.querySelectorAll('.cwfm-bm-row')].filter(r=>r.offsetParent).map(r=>r.dataset.type)")
    check('篩選隱藏定位', vis == ['note'], vis)
    pg.click('.cwfm-chip-toggle[data-key="pos"]'); pg.wait_for_timeout(200)
    pg.click('.cwfm-bm-row[data-type="note"] .cwfm-bm-exp'); pg.wait_for_timeout(200)
    det = pg.evaluate("(document.querySelector('.cwfm-bm-card')||{}).innerText||''")
    check('展開顯示備註', '備註' in det and '$&' in det, det[:60])
    pg.screenshot(path='v1792_card.png')
    pw = pg.evaluate("[document.querySelector('.cwfm-panel.cwfm-open').getBoundingClientRect().width, document.querySelector('.cwfm-bm-card').getBoundingClientRect().left, document.querySelector('.cwfm-panel.cwfm-open').getBoundingClientRect().right]")
    check('卡片往右彈出、目錄寬度不變', pw[0] == 320 and pw[1] > pw[2], pw)
    check('匯出在篩選列', pg.evaluate("!!document.querySelector('.cwfm-toc-filter .cwfm-chip-action')"))
    # 從目錄點摘錄書籤跳轉後，標示位置要跟文字一致
    pg.evaluate(f"{VIEW}.goTo(1)"); pg.wait_for_timeout(800)
    pg.click('.cwfm-bm-row[data-type="note"] .cwfm-bm-name'); pg.wait_for_timeout(1800)
    hlpos = pg.evaluate(f"""(()=>{{const v={VIEW};const c=v.renderer.getContents()[0];const g=c.overlayer.element.querySelector('g rect');
      const bm=Object.values(JSON.parse(localStorage.getItem('cwfm-bookdata-9252')).bookmarks).find(b=>b.note);
      const r=v.resolveCFI(bm.cfi).anchor(c.doc).getClientRects()[0];return g?[Math.round(+g.getAttribute('x')),Math.round(+g.getAttribute('y')),Math.round(r.left),Math.round(r.top)]:null}})()""")
    print('HLPOS', hlpos, pg.evaluate(f"(()=>{{const c={VIEW}.renderer.getContents();return c.map(x=>[x.index, x.overlayer?x.overlayer.element.outerHTML.slice(0,200):null])}})()"), pg.evaluate("localStorage.getItem('cwfm-bookdata-9252')")[:300])
    check('跳轉後標示位置正確', hlpos and abs(hlpos[0]-hlpos[2]) <= 2 and abs(hlpos[1]-hlpos[3]) <= 2, hlpos)
    # 先跳到別處再點定位書籤
    pg.evaluate(f"{VIEW}.goTo(1)"); pg.wait_for_timeout(800)
    pg.click('.cwfm-bm-row[data-type="pos"] .cwfm-bm-body'); pg.wait_for_timeout(1500)
    check('點定位書籤回到同一個字', pg.evaluate(FIRST) == first_after, (pg.evaluate(FIRST), first_after))
    nav_put = [h for h in hits if h[0] == 'PUT' and h[1].endswith('/navhist')]
    pg.wait_for_timeout(1000)
    check('跳轉紀錄存到伺服器', STATE['navhist'] and STATE['navhist'].get('toc', {}).get('entries'), STATE['navhist'])

    # 6. 搜尋（簡體「黄」找繁體「黃」；全形 ＡＢＣ 用 abc 找到）
    pg.click('button[aria-label="搜尋"], button[aria-label="Search"]', force=True); pg.wait_for_timeout(300)
    pg.fill('.cwfm-search-panel input[type="text"]', '玄黄'); pg.keyboard.press('Enter'); pg.wait_for_timeout(2500)
    n_hits = pg.evaluate("document.querySelectorAll('.cwfm-search-hit.cwfm-sr-text').length")
    check('簡繁互通搜尋', n_hits >= 200, n_hits)
    pg.fill('.cwfm-search-panel input[type="text"]', 'abc'); pg.keyboard.press('Enter'); pg.wait_for_timeout(2500)
    n2 = pg.evaluate("document.querySelectorAll('.cwfm-search-hit.cwfm-sr-text').length")
    check('全形半形搜尋', n2 >= 10, n2)
    pg.fill('.cwfm-search-panel input[type="text"]', '备注'); pg.keyboard.press('Enter'); pg.wait_for_timeout(1500)
    nb = pg.evaluate("document.querySelectorAll('.cwfm-search-hit.cwfm-sr-bm').length")
    check('搜尋書籤備註', nb == 1, nb)
    pg.fill('.cwfm-search-panel input[type="text"]', '門前'); pg.keyboard.press('Enter'); pg.wait_for_timeout(2500)
    before = pg.evaluate(FIRST)
    pg.click('.cwfm-search-hit.cwfm-sr-text >> nth=3'); pg.wait_for_timeout(1200)
    vis_txt = pg.evaluate(f"{VIEW}.renderer.getVisibleRange().toString()")
    check('點搜尋結果跳轉', '門前' in vis_txt, before)
    cnt = lambda: pg.evaluate(f"{VIEW}.renderer.getContents()[0].overlayer.element.childElementCount")
    c_open = cnt()
    pg.click('.cwfm-search-panel .cwfm-panel-header .cwfm-close-btn'); pg.wait_for_timeout(300)
    c_closed = cnt()
    pg.click('button[aria-label="搜尋"], button[aria-label="Search"]', force=True); pg.wait_for_timeout(2500)
    check('關搜尋面板隱藏標示、再開畫回來', c_closed < c_open and cnt() == c_open, (c_open, c_closed, cnt()))
    check('搜尋紀錄併入工具列那組（面板內不再有）', pg.evaluate("!document.querySelector('.cwfm-search-panel .cwfm-nav-group') && !!document.querySelector('.cwfm-toolbar-top .cwfm-nav-group.cwfm-nav-visible')"))
    pg.click('.cwfm-search-clear'); pg.wait_for_timeout(300)
    check('搜尋框 ⓧ 清空', pg.evaluate("document.querySelector('.cwfm-search-panel input').value") == '' and cnt() < c_open, cnt())

    # 7. 匯出
    html = pg.evaluate("window.__cwfm.exportBookmarks('html')")
    md = pg.evaluate("window.__cwfm.exportBookmarks('md')")
    csv = pg.evaluate("window.__cwfm.exportBookmarks('csv')")
    check('匯出旗頭與雙標記', 'class="side f-note both"' in html and 'class="bars' not in html and html.count('class="ico') == 2 and html.count('class="tag"') >= 4, '')
    check('匯出連結開新分頁', 'target="_blank"' in html)
    check('匯出連結文字沒有 %', '">http' in html and re.search(r'">[^<]*#cfi=epubcfi\(/6/', html) is not None and '%2F' in html, '')
    check('匯出 HTML/MD/CSV', '這是 $&amp; 備註' in html and '#cfi=' in html and '> ' in md and csv.count('\n') >= 2, len(html))

    # 8. 複製連結 → 預覽模式
    link = pg.evaluate(f"location.origin+location.pathname+'#cfi='+encodeURIComponent({json.dumps(pos_bm.get('cfi',''))})")
    pg.close()
    bm_before = STATE['bookmark']
    pv = newpage(link)
    banner = pv.evaluate("(document.querySelector('.cwfm-preview-bar')||{}).innerText||''")
    check('預覽提示條', '預覽' in banner or 'Preview' in banner, banner)
    check('預覽提示在工具列裡', pv.evaluate("document.querySelector('.cwfm-preview-bar').getBoundingClientRect().bottom") <= 48)
    check('預覽位置精準', pv.evaluate(FIRST) == first_after, (pv.evaluate(FIRST), first_after))
    pv.evaluate(f"{VIEW}.renderer.next()"); pv.wait_for_timeout(1200)
    check('預覽不寫閱讀進度', STATE['bookmark'] == bm_before)
    h1 = pv.evaluate("location.hash")
    check('預覽網址跟著更新', h1.startswith('#cfi=') and h1 != '#cfi=' + urllib.parse.quote(pos_bm.get('cfi', ''), safe=''), h1[:60])
    pv.reload(); pv.wait_for_timeout(3500)
    check('重新整理仍是預覽', pv.locator('.cwfm-preview-bar').count() == 1)
    pv.click('.cwfm-preview-bar button'); pv.wait_for_timeout(1200)
    check('正式閱讀後寫入進度、移除 #cfi', STATE['bookmark'] != bm_before and pv.evaluate('location.hash') == '', STATE['bookmark'])
    synced3 = STATE['bookmark']
    first_c = pv.evaluate(FIRST)
    pv.close()

    # 9. 雲端紀錄優先：清掉本機，換一個「視窗大小」開書，第一個字跟同步的一樣
    ctx2 = b.new_context(viewport={'width': 800, 'height': 700})
    pg2 = ctx2.new_page()
    pg2.on('pageerror', lambda e: errs.append(str(e)[:200]))
    pg2.add_init_script("localStorage.setItem('cwfm-settings', %s)" % json.dumps(json.dumps({'flow': 'paginated', 'maxColumnCount': 1})))
    pg2.goto(URL); pg2.wait_for_timeout(4000)
    check('換裝置開書第一個字相同', pg2.evaluate(FIRST) == first_c, (pg2.evaluate(FIRST), first_c))
    rows2 = pg2.evaluate("document.querySelectorAll('.cwfm-bm-row').length")
    check('換裝置讀到書籤', rows2 == 2, rows2)
    nav2 = pg2.evaluate("[...document.querySelectorAll('.cwfm-toolbar-top .cwfm-nav-group[data-nav-kind=toc] button')].map(b=>b.disabled)")
    check('換裝置讀到跳轉紀錄', nav2 and nav2[0] is False, nav2)
    # 刪除書籤
    pg2.click('button[aria-label="目錄"], button[aria-label="Table of Contents"]', force=True); pg2.wait_for_timeout(300)
    pg2.click('.cwfm-bm-row[data-type="pos"] .cwfm-bm-exp'); pg2.wait_for_timeout(200)
    pg2.click('.cwfm-card-actions .cwfm-card-danger'); pg2.wait_for_timeout(200)
    pg2.click('.cwfm-confirm-ok'); pg2.wait_for_timeout(600)
    check('刪除書籤', len(STATE['bookmarks']) == 1, list(STATE['bookmarks']))
    ctx2.close()
    b.close()

print('PAGE ERRORS', errs[:10])
print('SUMMARY', sum(results), '/', len(results))
