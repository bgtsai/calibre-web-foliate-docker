"""v1.80 功能測試：首次預設、跳轉紀錄合併、書籤卡片 hover、全螢幕停用、觸控翻頁。
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
        elif p == '/cwfm/api/errlog':
            self.send(200, ('cwfm 錯誤紀錄\n網址：' + BASE + '/read/9252/epub\n閱讀器檔案：/static/js/cwfm/cwfm-reader.js').encode(), 'text/plain; charset=utf-8')
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
    errs = []

    def newpage(url, settings=None):
        pg = ctx.new_page()
        pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
        pg.on('console', lambda m: errs.append(m.text[:200]) if m.type == 'error' and 'lock initial anchor' not in m.text and '404' not in m.text else None)
        if settings is not None:
            pg.add_init_script("localStorage.setItem('cwfm-settings', %s)" % json.dumps(json.dumps(settings)))
        pg.goto(url)
        pg.wait_for_timeout(3500)
STATE['bookmarks'] = {
    'b1': {'id': 'b1', 'cfi': 'epubcfi(/6/2!/4/106)', 'chapter': '第一章', 'fraction': 0.29, 'created': 1760000000000, 'modified': 1760000000000},
    'b2': {'id': 'b2', 'cfi': 'epubcfi(/6/2!/4/4,/1:2,/1:9)', 'excerpt': '章第1段：天地', 'note': '這是備註', 'chapter': '第一章', 'fraction': 0.29, 'created': 1760000001000, 'modified': 1760000001000},
    'b4': {'id': 'b4', 'cfi': 'epubcfi(/6/4!/4/4,/1:0,/1:5)', 'excerpt': '第2章第1', 'chapter': '第二章', 'fraction': 0.6, 'created': 1760000003000, 'modified': 1760000003000},
}
SET = "window.__cwfm.settings"

with sync_playwright() as p:
    b = getattr(p, BROWSER).launch()
    errs = []

    def page(ctx, settings=None, init=''):
        pg = ctx.new_page()
        pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
        if settings is not None:
            pg.add_init_script("localStorage.setItem('cwfm-settings', %s)" % json.dumps(json.dumps(settings)))
        if init: pg.add_init_script(init)
        pg.goto(URL); pg.wait_for_timeout(3500)
        return pg

    # ---- 電腦（滑鼠）：首次預設 ----
    ctx = b.new_context(viewport={'width': 1100, 'height': 780})
    pg = page(ctx)
    check('開好書後載入提示已移除', pg.evaluate("!document.getElementById('cwfm-loading')"))
    st = pg.evaluate(SET)
    check('電腦首次預設：1 欄、內容優先、540×648、字級 120%', st['maxColumnCount'] == 1 and st['horizontalSizeMode'] == 'content' and st['targetContentWidthPx'] == 540
          and st['targetContentHeightPx'] == 648 and st['fontSize'] == 120 and st['letterSpacing'] == 0 and st['lineSpacing'] == 1.5, {k: st[k] for k in ('targetContentWidthPx', 'targetContentHeightPx', 'fontSize')})
    zc = b.new_context(viewport={'width': 1100, 'height': 780}, locale='zh-TW'); zp = page(zc)
    zst = zp.evaluate(SET)
    check('中文介面首次預設：字距 0.2、行距 1.8、字級同英文', zst['letterSpacing'] == 0.2 and zst['lineSpacing'] == 1.8 and zst['fontSize'] == 120, {k: zst[k] for k in ('letterSpacing', 'lineSpacing', 'fontSize')})
    zc.close()
    check('自動隱藏工具列／游標預設關、點擊區開', not st['autoHideToolbar'] and not st['cursorAutoHideEnabled'] and st['tapZoneEnabled'])
    check('電腦點擊區仍是攔截層', pg.evaluate("getComputedStyle(document.querySelector('.cwfm-tap-right')).pointerEvents") == 'auto')

    # ---- 跳轉紀錄合併 ----
    pg.evaluate("window.__cwfmNavRecord('link')"); pg.evaluate(f"{VIEW}.renderer.next()"); pg.wait_for_timeout(600)
    vis = lambda sel: pg.evaluate(f"(()=>{{const e=document.querySelector('{sel}');return !!e && getComputedStyle(e).display!=='none'}})()")
    check('書內連結跳轉記進工具列那組', vis('.cwfm-toolbar-top .cwfm-nav-group'))
    check('工具列顯示時浮動組不出現', not vis('.cwfm-nav-float'))
    pg.evaluate("document.documentElement.classList.add('cwfm-bars-hidden')")
    check('工具列顯示時跳轉、之後隱藏也不出現', not vis('.cwfm-nav-float'))
    pg.evaluate("window.__cwfmNavRecord('link')"); pg.wait_for_timeout(200)
    check('工具列隱藏時跳轉才出現', vis('.cwfm-nav-float'))
    pg.evaluate("document.querySelector('.cwfm-nav-float button:last-child').click()")
    check('浮動組 ✕ 只收起、紀錄保留', not vis('.cwfm-nav-float') and pg.evaluate("window.__cwfm.navSnapshot().toc.entries.length") >= 2)
    pg.evaluate("window.__cwfmNavRecord('search')"); pg.wait_for_timeout(200)
    snap = pg.evaluate("window.__cwfm.navSnapshot()")
    check('新跳轉後浮動組再出現、只剩一份紀錄', vis('.cwfm-nav-float') and list(snap.keys()) == ['toc'], list(snap.keys()))
    pg.evaluate("document.documentElement.classList.remove('cwfm-bars-hidden')")
    pg.wait_for_timeout(1500)  # 讓跳轉紀錄存到伺服器
    # 重新整理＋自動隱藏工具列：讀回紀錄但不自己冒出來；喚醒後收回、再隱藏也不出現
    pa = page(ctx, {'autoHideToolbar': True, 'maxColumnCount': 1}); pa.mouse.move(550, 400); pa.wait_for_timeout(4500)
    visa = lambda: pa.evaluate("(()=>{const e=document.querySelector('.cwfm-nav-float');return !!e && getComputedStyle(e).display!=='none'})()")
    check('重新整理後自動隱藏：有紀錄也不自己出現', pa.evaluate("document.documentElement.classList.contains('cwfm-bars-hidden')") and pa.evaluate("window.__cwfm.navSnapshot().toc.entries.length") > 0 and not visa())
    pa.evaluate("window.__cwfmNavRecord('link')"); pa.wait_for_timeout(200)
    check('隱藏狀態下跳轉 → 出現', visa())
    pa.evaluate("document.querySelector('.cwfm-autohide-zone.cwfm-top').click()"); pa.wait_for_timeout(300)
    hid_after_wake = not visa(); pa.mouse.move(560, 420); pa.wait_for_timeout(4500)
    check('喚醒後收回、再自動隱藏也不出現', hid_after_wake and pa.evaluate("document.documentElement.classList.contains('cwfm-bars-hidden')") and not visa())
    pa.close()

    # ---- 書籤卡片：hover 開啟、換張、離開關閉、點箭頭釘住、F 樣式 ----
    pg.click('button[aria-label="目錄"], button[aria-label="Table of Contents"]', force=True); pg.wait_for_timeout(800)
    qn = pg.evaluate("[...document.querySelectorAll('.cwfm-bm-row[data-type=excerpt] .cwfm-bm-name')].map(e=>e.textContent)")
    check('英文介面：未命名摘錄用英文引號', all(n.startswith('\u201c') and n.endswith('\u201d') for n in qn) and qn, qn)
    for k in ('chapters', 'pos', 'excerpt', 'note'):
        pg.evaluate(f"document.querySelector('.cwfm-chip-toggle[data-key={k}]')?.click()"); pg.wait_for_timeout(100)
    emp = pg.evaluate("(()=>{const e=document.querySelector('.cwfm-toc-empty');return e&&getComputedStyle(e).display!=='none'?e.textContent:''})()")
    check('篩選全關：顯示沒有符合篩選條件', emp == 'Nothing matches the current filter', emp)
    for k in ('chapters', 'pos', 'excerpt', 'note'):
        pg.evaluate(f"document.querySelector('.cwfm-chip-toggle[data-key={k}]')?.click()"); pg.wait_for_timeout(100)
    check('篩選恢復後空狀態消失', pg.evaluate("getComputedStyle(document.querySelector('.cwfm-toc-empty')).display") == 'none')
    rows = pg.query_selector_all('.cwfm-bm-row')
    r1, r2 = rows[0].bounding_box(), rows[1].bounding_box()
    pg.mouse.move(r1['x'] + 60, r1['y'] + r1['height'] / 2); pg.wait_for_timeout(400)
    id1 = pg.evaluate("document.querySelector('.cwfm-bm-card')?.dataset.type")
    check('滑鼠移上去就開卡片', id1 is not None, id1)
    # v1.80.8：hover 只亮指到的那一塊；卡片打開時整列的類型色外框不變
    HV = "(()=>{const r=document.querySelector('.cwfm-bm-row.cwfm-bm-active');const s=e=>getComputedStyle(r.querySelector(e)).boxShadow;return {body:s('.cwfm-bm-body'),exp:s('.cwfm-bm-exp'),frame:getComputedStyle(r).backgroundColor}})()"
    h1 = pg.evaluate(HV)
    check('hover 左邊跳轉區：只有左邊變亮', h1['body'] != 'none' and h1['exp'] == 'none', h1)
    pg.screenshot(path=f'v1808_hover_body_{BROWSER}.png', clip={'x': 0, 'y': max(0, r1['y'] - 40), 'width': 420, 'height': 120})
    pg.mouse.move(r1['x'] + r1['width'] - 12, r1['y'] + r1['height'] / 2); pg.wait_for_timeout(300)
    h2 = pg.evaluate(HV)
    check('hover 右邊 ›：只有箭頭那格變亮', h2['exp'] != 'none' and h2['body'] == 'none', h2)
    check('hover 不改類型色外框', h1['frame'] == h2['frame'] and h1['frame'] not in ('rgba(0, 0, 0, 0)', ''), (h1['frame'], h2['frame']))
    pg.screenshot(path=f'v1808_hover_exp_{BROWSER}.png', clip={'x': 0, 'y': max(0, r1['y'] - 40), 'width': 420, 'height': 120})
    sch0 = pg.evaluate("document.documentElement.dataset.cwfmScheme||''")
    pg.evaluate("document.documentElement.dataset.cwfmScheme='light'"); pg.wait_for_timeout(100)
    TINT = {'pos': 'rgba(226, 75, 74, 0.15)', 'excerpt': 'rgba(250, 199, 117, 0.15)', 'note': 'rgba(159, 225, 203, 0.15)'}
    ty = pg.evaluate("document.querySelector('.cwfm-bm-row.cwfm-bm-active').dataset.type")
    check('hover 用卡片抬頭同一套類型淡色（深淺主題相同）', TINT[ty] in h2['exp'] and TINT[ty] in pg.evaluate(HV)['exp'], (ty, h2['exp']))
    pg.screenshot(path=f'v1808_hover_exp_light_{BROWSER}.png', clip={'x': 0, 'y': max(0, r1['y'] - 40), 'width': 420, 'height': 120})
    pg.evaluate(f"document.documentElement.dataset.cwfmScheme={json.dumps(sch0)}")
    pg.mouse.move(r1['x'] + 60, r1['y'] + r1['height'] / 2); pg.wait_for_timeout(300)
    pg.screenshot(path=f'v180_card_{BROWSER}.png')
    ol = pg.evaluate("(()=>{const c=document.querySelector('.cwfm-bm-card');const sv=c.querySelector('svg.cwfm-card-outline');const ps=sv?sv.querySelectorAll('path'):[];return {n:ps.length,w:+(sv&&sv.getAttribute('width')),cw:c.offsetWidth,stroke:ps[2]&&getComputedStyle(ps[2]).stroke,d:ps[0]&&ps[0].getAttribute('d').length,ring:getComputedStyle(c).boxShadow}})()")
    check('卡片外框一條 SVG 路徑（底色、標題淡色、色框）、寬度跟卡片一致', ol['n'] == 3 and ol['w'] == ol['cw'] and ol['stroke'] not in (None, 'none') and '0px 0px 0px 2px' not in ol['ring'], ol)
    pg.screenshot(path=f'v1801_card_{BROWSER}.png', clip={'x': 300, 'y': 150, 'width': 140, 'height': 120})
    pg.mouse.move(r2['x'] + 60, r2['y'] + r2['height'] / 2); pg.wait_for_timeout(400)
    check('移到另一張就換卡片', pg.evaluate("document.querySelector('.cwfm-bm-card')?.dataset.type") != id1)
    pg.mouse.move(r2['x'] + 60, r2['y'] + 300); pg.wait_for_timeout(600)
    check('滑鼠離開後關閉', pg.evaluate("!document.querySelector('.cwfm-bm-card')"))
    pg.mouse.move(r1['x'] + 60, r1['y'] + r1['height'] / 2); pg.wait_for_timeout(400)
    pg.click('.cwfm-bm-row[data-id] .cwfm-bm-exp >> nth=0'); pg.wait_for_timeout(200)
    pg.mouse.move(r2['x'] + 60, r2['y'] + 300); pg.wait_for_timeout(600)
    check('點箭頭釘住，滑鼠離開不關', pg.evaluate("!!document.querySelector('.cwfm-bm-card')"))
    pg.mouse.move(r2['x'] + 60, r2['y'] + r2['height'] / 2); pg.wait_for_timeout(400)
    check('釘住時移到另一張也會換', pg.evaluate("document.querySelector('.cwfm-bm-card')?.dataset.type") != id1)
    pg.click('.cwfm-bm-card button:has-text("Edit"), .cwfm-bm-card button:has-text("編輯")'); pg.wait_for_timeout(700)
    check('從卡片按編輯：對話框開著時卡片不被關掉', pg.evaluate("!!document.querySelector('.cwfm-bm-card')"))
    zz = pg.evaluate("[+getComputedStyle(document.querySelector('.cwfm-confirm-overlay')).zIndex, +getComputedStyle(document.querySelector('.cwfm-bm-card')).zIndex]")
    check('編輯對話框在卡片之上', zz[0] > zz[1], zz)
    pg.click('.cwfm-bm-dialog .cwfm-confirm-cancel'); pg.wait_for_timeout(300)
    pg.evaluate("window.__fs=true;window.__fsReq=0;Object.defineProperty(document,'fullscreenElement',{get(){return window.__fs?document.documentElement:null},configurable:true});document.documentElement.requestFullscreen=function(){if(/at close|close@/.test(String(new Error().stack)))window.__fsReq++;window.__fs=true;return Promise.resolve()}")
    pg.click('.cwfm-bm-card button:has-text("Edit"), .cwfm-bm-card button:has-text("編輯")'); pg.wait_for_timeout(500)
    pg.evaluate("window.__fs=false"); pg.click('.cwfm-bm-dialog .cwfm-confirm-cancel'); pg.wait_for_timeout(300)
    check('對話框開著時被踢出全螢幕 → 關閉時自動回全螢幕', pg.evaluate("window.__fsReq") == 1)
    pg.evaluate("delete document.fullscreenElement")
    pg.click('.cwfm-bm-card button:has-text("Edit"), .cwfm-bm-card button:has-text("編輯")'); pg.wait_for_timeout(500)
    dt = pg.evaluate("(()=>{const d=document.querySelector('.cwfm-bm-dialog');return [d.dataset.type,getComputedStyle(d).borderTopWidth,getComputedStyle(d).borderTopColor]})()")
    check('編輯對話框外框＝那張書籤的類型色（2px）', dt[1] == '2px' and dt[0] in ('pos', 'note'), dt)
    pg.screenshot(path=f'v1803_dialog_{BROWSER}.png')
    pg.fill('.cwfm-bm-dialog textarea', '新備註'); pg.wait_for_timeout(100)
    t1 = pg.evaluate("document.querySelector('.cwfm-bm-dialog').dataset.type")
    pg.fill('.cwfm-bm-dialog textarea', ''); pg.wait_for_timeout(100)
    t2 = pg.evaluate("document.querySelector('.cwfm-bm-dialog').dataset.type")
    check('打備註即時變備註色、清空變回', t1 == 'note' and t2 in ('pos', 'excerpt'), (t1, t2))
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    # v1.80.7：Esc 一次只關最上層（焦點在輸入框、在按鈕上都一樣）
    st = pg.evaluate("[!!document.querySelector('.cwfm-bm-dialog'), !!document.querySelector('.cwfm-bm-card')]")
    check('Esc（焦點在備註欄）只關對話框、卡片留著', st == [False, True], st)
    pg.click('.cwfm-bm-card button:has-text("Edit"), .cwfm-bm-card button:has-text("編輯")'); pg.wait_for_timeout(500)
    pg.focus('.cwfm-bm-dialog .cwfm-confirm-cancel'); pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    st = pg.evaluate("[!!document.querySelector('.cwfm-bm-dialog'), !!document.querySelector('.cwfm-bm-card')]")
    check('Esc（焦點在按鈕）也只關對話框、卡片留著', st == [False, True], st)
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    check('對話框關掉後再按 Esc 才關卡片', pg.evaluate("!document.querySelector('.cwfm-bm-card')"))
    # v1.81.0：「關於」分組在最後、預設收起；展開後有版本、打包方式、說明頁（Docker 版沒有檢查更新）
    pg.click('button[aria-label="設定"], button[aria-label="Settings"]', force=True); pg.wait_for_timeout(600)
    AB = "(()=>{const gs=[...document.querySelectorAll('.cwfm-settings-panel .cwfm-group')];const g=gs[gs.length-1];const t=g.querySelector('.cwfm-group-title').textContent;const b=g.querySelector('.cwfm-group-body');return {last:t,hidden:getComputedStyle(b).display==='none',rows:[...g.querySelectorAll('.cwfm-about-row')].map(r=>r.textContent),links:[...g.querySelectorAll('.cwfm-about-links a')].map(a=>[a.textContent,a.href,a.target]),fs:g.querySelector('.cwfm-about-row')&&getComputedStyle(g.querySelector('.cwfm-about-row')).fontSize,old:!!document.querySelector('.cwfm-version-line')}})()"
    ab = pg.evaluate(AB)
    check('「關於」是最後一個分組、預設收起、舊的最底下版本行已移除', ab['last'] in ('關於', 'About') and ab['hidden'] and not ab['old'], ab)
    pg.evaluate("[...document.querySelectorAll('.cwfm-settings-panel .cwfm-group-title')].pop().click()"); pg.wait_for_timeout(300)
    ab = pg.evaluate(AB)
    check('展開後：版本、發布日期、安裝方式 Docker，說明頁（GitHub）指向 Docker repo、開新分頁、沒有檢查更新',
          not ab['hidden'] and len(ab['rows']) == 3 and re.search(r'\d{4}-\d{2}-\d{2}$', ab['rows'][1]) and ab['rows'][2].endswith('Docker')
          and len(ab['links']) == 1 and ab['links'][0][0] in ('說明頁（GitHub）', 'Documentation (GitHub)')
          and ab['links'][0][1] == 'https://github.com/bgtsai/calibre-web-foliate-docker' and ab['links'][0][2] == '_blank', ab)
    fs = pg.evaluate("(()=>{const r=document.querySelector('.cwfm-about-row');const l=[...document.querySelectorAll('.cwfm-settings-panel .cwfm-group')].find(g=>/Language|語言/.test(g.textContent)).querySelector('label');return [getComputedStyle(r.children[0]).fontSize,getComputedStyle(r.children[1]).fontSize,getComputedStyle(document.querySelector('.cwfm-about-links a')).fontSize,getComputedStyle(l).fontSize,getComputedStyle(r.children[0]).color===getComputedStyle(l).color]})()")
    check('字級跟其他分組一致：名稱 12px（同欄位說明、同色）、內容與連結 13px', fs[:3] == ['12px', '13px', '13px'] and fs[3] == '12px' and fs[4], fs)
    pg.evaluate("document.querySelector('.cwfm-settings-panel .cwfm-panel-body').scrollTop=1e6"); pg.wait_for_timeout(200)
    pg.screenshot(path=f'v1810_about_{BROWSER}.png')
    pg.close()

    # ---- 全螢幕不支援：停用外觀＋提示 ----
    pg = page(ctx, {'maxColumnCount': 1}, "Object.defineProperty(Document.prototype,'fullscreenEnabled',{get(){return false},configurable:true});")
    fs = pg.query_selector('.cwfm-toolbar-top button[aria-label="全螢幕"], .cwfm-toolbar-top button[aria-label="Fullscreen"]')
    check('不支援全螢幕時按鈕停用外觀', fs.get_attribute('aria-disabled') == 'true')
    fs.dispatch_event('click'); pg.wait_for_timeout(300)
    check('點停用的全螢幕鈕跳提示', pg.evaluate("[...document.querySelectorAll('.cwfm-toast')].map(e=>e.textContent).join()") in ('該瀏覽器不支援全螢幕', 'This browser does not support fullscreen'))
    n0 = len([h for h in hits if 'errlog' in h[1]])
    pg.evaluate("window.dispatchEvent(new ErrorEvent('error',{message:'Script error.'}))"); pg.wait_for_timeout(6500)
    badge = pg.evaluate("[...document.querySelectorAll('button')].filter(b=>/^⚠/.test(b.textContent)&&getComputedStyle(b).display!=='none').map(b=>b.textContent)")
    check('沒有檔名的 Script error 不亮 ⚠；預設沒同意就不上傳', not badge and len([h for h in hits if 'errlog' in h[1]]) == n0, badge)
    # 設定面板：錯誤紀錄區、同意後才開、下載遮主機、清除
    pg.evaluate("document.querySelectorAll('.cwfm-toolbar-top button')[document.querySelectorAll('.cwfm-toolbar-top button').length-2].click()"); pg.wait_for_timeout(800)
    has = pg.evaluate("(()=>{const c=document.querySelector('.cwfm-errlog-card');return !!c && c.querySelectorAll('li').length===5 && !!c.querySelector('.cwfm-switch input') && !!c.querySelector('.cwfm-errlog-buttons')})()")
    check('錯誤紀錄卡：說明 5 條、開關與按鈕都在卡片內', has)
    cb = pg.evaluate_handle("document.querySelector('.cwfm-errlog-card .cwfm-switch input')")
    check('錯誤紀錄開關預設關、下載／清除停用', not cb.evaluate("e=>e.checked") and pg.evaluate("[...document.querySelectorAll('.cwfm-errlog-buttons button')].every(b=>b.disabled) && document.querySelector('.cwfm-errlog-deps').classList.contains('cwfm-disabled')"))
    check('按鈕文字精簡', pg.evaluate("[...document.querySelectorAll('.cwfm-errlog-buttons button')].map(b=>b.textContent).join('/')") in ('下載記錄/清除記錄', 'Download log/Clear log'))
    cb.evaluate("e=>e.click()"); pg.wait_for_timeout(300)
    dlg = pg.evaluate("!!document.querySelector('.cwfm-consent-dialog')")
    pg.click('.cwfm-consent-dialog .cwfm-confirm-cancel'); pg.wait_for_timeout(200)
    check('打開時先跳同意框；取消就維持關', dlg and not cb.evaluate("e=>e.checked") and not pg.evaluate("window.__cwfm.settings.errlogUpload"))
    cb.evaluate("e=>e.click()"); pg.wait_for_timeout(300)
    pg.click('.cwfm-consent-dialog .cwfm-ok-primary'); pg.wait_for_timeout(200)
    check('按同意並開啟才生效、按鈕跟著啟用', cb.evaluate("e=>e.checked") and pg.evaluate("window.__cwfm.settings.errlogUpload") is True and pg.evaluate("[...document.querySelectorAll('.cwfm-errlog-buttons button')].every(b=>!b.disabled)"))
    n1 = len([h for h in hits if 'errlog' in h[1]])
    pg.evaluate("window.dispatchEvent(new ErrorEvent('error',{message:'Script error.'}))"); pg.wait_for_timeout(6500)
    check('同意後出錯才上傳', len([h for h in hits if 'errlog' in h[1] and h[0] == 'POST']) > 0 and len([h for h in hits if 'errlog' in h[1]]) > n1)
    with pg.expect_download() as dli:
        pg.evaluate("[...document.querySelectorAll('.cwfm-errlog-buttons button')][0].click()")
    txt = open(dli.value.path(), encoding='utf-8').read()
    check('下載的紀錄遮掉主機、保留路徑', '<host>/read/9252/epub' in txt and '127.0.0.1' not in txt and txt[:1] in ('※', '*'), txt[:80])
    pg.evaluate("[...document.querySelectorAll('.cwfm-errlog-buttons button')][1].click()"); pg.wait_for_timeout(300)
    pg.click('.cwfm-confirm-box .cwfm-confirm-ok'); pg.wait_for_timeout(500)
    check('清除送出 DELETE', any(h[0] == 'DELETE' and 'errlog' in h[1] for h in hits))
    nd = len([h for h in hits if h[0] == 'DELETE' and 'errlog' in h[1]])
    cb.evaluate("e=>e.click()"); pg.wait_for_timeout(300)
    btns = pg.evaluate("[...document.querySelectorAll('.cwfm-confirm-box .cwfm-confirm-buttons button')].map(b=>b.textContent)")
    pg.click('.cwfm-confirm-box .cwfm-confirm-ok'); pg.wait_for_timeout(500)
    check('關閉時問要不要清除；選清除並關閉 → 送 DELETE、開關關、按鈕停用', len(btns) == 3 and not cb.evaluate("e=>e.checked")
          and len([h for h in hits if h[0] == 'DELETE' and 'errlog' in h[1]]) > nd and pg.evaluate("document.querySelector('.cwfm-errlog-deps').classList.contains('cwfm-disabled')"), btns)
    pg.screenshot(path=f'v1804_settings_{BROWSER}.png')
    pg.close(); ctx.close()

    # ---- 觸控：手機／平板首次預設與點擊翻頁（chromium 才能模擬 is_mobile） ----
    if BROWSER == 'chromium':
        for name, vp in (('phone', {'width': 390, 'height': 844}), ('tablet', {'width': 768, 'height': 1024})):
            tctx = b.new_context(viewport=vp, is_mobile=True, has_touch=True, **({'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.3 Safari/605.1.15'} if name == 'tablet' else {}))
            tp = page(tctx)
            st = tp.evaluate(SET)
            if name == 'phone':
                check('手機首次預設：留白優先、左右 16、字級 120%、點擊區 98', st['horizontalSizeMode'] == 'margin' and st['leftRightPadding'] == 16 and st['fontSize'] == 120 and st['tapZoneWidthPx'] == 98,
                      {k: st[k] for k in ('horizontalSizeMode', 'leftRightPadding', 'fontSize', 'tapZoneWidthPx')})
                check('觸控時點擊區不攔截', tp.evaluate("getComputedStyle(document.querySelector('.cwfm-tap-right')).pointerEvents") == 'none')
                f0 = tp.evaluate(FIRST)
                tp.touchscreen.tap(vp['width'] - 30, 420); tp.wait_for_timeout(900)
                f1 = tp.evaluate(FIRST)
                check('點右側翻下一頁', f1 != f0, (f0, f1))
                tp.touchscreen.tap(vp['width'] / 2, 420); tp.wait_for_timeout(900)
                check('點中間不翻頁', tp.evaluate(FIRST) == f1)
                tp.touchscreen.tap(30, 420); tp.wait_for_timeout(900)
                check('點左側翻回上一頁', tp.evaluate(FIRST) == f0)
                tp.screenshot(path='v180_phone.png')
                tp.evaluate(f"{VIEW}.goTo('epubcfi(/6/2!/4/230)')"); tp.wait_for_timeout(1500)
                seq = []
                for _ in range(8):
                    tp.touchscreen.tap(vp['width'] - 30, 420); tp.wait_for_timeout(450)
                    seq.append(round(tp.evaluate(f"{VIEW}.lastLocation?.fraction"), 3))
                check('跨章節後點右側仍能一直翻頁', len(set(seq)) >= 7 and seq == sorted(seq), seq)
            else:
                check('平板首次預設：內容優先 528×634、字級 200%', st['horizontalSizeMode'] == 'content' and st['targetContentWidthPx'] == 528 and st['targetContentHeightPx'] == 634 and st['fontSize'] == 200,
                      {k: st[k] for k in ('targetContentWidthPx', 'targetContentHeightPx', 'fontSize')})
                tp.screenshot(path='v180_tablet.png')
                f0 = tp.evaluate(FIRST)
                tp.touchscreen.tap(vp['width'] - 30, 500); tp.wait_for_timeout(900)
                f1 = tp.evaluate(FIRST)
                check('平板點右側空白（內容框外）翻下一頁', f1 != f0, (f0, f1))
                tp.touchscreen.tap(30, 500); tp.wait_for_timeout(900)
                check('平板點左側空白翻回上一頁', tp.evaluate(FIRST) == f0)
                tp.touchscreen.tap(30, 24); tp.wait_for_timeout(600)
                check('點工具列不翻頁', tp.evaluate(FIRST) == f0)
                tp.evaluate("Object.defineProperty(document,'fullscreenElement',{get(){return document.documentElement},configurable:true});document.dispatchEvent(new Event('fullscreenchange'))")
                tp.wait_for_timeout(300)
                pl = tp.evaluate("getComputedStyle(document.querySelector('.cwfm-toolbar-top')).paddingLeft")
                ua = tp.evaluate("navigator.userAgent")
                check('平板全螢幕時工具列左側讓開 ✕（iPad 識別字串時）', pl == '78px' if ('iPad' in ua or 'Macintosh' in ua) else pl == '14px', (pl, ua[:40]))
            tctx.close()
    print('PAGE ERRORS', errs)
    print('SUMMARY', sum(results), '/', len(results))
    b.close()
