# v1.85.0：新書開啟時套用（文字書籍／圖片書籍各選一個設定檔）、圖片書預設依長寬比、文字書插頁與書名頁、
#          翻頁設定小標題與精準定位移入、「閱讀行為」改名「閱讀紀錄」、開始頁在可見範圍置中
# 用法：CWFM_EPUB=<純圖片 EPUB> python3 ft185.py <dp.html> <dr.js> <瀏覽器>
import sys, os, json, re
exec(open('ft180.py').read().split("with sync_playwright() as p:")[0])
TEXT_EPUB = EPUB
IMG_EPUB = __import__('make_image_epub').default_image_epub()  # v1.87.0：預設現場產生測試用圖片書，CWFM_EPUB 可指定真書
OUT_DIR = os.environ.get('OUT_DIR', '/tmp')
V = "document.querySelector('foliate-view')"
S = "window.__cwfm.settings"
LS = "JSON.parse(localStorage.getItem('cwfm-settings')||'{}')"
SETBTN = 'button[aria-label="設定"], button[aria-label="Settings"]'


def open_panel(pg):
    pg.click(SETBTN, force=True); pg.wait_for_timeout(700)


def close_panel(pg):
    pg.evaluate("document.querySelector('.cwfm-settings-panel .cwfm-panel-header .cwfm-close-btn')?.click()"); pg.wait_for_timeout(400)


def forget_book(pg):  # 測試伺服器所有書同一個書號：刪掉這本書的紀錄，下一次開就是「新書」
    pg.evaluate("(()=>{const s=JSON.parse(localStorage.getItem('cwfm-settings')||'{}');delete (s.bookSettings||{})['%d'];localStorage.setItem('cwfm-settings',JSON.stringify(s))})()" % BOOK_ID)


