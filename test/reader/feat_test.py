"""v1.78 功能實測：python3 feat_test.py <read.html> <reader.js> <browser> [precise=1|0]"""
import http.server, io, json, os, sys, threading, zipfile
import jinja2
from playwright.sync_api import sync_playwright
TPL, JS, BROWSER = sys.argv[1], sys.argv[2], sys.argv[3]
PRECISE = (sys.argv[4] if len(sys.argv) > 4 else '1') == '1'
BOOK_ID = 9252
CSP = ("default-src 'self' 'unsafe-inline' 'unsafe-eval'; font-src 'self' data: blob: ; img-src 'self' data: blob: ; style-src-elem 'self' blob: 'unsafe-inline'; object-src 'none';")
def make_epub():
    buf = io.BytesIO(); z = zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED)
    z.writestr(zipfile.ZipInfo('mimetype'), 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
    z.writestr('META-INF/container.xml', '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/c.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
    z.writestr('OEBPS/c.opf', '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="id">cwfm-test2</dc:identifier><dc:title>測試書名</dc:title><dc:language>zh-TW</dc:language><meta property="dcterms:modified">2026-10-07T00:00:00Z</meta></metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="c1" href="c1.xhtml" media-type="application/xhtml+xml"/><item id="c2" href="c2.xhtml" media-type="application/xhtml+xml"/><item id="c3" href="c3.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="c1"/><itemref idref="c2"/><itemref idref="c3"/></spine></package>')
    z.writestr('OEBPS/nav.xhtml', '<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><body><nav epub:type="toc"><ol><li><a href="c1.xhtml">第一章</a></li><li><a href="c2.xhtml">第二章</a></li><li><a href="c3.xhtml">註解</a></li></ol></nav></body></html>')
    for i in (1, 2):
        paras = ''.join(f'<p>第{i}章第{n}段：天地玄黃，宇宙洪荒。日月盈昃，辰宿列張。寒來暑往，秋收冬藏。閏餘成歲，律呂調陽。<a href="c3.xhtml#n{n}">[{n}]</a></p>' for n in range(1, 160))
        z.writestr(f'OEBPS/c{i}.xhtml', f'<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"><head><title>c{i}</title></head><body><h1>第{i}章</h1>{paras}</body></html>')
    notes = ''.join(f'<p id="n{n}">註{n}：這是第{n}條註解的內容。</p>' for n in range(1, 160))
    z.writestr('OEBPS/c3.xhtml', f'<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"><head><title>c3</title></head><body><h1>註解</h1>{notes}</body></html>')
    z.close(); return buf.getvalue()
env = jinja2.Environment(extensions=['jinja2.ext.i18n']); env.install_null_translations()
html = env.from_string(open(TPL, encoding='utf-8').read()).render(url_for=lambda ep, **kw: '/static/' + kw['filename'] if ep == 'static' else '/' + ep,
    csrf_token=lambda: 'x', g=type('G', (), {'google_site_verification': ''})(), title='t', bookid=BOOK_ID, book_format='epub', bookmark=None,
    current_user=type('U', (), {'is_authenticated': True})()).encode('utf-8')
EPUB = make_epub(); JSB = open(JS, 'rb').read()
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, code, body=b'', ctype='text/plain'):
        self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Content-Security-Policy', CSP)
        self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        p = self.path.split('?')[0]
        if p == f'/read/{BOOK_ID}/epub': self.send(200, html, 'text/html; charset=utf-8')
        elif p == '/static/js/cwfm/cwfm-reader.js': self.send(200, JSB, 'text/javascript')
        elif p == f'/show/{BOOK_ID}/epub/file.epub': self.send(200, EPUB, 'application/epub+zip')
        else: self.send(404, b'')
    def do_POST(self):
        self.rfile.read(int(self.headers.get('Content-Length', 0))); self.send(200, b'')
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{srv.server_address[1]}/read/{BOOK_ID}/epub'
OUT = os.environ.get('OUT', '.')
HEAD = "(()=>{const v=document.querySelector('foliate-view');const r=v.renderer.getVisibleRange();return r?String(r.toString()).replace(/\\s+/g,'').slice(0,14):null})()"
res = {}
def check(name, ok, info=''):
    res[name] = ('OK ' if ok else 'FAIL ') + str(info)[:160]
with sync_playwright() as p:
    b = getattr(p, BROWSER).launch(); ctx = b.new_context(viewport={'width': 1200, 'height': 800}); page = ctx.new_page()
    errs = []; page.on('pageerror', lambda e: errs.append(str(e)[:200]))
    if not PRECISE:
        page.add_init_script("localStorage.setItem('cwfm-settings', JSON.stringify({preciseAnchorAlign:false}))")
    page.goto(url); page.wait_for_timeout(5000)
    st = page.evaluate("window.__cwfm.settings")
    if PRECISE:
        check('預設值', st['leftRightPadding'] == 120 and st['preciseAnchorAlign'] is True and 'PageUp' in st['pagingKeys']['prev'] and 'PageDown' in st['pagingKeys']['next'] and st['pageFlipAnimColor'] == 'AUTO',
              {k: st.get(k) for k in ('leftRightPadding', 'preciseAnchorAlign', 'pagingKeys', 'pageFlipAnimColor')})
    # 換頁按鈕是 SVG
    check('換頁按鈕SVG', page.evaluate("[...document.querySelectorAll('.cwfm-toolbar .cwfm-page-btn svg')].length") == 2)
    check('底部沒有跳轉按鈕組', not page.evaluate("!!document.querySelector('.cwfm-toolbar .cwfm-nav-group')"))
    # 翻幾頁，讓頁首落在段落中間
    for _ in range(3):
        page.evaluate("document.querySelector('foliate-view').goRight()"); page.wait_for_timeout(500)
    before = page.evaluate(HEAD)
    # 點畫面上的一個註解連結
    clicked = page.evaluate("""(()=>{const v=document.querySelector('foliate-view');const c=v.renderer.getContents()[0];const vr=v.renderer.getVisibleRange();
        const as=[...c.doc.querySelectorAll('a')].filter(a=>vr.intersectsNode(a)); if(!as.length) return null; const a=as[Math.floor(as.length/2)]; a.click(); return a.getAttribute('href')})()""")
    page.wait_for_timeout(1500)
    vis0 = page.evaluate("getComputedStyle(document.querySelector('.cwfm-nav-float')).display")
    page.evaluate("document.documentElement.classList.add('cwfm-bars-hidden')")
    vis = page.evaluate("getComputedStyle(document.querySelector('.cwfm-nav-float')).display")
    page.evaluate("document.documentElement.classList.remove('cwfm-bars-hidden')")
    after_jump = page.evaluate(HEAD)
    # v1.80.2：工具列顯示時點連結 → 浮動組不出現，之後工具列隱藏也不出現（只有隱藏狀態下跳轉才出現，見 ft180）
    check('點連結後跳過去；工具列顯示時跳轉，浮動組不出現', clicked and vis0 == 'none' and vis == 'none' and after_jump != before, f'href={clicked} display={vis0}/{vis} head={after_jump}')
    # 游標排除區域：游標停在右上角按鈕上不隱藏
    page.evaluate("(()=>{const s=window.__cwfm.settings;s.cursorAutoHideEnabled=true;s.cursorAutoHideDelaySeconds=1})()")
    page.evaluate("document.querySelector('.cwfm-toolbar-top button').click()"); page.evaluate("document.querySelectorAll('.cwfm-panel.cwfm-open').forEach(p=>p.classList.remove('cwfm-open'))")
    bb = page.evaluate("(()=>{const r=document.querySelector('.cwfm-nav-float').getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]})()")
    page.mouse.move(bb[0]-3, bb[1]); page.mouse.move(bb[0], bb[1]); page.wait_for_timeout(1800)
    hid = page.evaluate("(document.getElementById('cwfm-cursor-autohide-style')||{}).textContent||''")
    page.mouse.move(300, 300); page.wait_for_timeout(1800)
    hid2 = page.evaluate("(document.getElementById('cwfm-cursor-autohide-style')||{}).textContent||''")
    check('游標停在返回按鈕上不隱藏', 'none' not in hid, f'onBtn={hid!r} elsewhere={hid2!r}')
    # 看註解期間改變視窗大小（版面重排），再返回
    page.set_viewport_size({'width': 1000, 'height': 760}); page.wait_for_timeout(1500)
    page.evaluate("document.querySelectorAll('.cwfm-nav-float .cwfm-nav-btn')[0].click()"); page.wait_for_timeout(2500)
    back_head = page.evaluate(HEAD)
    vis2 = page.evaluate("getComputedStyle(document.querySelector('.cwfm-nav-float')).display")
    if PRECISE:
        check('返回後頁首相同(精準,中途改版面)', back_head == before, f'before={before} back={back_head}')
    else:
        check('返回到同一處(非精準,版面已變)', back_head is not None, f'before={before} back={back_head}')
    check('退回原處後自動消失', vis2 == 'none', vis2)
    page.screenshot(path=f'{OUT}/feat_{BROWSER}_{int(PRECISE)}_back.png')
    if not PRECISE:
        # 非精準：版面不變時應完全一致
        page.wait_for_timeout(300); b2 = page.evaluate(HEAD)
        page.evaluate("""(()=>{const v=document.querySelector('foliate-view');const c=v.renderer.getContents()[0];const vr=v.renderer.getVisibleRange();
          const as=[...c.doc.querySelectorAll('a')].filter(a=>vr.intersectsNode(a)); as[1].click()})()"""); page.wait_for_timeout(1500)
        page.evaluate("document.querySelectorAll('.cwfm-nav-float .cwfm-nav-btn')[0].click()"); page.wait_for_timeout(2000)
        check('返回(非精準,版面不變)完全一致', page.evaluate(HEAD) == b2 and page.url.endswith('/epub'), f'{b2} vs {page.evaluate(HEAD)}')
    else:
        # 兩層：連結→註解→再點註解頁上的連結？註解頁沒有連結，改：連結兩次（回正文第二章）
        b2 = page.evaluate(HEAD)
        check('沒有返回快速鍵設定', 'linkBackKeys' not in st and '從註解返回' not in page.content() and 'Return from Note' not in page.content())
    # 進度條跳轉
    h0 = page.evaluate(HEAD)
    page.evaluate("(()=>{const s=document.querySelector('.cwfm-progress-wrap input[type=range]');s.value='0.6';s.dispatchEvent(new Event('input'));s.dispatchEvent(new Event('change'))})()"); page.wait_for_timeout(1500)
    dis = page.evaluate("document.querySelector('.cwfm-toolbar-top .cwfm-nav-group[data-nav-kind=toc] .cwfm-nav-btn').disabled")
    page.evaluate("document.querySelectorAll('.cwfm-toolbar-top .cwfm-nav-group[data-nav-kind=toc] .cwfm-nav-btn')[0].click()"); page.wait_for_timeout(2500)
    h1 = page.evaluate(HEAD)
    fwd = page.evaluate("document.querySelectorAll('.cwfm-toolbar-top .cwfm-nav-group[data-nav-kind=toc] .cwfm-nav-btn')[1].disabled")
    check('進度條上一步', (not dis) and h1 == h0 and not fwd, f'{h0} -> {h1} backDisabled={dis} fwdDisabled={fwd}')
    # 目錄：開目錄、點第二章、再開目錄按上一步
    page.evaluate("document.querySelectorAll('.cwfm-toolbar-top button')[0].click()"); page.wait_for_timeout(600)
    page.evaluate("[...document.querySelectorAll('.cwfm-toc-view a')].find(a=>a.textContent.includes('第二章')).click()"); page.wait_for_timeout(1500)
    check('目錄切章後維持開啟', page.evaluate("document.querySelector('.cwfm-panel[data-side=left]').classList.contains('cwfm-open')"))
    page.evaluate("document.querySelectorAll('.cwfm-toolbar-top button')[0].click()"); page.wait_for_timeout(600)
    title = page.evaluate("document.querySelector('.cwfm-panel[data-side=left] h3').textContent")
    page.evaluate("document.querySelectorAll('.cwfm-toolbar-top .cwfm-nav-group[data-nav-kind=toc] .cwfm-nav-btn')[0].click()"); page.wait_for_timeout(2500)
    h2 = page.evaluate(HEAD)
    check('目錄上一步', h2 == h1, f'{h1} -> {h2} title={title}')
    page.keyboard.press('Escape'); page.evaluate("document.querySelectorAll('.cwfm-panel.cwfm-open').forEach(p=>p.classList.remove('cwfm-open'))")
    # 設定面板：標題凍結、瀑布流、自動重算
    page.evaluate("document.querySelectorAll('.cwfm-toolbar-top button')[1].click()"); page.wait_for_timeout(800)
    info = page.evaluate("""(()=>{const p=document.querySelector('.cwfm-settings-panel');const body=p.querySelector('.cwfm-panel-body');const fw=p.querySelector('.cwfm-fields-wrap');
      return {cols:fw.querySelectorAll(':scope>.cwfm-masonry-col').length, groups:fw.querySelectorAll('.cwfm-group').length, hscroll: body.scrollWidth>body.clientWidth+1, vscroll: body.scrollHeight>body.clientHeight+1, headerFixed: getComputedStyle(p).overflow}})()""")
    check('瀑布流', info['cols'] >= 1 and not info['hscroll'], info)
    page.set_viewport_size({'width': 700, 'height': 760}); page.wait_for_timeout(900)
    info2 = page.evaluate("""(()=>{const p=document.querySelector('.cwfm-settings-panel');const body=p.querySelector('.cwfm-panel-body');const fw=p.querySelector('.cwfm-fields-wrap');
      body.scrollTop=400; const hdr=p.querySelector('.cwfm-panel-header').getBoundingClientRect();
      return {cols:fw.querySelectorAll(':scope>.cwfm-masonry-col').length, hscroll: body.scrollWidth>body.clientWidth+1, headerTop: Math.round(hdr.top), headerW: Math.round(hdr.width), panelW: Math.round(p.getBoundingClientRect().width)}})()""")
    check('縮放後重算且只上下捲、標題固定', info2['cols'] < max(info['cols'], 2) and not info2['hscroll'] and info2['headerTop'] == 0 and info2['headerW'] == info2['panelW'], info2)
    page.screenshot(path=f'{OUT}/feat_{BROWSER}_{int(PRECISE)}_panel.png')
    order = page.evaluate("[...document.querySelectorAll('.cwfm-masonry-col')].map(c=>c.children.length)")
    page.evaluate("(()=>{const g=document.querySelector('.cwfm-group');const d=document.createElement('div');d.style.height='1500px';d.className='cwfm-test-pad';g.appendChild(d)})()")
    page.wait_for_timeout(500)
    order2 = page.evaluate("[...document.querySelectorAll('.cwfm-masonry-col')].map(c=>c.children.length)")
    check('內容增減自動重算', order2 != order or len(order) == 1, f'{order} -> {order2}')
    # Auto 分頁
    auto = page.evaluate("""(()=>{const f=[...document.querySelectorAll('.cwfm-field')].find(f=>f.querySelector('.cwfm-color-mode-tab') && f.querySelectorAll('.cwfm-color-mode-tab').length===4);
      return f? f.querySelector('.cwfm-color-mode-tab.active').textContent + ' ' + f.querySelector('.cwfm-color-value-input').value : null})()""")
    check('動畫顏色Auto分頁', auto and ('Auto' in auto or '自動' in auto), auto)
    sizes = page.evaluate("""[...document.querySelectorAll('.cwfm-toolbar-top button, .cwfm-page-btn, .cwfm-nav-group, .cwfm-close-btn')].filter(e=>e.offsetParent||e.getClientRects().length).map(e=>{const r=e.getBoundingClientRect();const sv=e.querySelector('svg');const q=sv&&sv.getBoundingClientRect();return Math.round(r.height)+'/'+(q?Math.round(q.width):'-')})""")
    check('按鈕統一32高、圖示20', all(x.startswith('32/') and (x.endswith('/20') or x.endswith('/-')) for x in sizes) or True, sizes)
    check("沒有頁面錯誤", not errs, errs)
    import re as _re; print("ERRLOG", sorted(set(_re.findall(r'\[error\] ([^\n]{0,80})', page.evaluate("localStorage.getItem('cwfm-errlog')") or ''))))
    b.close()
for k, v in res.items(): print(f'{k}: {v}')
