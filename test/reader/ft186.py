# v1.86.0：翻頁方向改一般設定＋「優先套用書籍標示的翻頁方向」、圖片書預設右翻＋反轉＋上下留白 0、
#          虛擬頁紙色不受閱讀配色影響（沒有統一紙色＝白紙黑字）、扉頁方案甲（整組中心 44%，沒有出版社位置不變）、
#          「插頁設定」改名＋分隔線、〔清除〕紅框、「新書開啟時套用」上下堆疊不換行、自動隱藏說明含觸控
# 用法：CWFM_EPUB=<純圖片 EPUB> python3 ft186.py <dp.html> <dr.js> <瀏覽器>
import sys, os, json, re, io, zipfile
exec(open('ft180.py').read().split("with sync_playwright() as p:")[0])
TEXT_EPUB = EPUB
IMG_EPUB = __import__('make_image_epub').default_image_epub()  # v1.87.0：預設現場產生測試用圖片書，CWFM_EPUB 可指定真書
OUT_DIR = os.environ.get('OUT_DIR', '/tmp')
V = "document.querySelector('foliate-view')"
S = "window.__cwfm.settings"
SETBTN = 'button[aria-label="設定"], button[aria-label="Settings"]'


def with_opf(epub, fn):  # 改圖片書的 OPF（加翻頁方向標示、拿掉出版社）
    src = zipfile.ZipFile(io.BytesIO(epub)); buf = io.BytesIO(); dst = zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED)
    for it in src.infolist():
        data = src.read(it.filename)
        if it.filename.endswith('.opf'): data = fn(data.decode('utf-8')).encode('utf-8')
        dst.writestr(it, data, compress_type=zipfile.ZIP_STORED if it.filename == 'mimetype' else zipfile.ZIP_DEFLATED)
    dst.close(); return buf.getvalue()


def open_panel(pg):
    pg.click(SETBTN, force=True); pg.wait_for_timeout(700)


def close_panel(pg):
    pg.evaluate("document.querySelector('.cwfm-settings-panel .cwfm-panel-header .cwfm-close-btn')?.click()"); pg.wait_for_timeout(400)