with sync_playwright() as p:
    BR = sys.argv[3]; b = getattr(p, BR).launch()
    errs = []

    def page(ctx):
        pg = ctx.new_page()
        pg.on('pageerror', lambda e: errs.append(str(e)[:300]))
        pg.on('console', lambda m: errs.append(m.text[:300]) if m.type == 'error' and 'lock initial anchor' not in m.text and '初始鎖定' not in m.text and '404' not in m.text else None)
        pg.goto(URL); pg.wait_for_timeout(4500)
        return pg

    # ---------- 1. 面板：分組名稱、小標題、精準定位位置、新書開啟時套用 ----------
    ctx = b.new_context(viewport={'width': 1200, 'height': 800}, locale='zh-TW')
    EPUB = TEXT_EPUB
    pg = page(ctx)
    open_panel(pg)
    titles = pg.evaluate("[...document.querySelectorAll('.cwfm-settings-panel .cwfm-group-title')].map(e=>e.textContent.trim())")
    check('「閱讀行為」改名「閱讀紀錄」', '閱讀紀錄' in titles and '閱讀行為' not in titles, titles)
    order = pg.evaluate("""(()=>{const g=[...document.querySelectorAll('.cwfm-settings-panel .cwfm-group')].find(g=>g.querySelector('.cwfm-group-title').textContent.trim()==='翻頁設定');
        return [...g.querySelectorAll('.cwfm-subhead, .cwfm-field > label, .cwfm-field .cwfm-checkbox-row > label:first-child, .cwfm-field .cwfm-color-row label')].map(e=>e.textContent.trim()).filter(Boolean)})()""")
    want = ['翻頁方式', '翻頁方向', '優先套用書籍標示', '反轉點擊區', '翻頁精準定位', '左右點擊區']
    check('翻頁設定：翻頁方式（方向、反轉、精準定位）→ 左右點擊區', [next((w for w in want if o.startswith(w)), None) for o in order][:6] == want, order)
    rec = pg.evaluate("""(()=>{const g=[...document.querySelectorAll('.cwfm-settings-panel .cwfm-group')].find(g=>g.querySelector('.cwfm-group-title').textContent.trim()==='閱讀紀錄');return g.textContent})()""")
    check('閱讀紀錄裡沒有精準定位', '精準定位' not in rec)
    nb = pg.evaluate("""(()=>{const n=document.querySelector('.cwfm-settings-panel .cwfm-newbook');if(!n)return null;
        return [n.querySelector('.cwfm-newbook-title').textContent, [...n.querySelectorAll('select')].map(s=>[s.value,[...s.options].map(o=>o.textContent)]), n.querySelectorAll('svg').length, getComputedStyle(n).display]})()""")
    check('設定檔分組裡常駐「新書開啟時套用」：兩個選單、預設內建、有圖示', nb and nb[0] == '新書開啟時套用' and [x[0] for x in nb[1]] == ['builtin:text', 'builtin:image'] and nb[1][0][1] == ['文字書（內建）', '圖片書（內建）'] and nb[2] == 2 and nb[3] != 'none', nb)
    check('設定檔不再有分隔線', pg.evaluate("!document.querySelector('.cwfm-settings-panel .cwfm-keylist-sep')"))
    pg.screenshot(path=f'{OUT_DIR}/v185_panel_{BR}.png')
    # 存一個自訂設定檔（兩欄、字級 150），指定給文字書籍
    pg.evaluate(f"{S}.maxColumnCount=1; {S}.fontSize=150")
    pg.evaluate("[...document.querySelectorAll('.cwfm-settings-panel .cwfm-keychip-add')].find(b=>/設定檔/.test(b.textContent)).click()"); pg.wait_for_timeout(400)
    pg.fill('.cwfm-confirm-overlay input', '我的小說'); pg.keyboard.press('Enter'); pg.wait_for_timeout(600)
    opts = pg.evaluate("[...document.querySelectorAll('.cwfm-newbook select')][0].options.length")
    check('新增設定檔後選單立刻多一個選項', opts == 3, opts)
    pg.evaluate("(()=>{const s=document.querySelectorAll('.cwfm-newbook select')[0];s.value=[...s.options].find(o=>o.textContent==='我的小說').value;s.dispatchEvent(new Event('change'))})()"); pg.wait_for_timeout(300)
    ref = (pg.evaluate(LS).get('newBookProfile') or {}).get('text', '')
    check('指定存進 newBookProfile', ref.startswith('theme:'), ref)
    close_panel(pg)
    # 改回別的值，讓下一本新書能看出是套用設定檔
    pg.evaluate(f"{S}.fontSize=100; {S}.maxColumnCount=2"); forget_book(pg); pg.close()

    pg = page(ctx)
    v = pg.evaluate(f"[{S}.fontSize, {S}.maxColumnCount]")
    check('新文字書套用指定的自訂設定檔「我的小說」', v == [150, 1], v)
    # 刪掉這個設定檔 → 選單退回內建
    open_panel(pg)
    pg.evaluate("[...document.querySelectorAll('.cwfm-settings-panel .cwfm-keychip')].find(c=>c.textContent.includes('我的小說')).querySelector('.cwfm-keychip-remove').click()"); pg.wait_for_timeout(400)
    pg.click('.cwfm-confirm-overlay .cwfm-ok-primary, .cwfm-confirm-overlay button.cwfm-confirm-ok'); pg.wait_for_timeout(500)
    sv = pg.evaluate("document.querySelectorAll('.cwfm-newbook select')[0].value")
    check('指定的設定檔刪掉後，選單顯示退回內建', sv == 'builtin:text', sv)
    close_panel(pg)

    # ---------- 2. 文字書插頁：書名頁、空白頁 ----------
    open_panel(pg)
    pg.evaluate("[...document.querySelectorAll('.cwfm-settings-panel label')].find(l=>l.textContent==='在全書最前面補一頁').parentElement.querySelector('input').click()"); pg.wait_for_timeout(1800)
    close_panel(pg)
    pg.evaluate(f"{V}.goTo(0)"); pg.wait_for_timeout(1500)
    st = pg.evaluate(f"(()=>{{const d={V}.renderer.getContents()[0].doc;const s=d.querySelector('cwfm-ins.cwfm-ins-start');return s?[s.querySelector('.cwfm-ib-title').textContent, !!s.querySelector('button')]:null}})()")
    check('文字書：第一章前面多一頁書名頁（沒有按鈕）', st == ['測試書名', False], st)
    pg.wait_for_timeout(1500)
    check('書名頁不算位置：閱讀進度記的是第一章開頭（不是書名頁）', re.match(r'epubcfi\(/6/2!/4[,/]', STATE['bookmark'] or '') is not None, STATE['bookmark'])
    pg.screenshot(path=f'{OUT_DIR}/v185_textstart_{BR}.png')
    bm = list(STATE['bookmarks'].values())
    # 翻幾頁，在這頁前插空白頁
    for _ in range(2): pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(600)
    before = pg.evaluate(FIRST)
    open_panel(pg)
    lab = pg.evaluate("[...document.querySelectorAll('.cwfm-settings-panel label')].find(l=>/這頁前/.test(l.textContent)).textContent")
    check('文字書：插頁按鈕可用、顯示插入', lab == '在這頁前插入空白頁', lab)
    pg.evaluate("[...document.querySelectorAll('.cwfm-settings-panel label')].find(l=>/這頁前/.test(l.textContent)).parentElement.querySelector('button').click()"); pg.wait_for_timeout(2000)
    lab2 = pg.evaluate("[...document.querySelectorAll('.cwfm-settings-panel label')].find(l=>/這頁前/.test(l.textContent)).textContent")
    close_panel(pg)
    blank = pg.evaluate(f"!!{V}.renderer.getContents()[0].doc.querySelector('cwfm-ins.cwfm-ins-blank')")
    check('插入後章節裡多一個空白頁、按鈕變移除', blank and lab2 == '移除這頁前的空白頁', [blank, lab2])
    after = pg.evaluate(FIRST)
    check('插入後停在原本那頁（空白頁在它前面）', after == before, [before, after])
    pg.keyboard.press('ArrowLeft'); pg.wait_for_timeout(800)
    vis = pg.evaluate("window.__cwfm.insertState()")
    check('往前翻一頁就是空白頁（按鈕仍是移除）', vis == {'can': True, 'has': True}, vis)
    pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(800)
    ls = pg.evaluate(LS)
    bb = ((ls.get('bookSettings') or {}).get(str(BOOK_ID)) or {}).get('b') or {}
    check('文字書記住：補一頁＋一個插入點（原書 CFI）', bb.get('frontInsert') is True and len(bb.get('textInserts') or []) == 1 and bb['textInserts'][0].startswith('epubcfi('), bb)
    pg.close()
    pg = page(ctx)
    # v1.87.1：重開時依閱讀進度回到插入點那頁（插在段落中間時，CFI 落在切開的文字節點切口；Firefox 以前會停在前一頁）
    reopen = pg.evaluate(FIRST)
    check('重開文字書：回到插入空白頁後的那一頁', reopen == after, [after, reopen])
    again = pg.evaluate(f"(async()=>{{const v={V};await v.goTo(0);return !!v.renderer.getContents()[0].doc.querySelector('cwfm-ins.cwfm-ins-start')}})()")
    check('重開文字書：書名頁還在', again)
    pg.close()
    ctx.close()

    # ---------- 3. 圖片書：留白 0、開始頁在可見範圍置中；直向畫面預設 1 欄 ----------
    EPUB = IMG_EPUB
    ctx = b.new_context(viewport={'width': 1200, 'height': 800}, locale='zh-TW')
    pg = page(ctx)
    i = pg.evaluate(f"[{S}.maxColumnCount,{S}.leftRightPadding,{S}.topBottomPadding,{S}.columnGapPx,{S}.horizontalSizeMode,{S}.verticalSizeMode,{S}.tapZoneVisible,{S}.pageDirection,{S}.reverseTapZones,{V}.book.dir]")
    check('圖片書內建預設（v1.86.0）：橫向 2 欄、上下左右留白 0、欄間距 0、留白優先、點擊區顯示、右翻、反轉點擊區', i == [2, 0, 0, 0, 'margin', 'margin', True, 'rtl', True, 'rtl'], i)
    pg.evaluate("window.__cwfm.setFrontInsert(true)"); pg.wait_for_timeout(1800)
    pg.evaluate(f"{V}.goTo('epubcfi(/6/4!/4)')"); pg.wait_for_timeout(1500)
    pg.wait_for_timeout(1500)  # 等紙色算完
    c = pg.evaluate(f"""(()=>{{const d={V}.renderer.getContents()[0].doc;const fr=d.defaultView.frameElement.getBoundingClientRect();
        const pp=d.querySelector('.cwfm-ib-start .cwfm-ib-paper').getBoundingClientRect();const bt=d.querySelector('.cwfm-ib-start .cwfm-ib-title').getBoundingClientRect();
        const im=d.querySelector('.cwfm-ib-img').getBoundingClientRect();
        return {{paper:[pp.left+fr.left,pp.right+fr.left,pp.top,pp.bottom],btn:(bt.left+bt.right)/2+fr.left,col:[im.left+fr.left,im.right+fr.left,im.top,im.bottom],
          bg:getComputedStyle(d.querySelector('.cwfm-ib-paper')).backgroundColor,border:getComputedStyle(d.querySelector('.cwfm-ib-paper')).borderTopWidth,
          paperColor:window.__cwfm.bookState.paperColor}}}})()""")
    W = c['paper'][1] - c['paper'][0]; H = c['paper'][3] - c['paper'][2]
    colH = c['col'][3] - c['col'][2]
    check('開始頁的紙跟後面那頁畫出來一樣大（寬≈高×0.69、高＝欄高）、貼著書脊', abs(H - colH) <= 1 and abs(W - H * 1650 / 2390) <= 2 and min(abs(c['paper'][1] - 600), abs(c['paper'][0] - 600)) <= 1, c)
    check('書名在紙的正中央', abs(c['btn'] - (c['paper'][0] + c['paper'][1]) / 2) <= 1, c)
    check('紙色從內頁判斷（不是封面）、有細框', isinstance(c['paperColor'], str) and c['paperColor'].startswith('#') and c['border'] == '1px', c)
    pg.screenshot(path=f'{OUT_DIR}/v185_imgstart_{BR}.png')
    pg.close(); ctx.close()
    ctx = b.new_context(viewport={'width': 600, 'height': 900}, locale='zh-TW')
    pg = page(ctx)
    i = pg.evaluate(f"[{S}.maxColumnCount, {V}.book.sections[0].cwfmSeg.items.length]")
    check('直向畫面：圖片書預設 1 欄（分段 12 頁）', i == [1, 12], i)
    pg.screenshot(path=f'{OUT_DIR}/v185_portrait_{BR}.png')
    pg.close(); ctx.close()

    # ---------- 4. 圖片書籍指定自訂設定檔 ----------
    ctx = b.new_context(viewport={'width': 1200, 'height': 800}, locale='zh-TW')
    pg = ctx.new_page(); pg.goto(BASE + '/x')
    pg.evaluate("localStorage.setItem('cwfm-settings', JSON.stringify({savedThemes:[{id:'t1',name:'漫畫三欄',values:{maxColumnCount:3,leftRightPadding:8}}],newBookProfile:{image:'theme:t1'}}))")
    pg.close()
    pg = page(ctx)
    i = pg.evaluate(f"[{S}.maxColumnCount, {S}.leftRightPadding, {V}.book.sections[0].cwfmSeg.items.length]")
    check('圖片書籍指定「漫畫三欄」：新圖片書 3 欄、分段 12 頁（3 的倍數）', i == [3, 8, 12], i)
    pg.close(); ctx.close()
    b.close()
check('沒有頁面錯誤', not errs, errs)
