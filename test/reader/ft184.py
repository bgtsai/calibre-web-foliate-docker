# v1.84.0：圖片書多欄並排、翻頁方向、反轉點擊區、插頁、內建設定檔、設定跟著書、「上一步」動畫方案 E
# 用法：CWFM_EPUB=<純圖片 EPUB> python3 ft184.py <dp.html> <dr.js> <瀏覽器>
#   CWFM_EPUB 預設 /home/claude/testbook/manga30.epub（「日本兄弟」修剪成約 30 頁：cover＋29 頁，每頁一張圖，
#   cover 與第 1 頁同一張圖、沒有標翻頁方向）。截圖寫到 OUT_DIR（預設 /tmp）。
import sys, os, json
exec(open('ft180.py').read().split("with sync_playwright() as p:")[0])
TEXT_EPUB = EPUB
IMG_EPUB = open(os.environ.get('CWFM_EPUB', '/home/claude/testbook/manga30.epub'), 'rb').read()
OUT_DIR = os.environ.get('OUT_DIR', '/tmp')
V = "document.querySelector('foliate-view')"
CFI = V + ".lastLocation.cfi"
LS = "JSON.parse(localStorage.getItem('cwfm-settings')||'{}')"


def orig_index(cfi):  # epubcfi(/6/N!/4) → 原書章節序號
    import re
    m = re.match(r'epubcfi\(/6/(\d+)', cfi or '')
    return int(m.group(1)) // 2 - 1 if m else -1


def open_panel(pg):
    pg.click('button[aria-label="設定"], button[aria-label="Settings"]', force=True); pg.wait_for_timeout(700)


def close_panel(pg):
    pg.evaluate("document.querySelector('.cwfm-settings-panel .cwfm-panel-header button')?.click()"); pg.wait_for_timeout(400)