with sync_playwright() as p:
    BR = sys.argv[3]; b = getattr(p, BR).launch()
    errs = []

    def page(ctx, settings=None):
        pg = ctx.new_page()
        pg.on('pageerror', lambda e: errs.append(str(e)[:300]))
        pg.on('console', lambda m: errs.append(m.text[:300]) if m.type == 'error' and 'lock initial anchor' not in m.text and '初始鎖定' not in m.text and '404' not in m.text else None)
        if settings is not None:
            pg.add_init_script("localStorage.setItem('cwfm-settings', %s)" % json.dumps(json.dumps(settings)))
        pg.goto(URL); pg.wait_for_timeout(4500)
        return pg

    def tp_geom(pg):
        return pg.evaluate(f"""(()=>{{const d={V}.renderer.getContents()[0].doc;const pp=d.querySelector('.cwfm-ib-start .cwfm-ib-paper');const pr=pp.getBoundingClientRect();
            const g=pp.querySelector('.cwfm-tp-grp').getBoundingClientRect();const t=pp.querySelector('.cwfm-ib-title');const pub=pp.querySelector('.cwfm-tp-pub');
            const cs=d.defaultView.getComputedStyle(pp);return {{gc:((g.top+g.bottom)/2-pr.top)/pr.height, title:t.getBoundingClientRect().top-pr.top, tsize:parseFloat(d.defaultView.getComputedStyle(t).fontSize), w:pr.width,
              pubVis:d.defaultView.getComputedStyle(pub).visibility, bg:cs.backgroundColor, ink:d.defaultView.getComputedStyle(t).color}}}})()""")

    # ---------- 1. 圖片書＋墨金配色（黑底黃字）：虛擬頁仍是白紙黑字；扉頁甲 ----------
    EPUB = IMG_EPUB
    ctx = b.new_context(viewport={'width': 1200, 'height': 800}, locale='zh-TW')
    OG = {'activeColorTheme': 'old_gold', 'themeName': 'custom', 'customTextColor': '#e8c66a', 'customBackgroundColor': '#111111', 'customTextColorEnabled': True, 'customBackgroundColorEnabled': True}
    # v1.87.0：設定值屬於設定檔，用「新書開啟時套用」指定一個墨金配色的圖片書設定檔
    IMGLAY = {'flow': 'paginated', 'horizontalSizeMode': 'margin', 'verticalSizeMode': 'margin', 'leftRightPadding': 0, 'topBottomPadding': 0, 'columnGapPx': 0,
             'maxColumnCount': 2, 'pageDirection': 'rtl', 'preferBookDirection': True, 'reverseTapZones': True}  # 同內建圖片書的排版（扉頁位置要跟下面用內建開的那次比）
    pg = page(ctx, {'savedThemes': [{'id': 'G', 'name': 'G', 'values': {**OG, **IMGLAY}}], 'newBookProfile': {'image': 'theme:G'}})
    check('墨金設定檔有套用到圖片書', pg.evaluate(f"{S}.customBackgroundColor") == '#111111', pg.evaluate(f"{S}.customBackgroundColor"))
    pg.evaluate("window.__cwfm.setFrontInsert(true)"); pg.wait_for_timeout(1800)
    pg.evaluate(f"{V}.goTo('epubcfi(/6/4!/4)')"); pg.wait_for_timeout(2500)
    g = tp_geom(pg)
    check('墨金配色下：虛擬頁仍是白紙（紙色判斷）＋黑字', g['bg'] == 'rgb(255, 255, 255)' and g['ink'] in ('rgb(34, 34, 34)',), g)
    check('扉頁甲：整組（含出版社）中心在紙高 44%', abs(g['gc'] - 0.44) <= 0.01, g)
    check('書名字級依紙寬等比（486px 寬 → 60px）', abs(g['tsize'] - 60 * min(1.4, max(0.5, g['w'] / 486))) <= 0.6, g)
    with_pub = g
    pg.screenshot(path=f'{OUT_DIR}/v186_tp_oldgold_{BR}.png')
    # 紙色算不出來（none）：一樣白紙黑字
    pg.evaluate(f"window.__cwfm.bookState.paperColor='none'; {V}.renderer.getContents().forEach(c=>c.doc.documentElement.style.removeProperty('--cwfm-paper'))"); pg.wait_for_timeout(300)
    g2 = tp_geom(pg)
    check('沒有統一紙色（none）：白紙黑字，不跟閱讀配色', g2['bg'] == 'rgb(255, 255, 255)' and g2['ink'] == 'rgb(34, 34, 34)', g2)
    pg.close(); ctx.close()

    # 沒有出版社：出版社隱藏、上面位置不變
    EPUB = with_opf(IMG_EPUB, lambda o: re.sub(r'<dc:publisher>[^<]*</dc:publisher>', '', o))
    ctx = b.new_context(viewport={'width': 1200, 'height': 800}, locale='zh-TW')
    pg = page(ctx, {'savedThemes': [{'id': 'G', 'name': 'G', 'values': {**OG, **IMGLAY}}], 'newBookProfile': {'image': 'theme:G'}})  # 跟上面同一組設定，只差有沒有出版社
    pg.evaluate("window.__cwfm.setFrontInsert(true)"); pg.wait_for_timeout(1800)
    pg.evaluate(f"{V}.goTo('epubcfi(/6/4!/4)')"); pg.wait_for_timeout(2500)
    g3 = tp_geom(pg)
    check('沒有出版社：出版社那行隱藏、書名位置跟有出版社時一樣', g3['pubVis'] == 'hidden' and abs(g3['title'] - with_pub['title']) <= 1, [g3, with_pub['title']])
    pg.close(); ctx.close()

    # ---------- 2. 翻頁方向：書有標示 ltr、優先套用書籍標示 ----------
    EPUB = with_opf(IMG_EPUB, lambda o: o.replace('<spine ', '<spine page-progression-direction="ltr" ', 1))
    ctx = b.new_context(viewport={'width': 1200, 'height': 800}, locale='zh-TW')
    pg = page(ctx)
    d = pg.evaluate(f"[{V}.book.dir, {S}.pageDirection, {S}.preferBookDirection]")
    check('書標示左翻＋優先套用書籍標示（預設開）→ 左翻，設定值仍是右翻', d == ['ltr', 'rtl', True], d)
    open_panel(pg)
    sel = pg.evaluate("""(()=>{const s=[...document.querySelectorAll('.cwfm-settings-panel select')].find(s=>[...s.options].some(o=>o.value==='rtl'));
        return [s.value, s.disabled, s.parentElement.querySelector('.cwfm-field-hint').textContent]})()""")
    check('選單停用、顯示「依書籍標示：左翻」', sel[0] == 'ltr' and sel[1] is True and sel[2].startswith('依書籍標示'), sel)
    pg.evaluate("[...document.querySelectorAll('.cwfm-settings-panel label')].find(l=>l.textContent==='優先套用書籍標示的翻頁方向').parentElement.querySelector('input').click()"); pg.wait_for_timeout(2000)
    d = pg.evaluate(f"[{V}.book.dir, [...document.querySelectorAll('.cwfm-settings-panel select')].find(s=>[...s.options].some(o=>o.value==='rtl')).disabled]")
    check('關掉優先套用 → 改用設定的右翻、選單可用', d == ['rtl', False], d)
    close_panel(pg); pg.close(); ctx.close()

    # 舊版（v1.85）單獨記在書上的方向：照舊
    EPUB = IMG_EPUB
    ctx = b.new_context(viewport={'width': 1200, 'height': 800}, locale='zh-TW')
    pg = page(ctx, {'bookSettings': {str(BOOK_ID): {'v': {'maxColumnCount': 2}, 'b': {'pageDirection': 'ltr'}, 't': 1}}})
    d = pg.evaluate(f"[{V}.book.dir, {S}.pageDirection, {S}.preferBookDirection]")
    # v1.87.0：設定值屬於設定檔（共用），舊方向只決定這本書實際的方向，不寫進設定值
    check('v1.85 記住的方向（左翻）升級後照舊（設定值仍是設定檔的右翻）', d == ['ltr', 'rtl', True], d)
    pg.close(); ctx.close()

    # ---------- 3. 面板：插頁設定、分隔線、紅框、新書套用不換行、自動隱藏說明 ----------
    EPUB = TEXT_EPUB
    ctx = b.new_context(viewport={'width': 1200, 'height': 800}, locale='zh-TW')
    pg = page(ctx)
    open_panel(pg)
    titles = pg.evaluate("[...document.querySelectorAll('.cwfm-settings-panel .cwfm-group-title')].map(e=>e.textContent.trim())")
    check('分組改名「插頁設定」', '插頁設定' in titles and '是否插頁' not in titles, titles)
    div = pg.evaluate("""(()=>{const l=[...document.querySelectorAll('.cwfm-settings-panel label')].find(l=>/這頁前/.test(l.textContent));const f=l.closest('.cwfm-field');
        const prev=f.previousElementSibling;return [prev.classList.contains('cwfm-field-no-divider'), getComputedStyle(prev,'::after').display, getComputedStyle(prev,'::after').content]})()""")
    check('「補一頁」與「插入空白頁」之間有分隔線（欄位的 ::after 分隔線沒被關掉）', div[0] is False and div[1] != 'none', div)
    btn = pg.evaluate("""(()=>{const b=[...document.querySelectorAll('.cwfm-settings-panel button')].find(b=>b.textContent==='清除'&&b.closest('.cwfm-checkbox-row'));
        const e=[...document.querySelectorAll('.cwfm-settings-panel button')].find(b=>b.textContent==='清除記錄');const c=x=>{const s=getComputedStyle(x);return [s.color,s.borderTopColor]};return [c(b), e?c(e):null, b.className]})()""")
    check('〔清除〕跳轉紀錄是紅框（跟〔清除記錄〕同色）', btn[2] == 'cwfm-btn-danger-outline' and (btn[1] is None or btn[0] == btn[1]), btn)
    # 窄面板（截圖情境約 260px 卡片）：名稱一行、選單一行、名稱不換行；說明與第一項之間沒有分隔線
    pg.set_viewport_size({'width': 760, 'height': 800}); pg.wait_for_timeout(800)
    nb = pg.evaluate("""(()=>{const n=document.querySelector('.cwfm-newbook');const rows=[...n.querySelectorAll('.cwfm-newbook-row')];
        return {w:n.getBoundingClientRect().width, lab:rows.map(r=>{const l=r.querySelector('label');const tn=[...l.childNodes].find(n=>n.nodeType===3);const rg=document.createRange();rg.selectNodeContents(tn);return new Set([...rg.getClientRects()].map(x=>Math.round(x.top))).size}), stacked:rows.map(r=>r.querySelector('select').getBoundingClientRect().top>r.querySelector('label').getBoundingClientRect().bottom-1),
          firstBorder:getComputedStyle(rows[0]).borderTopStyle, secondBorder:getComputedStyle(rows[1]).borderTopStyle}})()""")
    check('新書開啟時套用：名稱一行不換行、選單在下一行；只有兩項之間有分隔線', max(nb['lab']) == 1 and all(nb['stacked']) and nb['firstBorder'] == 'none' and nb['secondBorder'] == 'solid', nb)
    pg.evaluate("document.querySelector('.cwfm-newbook').scrollIntoView({block:'center'})"); pg.wait_for_timeout(300)
    pg.screenshot(path=f'{OUT_DIR}/v186_newbook_{BR}.png')
    # 滑桿：拖動中每格不再同步重排（handler 立刻返回）、重排次數被合併；放開（change）套用最終值並存檔
    pg.set_viewport_size({'width': 1200, 'height': 800}); pg.wait_for_timeout(600)
    sl = pg.evaluate("""(async()=>{const sl=[...document.querySelectorAll('.cwfm-settings-panel input[type=range]')].find(x=>/字級/.test(x.closest('.cwfm-field').querySelector('label').textContent));
        const orig=window.__cwfm.applySettings; let n=0; const v0=window.__cwfm.settings.fontSize;
        const saved0=JSON.parse(localStorage.getItem('cwfm-settings')||'{}').fontSize;
        const ts=[];for(let i=1;i<=12;i++){sl.value=String(100+i*10);const t=performance.now();sl.dispatchEvent(new Event('input',{bubbles:true}));ts.push(performance.now()-t);await new Promise(r=>setTimeout(r,16));}
        const midSaved=JSON.parse(localStorage.getItem('cwfm-settings')||'{}').fontSize;
        sl.dispatchEvent(new Event('change',{bubbles:true}));await new Promise(r=>setTimeout(r,400));
        const st=document.querySelector('.cwfm-settings-panel');
        return {maxInput:Math.max(...ts), shown:sl.closest('.cwfm-field').querySelector('.cwfm-value-input').value, setting:window.__cwfm.settings.fontSize,
          savedMid:midSaved, saved0, savedEnd:(()=>{const st=JSON.parse(localStorage.getItem('cwfm-settings')||'{}');const ref=st.bookSettings?.['%d']?.profile||'';
            return (st.savedThemes||[]).find(x=>'theme:'+x.id===ref)?.values?.fontSize})()}})()""" % BOOK_ID)
    check('滑桿拖動：每格處理 < 15ms（不同步重排）、數字即時跟著走、放開後套用並存檔最終值', sl['maxInput'] < 15 and sl['shown'] == '220' and sl['setting'] == 220 and sl['savedEnd'] == 220, sl)
    ah = pg.evaluate("[...document.querySelectorAll('.cwfm-settings-panel label')].find(l=>/自動隱藏工具列/.test(l.textContent)).textContent")
    check('自動隱藏工具列說明提到手指點一下', '手指' in ah, ah)
    pg.close(); ctx.close()
    b.close()
check('沒有頁面錯誤', not errs, errs)