with sync_playwright() as p:
    BR = sys.argv[3]; b = getattr(p, BR).launch()
    ctx = b.new_context(viewport={'width': 1200, 'height': 800}, locale='zh-TW')
    # v1.86.0 起內建「圖片書」預設右翻＋反轉點擊區；這支測 v1.84 的功能（左翻開始、再手動改右翻），先把內建圖片書覆蓋回左翻
    ctx.add_init_script("if(!sessionStorage.getItem('s')&&!localStorage.getItem('cwfm-seeded')){localStorage.setItem('cwfm-settings',JSON.stringify({builtinProfiles:{image:{pageDirection:'ltr',reverseTapZones:false}}}));localStorage.setItem('cwfm-seeded','1')}")
    errs = []

    def page():
        pg = ctx.new_page()
        pg.on('pageerror', lambda e: errs.append(str(e)[:300]))
        pg.on('console', lambda m: errs.append(m.text[:300]) if m.type == 'error' and 'lock initial anchor' not in m.text and '初始鎖定' not in m.text and '404' not in m.text else None)
        pg.goto(URL); pg.wait_for_timeout(4500)
        return pg

    # ---------- 1. 圖片書判斷、分段、兩欄並排 ----------
    EPUB = IMG_EPUB
    pg = page()
    info = pg.evaluate(f"(()=>{{const v={V};return {{img:!!window.__cwfm.imageBook,ids:v.book.sections.map(s=>s.id),dir:v.book.dir,cols:window.__cwfm.settings.maxColumnCount,lr:window.__cwfm.settings.leftRightPadding,gap:window.__cwfm.settings.columnGapPx}}}})()")
    check('判斷為圖片書', info['img'], info)
    check('略過重複封面、每段 12 頁（30 頁 → 3 段）', info['ids'] == ['cwfm-seg-0-1', 'cwfm-seg-1-13', 'cwfm-seg-2-25'], info['ids'])
    check('第一次開圖片書套內建「圖片書」：橫向畫面兩欄、左右留白 0、欄間距 0', info['cols'] == 2 and info['lr'] == 0 and info['gap'] == 0, info)
    check('沒有標示翻頁方向 → 預設左翻', info['dir'] == 'ltr', info['dir'])
    vis = pg.evaluate(f"(()=>{{const d={V}.renderer.getContents()[0].doc;const fr=d.defaultView.frameElement.getBoundingClientRect();return [...d.querySelectorAll('.cwfm-ib-p')].map(e=>{{const r=e.getBoundingClientRect();return [e.dataset.orig, Math.round(r.left+fr.left)]}}).filter(x=>x[1]>=0&&x[1]<1180)}})()")
    check('畫面上並排兩頁（第 1、2 頁，左→右）', [v[0] for v in vis] == ['1', '2'] and vis[0][1] < vis[1][1], vis)
    spread = pg.evaluate(f"{V}.renderer.getContents()[0].doc.documentElement.classList.contains('cwfm-ib-spread')")
    check('兩欄並排時圖片靠書脊（.cwfm-ib-spread）', spread)
    pg.screenshot(path=f'{OUT_DIR}/v184_spread_{BR}.png')
    check('開書位置是原書第 1 頁的 CFI', orig_index(pg.evaluate(CFI)) == 1, pg.evaluate(CFI))
    for _ in range(6): pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(500)
    pg.wait_for_timeout(600)
    c = pg.evaluate(CFI)
    check('翻 6 次（跨到第二段）→ 原書第 13 頁', orig_index(c) == 13, c)
    pg.wait_for_timeout(1500)
    check('閱讀進度存原書座標', orig_index(STATE['bookmark']) == 13, STATE['bookmark'])
    pg.keyboard.press('ArrowLeft'); pg.wait_for_timeout(800)
    check('往回翻跨回第一段 → 第 11 頁', orig_index(pg.evaluate(CFI)) == 11, pg.evaluate(CFI))
    # 書籤：存原書座標，跳得回來
    pg.click(BMB if 'BMB' in globals() else 'button[aria-label="加入書籤"]'); pg.wait_for_timeout(300)
    pg.click('.cwfm-bm-dialog .cwfm-ok-primary'); pg.wait_for_timeout(1200)
    bms = list(STATE['bookmarks'].values())
    bm = [x for x in bms if orig_index(x.get('cfi')) == 11]
    check('加書籤：CFI 是原書第 11 頁', len(bm) == 1, [x.get('cfi') for x in bms])
    pg.evaluate(f"{V}.goTo('epubcfi(/6/56!/4)')"); pg.wait_for_timeout(1200)
    check('用原書 CFI 跳到第 27 頁（第三段）', orig_index(pg.evaluate(CFI)) == 27, pg.evaluate(CFI))
    pg.evaluate(f"{V}.goTo({json.dumps(bm[0]['cfi'] if bm else '')})"); pg.wait_for_timeout(1200)
    check('跳回書籤（第 11 頁）', orig_index(pg.evaluate(CFI)) == 11, pg.evaluate(CFI))
    pg.evaluate(f"{V}.goTo('epubcfi(/6/2!/4)')"); pg.wait_for_timeout(1200)
    check('原書封面（cover.xhtml）→ 對到第 1 頁', orig_index(pg.evaluate(CFI)) == 1, pg.evaluate(CFI))
    # 搜尋不會出錯（圖片書沒有字）
    pg.evaluate(f"(async()=>{{for await (const r of {V}.search({{query:'天'}})) {{ if (r==='done') break; }}}})()"); pg.wait_for_timeout(800)

    # ---------- 2. 欄數改變 → 分段大小跟著變，停在同一頁 ----------
    pg.evaluate(f"{V}.goTo('epubcfi(/6/36!/4)')"); pg.wait_for_timeout(1200)
    open_panel(pg)
    ci = pg.query_selector_all('.cwfm-settings-panel input[type=number]')
    pg.evaluate("(()=>{const s=window.__cwfm.settings;s.maxColumnCount=5;window.__cwfm.applySettings ? window.__cwfm.applySettings(s) : null})()")
    close_panel(pg)
    # 直接透過面板欄位改：找最大欄數欄位
    pg.evaluate("""(()=>{const s=window.__cwfm.settings;s.maxColumnCount=5;})()""")
    pg.evaluate("window.__cwfm.imgOnSettings(window.__cwfm.settings)"); pg.wait_for_timeout(1500)
    ids = pg.evaluate(f"{V}.book.sections.map(s=>s.id)")
    check('5 欄 → 每段 15 頁（29 頁 → 2 段）', ids == ['cwfm-seg-0-1', 'cwfm-seg-1-16'], ids)
    k = orig_index(pg.evaluate(CFI))
    check('改欄數後仍在第 17 頁附近（同一跨頁內）', 16 <= k <= 17, pg.evaluate(CFI))
    pg.evaluate("window.__cwfm.settings.maxColumnCount=2; window.__cwfm.imgOnSettings(window.__cwfm.settings)"); pg.wait_for_timeout(1500)

    # ---------- 3. 翻頁方向：右翻 ----------
    pg.evaluate(f"{V}.goTo('epubcfi(/6/12!/4)')"); pg.wait_for_timeout(1200)
    open_panel(pg)
    sel = pg.query_selector('.cwfm-settings-panel select >> nth=0')
    dir_sel = pg.evaluate_handle("[...document.querySelectorAll('.cwfm-settings-panel select')].find(s=>[...s.options].some(o=>o.value==='rtl'))")
    pg.evaluate("(s)=>{s.value='rtl';s.dispatchEvent(new Event('change'))}", dir_sel); pg.wait_for_timeout(1800)
    close_panel(pg)
    st = pg.evaluate(f"(()=>{{const v={V};const d=v.renderer.getContents()[0].doc;return [v.book.dir,d.documentElement.getAttribute('dir')]}})()")
    check('改右翻：book.dir＝rtl、文件版面 rtl', st == ['rtl', 'rtl'], st)
    check('改右翻後仍在同一頁（第 5 頁）', orig_index(pg.evaluate(CFI)) == 5, pg.evaluate(CFI))
    vis = pg.evaluate(f"(()=>{{const d={V}.renderer.getContents()[0].doc;const fr=d.defaultView.frameElement.getBoundingClientRect();return [...d.querySelectorAll('.cwfm-ib-p')].map(e=>{{const r=e.getBoundingClientRect();return [e.dataset.orig, Math.round(r.left+fr.left)]}}).filter(x=>x[1]>=0&&x[1]<1180).sort((a,b)=>a[1]-b[1])}})()")
    check('右翻：第 5 頁在右、第 6 頁在左', [v[0] for v in vis] == ['6', '5'], vis)
    pg.screenshot(path=f'{OUT_DIR}/v184_rtl_{BR}.png')
    pg.keyboard.press('ArrowLeft'); pg.wait_for_timeout(900)
    check('右翻：← 是下一頁（第 7 頁）', orig_index(pg.evaluate(CFI)) == 7, pg.evaluate(CFI))
    pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(900)
    check('右翻：→ 是上一頁（第 5 頁）', orig_index(pg.evaluate(CFI)) == 5, pg.evaluate(CFI))
    # 反轉點擊區：← → 一起對調
    pg.evaluate("window.__cwfm.settings.reverseTapZones=true")
    pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(900)
    check('反轉點擊區：右翻時 → 變成下一頁（第 7 頁）', orig_index(pg.evaluate(CFI)) == 7, pg.evaluate(CFI))
    pg.mouse.click(60, 400); pg.wait_for_timeout(900)
    check('反轉點擊區：點左邊變成上一頁（第 5 頁）', orig_index(pg.evaluate(CFI)) == 5, pg.evaluate(CFI))
    pg.evaluate("window.__cwfm.settings.reverseTapZones=false")

    # ---------- 4. 插頁：最前面補一頁（開始頁）、在這頁前插空白頁 ----------
    open_panel(pg)
    front = pg.evaluate_handle("[...document.querySelectorAll('.cwfm-settings-panel label')].find(l=>l.textContent==='在全書最前面補一頁').parentElement.querySelector('input')")
    pg.evaluate("(i)=>i.click()", front); pg.wait_for_timeout(1800)
    btxt = pg.evaluate("[...document.querySelectorAll('.cwfm-settings-panel label')].find(l=>/這頁前/.test(l.textContent)).textContent")
    check('插頁按鈕：這頁還沒插過 → 顯示「插入」', btxt == '在這頁前插入空白頁', btxt)
    ins = pg.evaluate_handle("[...document.querySelectorAll('.cwfm-settings-panel label')].find(l=>/這頁前/.test(l.textContent)).parentElement.querySelector('button')")
    pg.evaluate("(b)=>b.click()", ins); pg.wait_for_timeout(1800)
    btxt = pg.evaluate("[...document.querySelectorAll('.cwfm-settings-panel label')].find(l=>/這頁前/.test(l.textContent)).textContent")
    close_panel(pg)
    check('插入後按鈕變「移除」', btxt == '移除這頁前的空白頁', btxt)
    blank = pg.evaluate(f"(()=>{{const d={V}.renderer.getContents()[0].doc;const b=d.querySelector('.cwfm-ib-blank');return b&&b.nextElementSibling&&b.nextElementSibling.dataset.orig}})()")
    check('空白頁插在目前那頁前面（補頁後跨頁變成 4、5）', blank in ('4', '5'), blank)
    pg.evaluate(f"{V}.goTo('epubcfi(/6/4!/4)')"); pg.wait_for_timeout(1500)
    sp = pg.evaluate(f"(()=>{{const d={V}.renderer.getContents()[0].doc;const s=d.querySelector('.cwfm-ib-start');return s?[s.querySelector('.cwfm-ib-title').textContent,!!s.querySelector('button'),s.nextElementSibling.dataset.orig,s.querySelector('.cwfm-ib-author').textContent,(s.querySelector('.cwfm-tp-pub')||{{}}).textContent,s.querySelectorAll('.cwfm-tp-rule').length]:null}})()")
    check('開始頁在封面前：古典扉頁（書名、作者 著、上下分隔線、最下緣出版社，沒有按鈕）', sp == ['日本兄弟', False, '1', '松本大洋　著', '大塊文化', 2], sp)
    pg.screenshot(path=f'{OUT_DIR}/v184_start_{BR}.png')
    check('開始頁不算位置：CFI 仍是第 1 頁', orig_index(pg.evaluate(CFI)) == 1, pg.evaluate(CFI))
    pg.keyboard.press('ArrowLeft'); pg.wait_for_timeout(1000)
    check('從開始頁翻下一頁（右翻 ←）→ 下一個跨頁（第 2 頁起）', orig_index(pg.evaluate(CFI)) == 2, pg.evaluate(CFI))
    ls = pg.evaluate(LS)
    bk = (ls.get('bookSettings') or {}).get(str(BOOK_ID)) or {}
    check('這本書記住：右翻（v1.86.0 起是一般設定，存在 v）、補一頁、插頁位置', (bk.get('v') or {}).get('pageDirection') == 'rtl' and (bk.get('b') or {}).get('frontInsert') is True and len(bk['b'].get('insertsBefore') or []) == 1, [ (bk.get('v') or {}).get('pageDirection'), bk.get('b')])
    pg.close()

    # ---------- 5. 重開同一本：全部記住 ----------
    pg = page()
    st = pg.evaluate(f"(()=>{{const v={V};return [v.book.dir, !!v.renderer.getContents()[0].doc.querySelector('.cwfm-ib-start') || v.book.sections[0].cwfmSeg.items[0].type]}})()")
    check('重開：右翻、開始頁都還在', st[0] == 'rtl' and st[1] in (True, 'start'), st)
    pg.close()

    # ---------- 6. 文字書不受影響、用全域設定 ----------
    EPUB = TEXT_EPUB
    # 測試伺服器兩本書同一個書號：先刪掉圖片書記住的設定，模擬「另一本沒調整過的文字書」
    pg = ctx.new_page(); pg.goto(BASE + '/x')
    pg.evaluate("(()=>{const s=JSON.parse(localStorage.getItem('cwfm-settings')||'{}');delete (s.bookSettings||{})['%d'];localStorage.setItem('cwfm-settings',JSON.stringify(s))})()" % BOOK_ID)
    pg.close()
    pg = page()
    tinfo = pg.evaluate(f"(()=>{{const v={V};return [!!window.__cwfm.imageBook, v.book.sections.length, v.book.dir, window.__cwfm.settings.leftRightPadding]}})()")
    check('文字書：不是圖片書、章節不變、左翻、留白不是圖片書的 0', tinfo[0] is False and tinfo[1] == 2 and tinfo[2] == 'ltr' and tinfo[3] != 0, tinfo)
    # 內建設定檔標籤
    open_panel(pg)
    chips = pg.evaluate("""(()=>{const g=[...document.querySelectorAll('.cwfm-settings-panel .cwfm-keylist')];
        const prof=g.find(w=>/文字書/.test(w.textContent));
        const b=[...prof.querySelectorAll('.cwfm-keychip-builtin')].map(c=>[c.textContent, !!c.querySelector('.cwfm-keychip-bicon svg'), !!c.querySelector('.cwfm-keychip-remove'), c.querySelectorAll('.cwfm-keychip-rename').length]);
        const sep=!!prof.querySelector('.cwfm-keylist-sep');
        const col=g.find(w=>/跟隨系統/.test(w.textContent));
        const cb=[...col.querySelectorAll('.cwfm-keychip-builtin')].map(c=>!!c.querySelector('.cwfm-keychip-bicon svg'));
        return {b,sep,cb}})()""")
    check('內建設定檔：文字書、圖片書排最前面，有圖示、沒有刪除鈕、沒有改名（只有覆蓋更新）', chips['b'][0] == ['文字書', True, False, 1] and chips['b'][1][:3] == ['圖片書', True, False], chips['b'])
    check('沒有自訂設定檔時不畫分隔線', not chips['sep'])
    check('配色的內建標籤也有圖示', len(chips['cb']) == 5 and all(chips['cb']), chips['cb'])
    pg.screenshot(path=f'{OUT_DIR}/v184_panel_{BR}.png')
    pg.evaluate("[...document.querySelectorAll('.cwfm-keychip-builtin')].find(c=>c.textContent==='圖片書').querySelector('.cwfm-keychip-text').click()"); pg.wait_for_timeout(800)
    s2 = pg.evaluate("[window.__cwfm.settings.maxColumnCount, window.__cwfm.settings.leftRightPadding]")
    check('套用「圖片書」：兩欄、留白 0', s2 == [2, 0], s2)
    # 覆蓋更新 → 出現恢復預設值；恢復後消失
    pg.evaluate("window.__cwfm.settings.leftRightPadding=40")
    pg.evaluate("[...document.querySelectorAll('.cwfm-keychip-builtin')].find(c=>c.textContent==='圖片書').querySelector('.cwfm-keychip-rename').click()"); pg.wait_for_timeout(400)
    pg.click('.cwfm-confirm-overlay .cwfm-ok-primary, .cwfm-confirm-overlay button.cwfm-confirm-ok'); pg.wait_for_timeout(400)
    pg.keyboard.press('Enter'); pg.wait_for_timeout(400)
    over = pg.evaluate(LS).get('builtinProfiles', {}).get('image', {})
    nbtn = pg.evaluate("[...document.querySelectorAll('.cwfm-keychip-builtin')].find(c=>c.textContent==='圖片書').querySelectorAll('.cwfm-keychip-rename').length")
    check('覆蓋更新「圖片書」：存下留白 40，多一顆恢復預設值', (over or {}).get('leftRightPadding') == 40 and nbtn == 2, [over and over.get('leftRightPadding'), nbtn])
    close_panel(pg)
    # 文字書這次有調整（套用圖片書）→ 這本書記住了；圖片書的「最後一次設定」不受影響
    ls = pg.evaluate(LS)
    check('調整過的文字書記住自己的設定', str(BOOK_ID) in (ls.get('bookSettings') or {}), list((ls.get('bookSettings') or {}).keys()))
    pg.close()

    # ---------- 7. 上一步存檔動畫（方案 E） ----------
    pg = page()
    pg.evaluate(f"{V}.goTo('epubcfi(/6/4!/4/2)')"); pg.wait_for_timeout(500)
    BACK = ".cwfm-toolbar-top .cwfm-nav-group[data-nav-kind=toc] .cwfm-nav-btn"
    pg.evaluate("window.__cwfm.recordNav ? 0 : 0")
    # 用目錄跳一次產生紀錄
    pg.click('button[aria-label="目錄"], button[aria-label="Table of Contents"]', force=True); pg.wait_for_timeout(500)
    pg.evaluate("[...document.querySelectorAll('.cwfm-toc-view a, .cwfm-toc-view [role=treeitem]')].find(a=>/第二章/.test(a.textContent)).click()"); pg.wait_for_timeout(150)
    a = pg.evaluate(f"(()=>{{const b=document.querySelector('{BACK}');const p=b.querySelector('.cwfm-nav-plus');return [b.dataset.cwfmAnimNav, p&&p.textContent, getComputedStyle(b.querySelector('svg')).animationName, p&&getComputedStyle(p).animationName, getComputedStyle(b.querySelector('.cwfm-nav-count')).animationName]}})()")
    check('記錄一筆：上一步箭頭放大＋數字位置出現 +1', a[0] == '1' and a[1] == '+1' and a[2] == 'cwfm-anim-pulse' and a[3] == 'cwfm-anim-plus' and a[4] == 'cwfm-anim-count-out', a)
    pg.screenshot(path=f'{OUT_DIR}/v184_navanim_{BR}.png', clip={'x': 1000, 'y': 0, 'width': 200, 'height': 48})
    pg.wait_for_timeout(900)
    check('0.7 秒後動畫結束', pg.evaluate(f"document.querySelector('{BACK}').dataset.cwfmAnimNav") is None)
    pg.close()

    b.close()
check('沒有頁面錯誤', not errs, errs)
