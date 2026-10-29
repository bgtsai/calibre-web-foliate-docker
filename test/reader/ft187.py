# v1.87.0：設定檔改成「目前使用中的那一組，調整自動存回」——自動儲存、內建唯讀→自動建立「（已調整）」與編號、
#          書指向設定檔且共用、還原這次調整（含刪副本、兩處按鈕）、介面狀態／素材庫／語言不跟設定檔、選中樣式、
#          標籤前置圖示 14px、內建圖片書動畫黑色、舊資料（v、builtinProfiles）丟掉、刪掉使用中的設定檔退回新書預設
# 用法：python3 ft187.py <dp.html> <dr.js> <瀏覽器>（CWFM_EPUB 可指定真的圖片書，預設現場產生）
import sys, os, json
exec(open('ft180.py').read().split("with sync_playwright() as p:")[0])
TEXT_EPUB = EPUB
IMG_EPUB = __import__('make_image_epub').default_image_epub()
OUT_DIR = os.environ.get('OUT_DIR', '/tmp')
S = "window.__cwfm.settings"
SETBTN = 'button[aria-label="設定"], button[aria-label="Settings"]'
LS = "JSON.parse(localStorage.getItem('cwfm-settings')||'{}')"
PROF = "[...document.querySelectorAll('.cwfm-settings-panel .cwfm-group')].find(g=>g.querySelector('.cwfm-group-title').textContent.trim()==='設定檔')"


def open_panel(pg):
    pg.click(SETBTN, force=True); pg.wait_for_timeout(700)


def close_panel(pg):
    pg.evaluate("document.querySelector('.cwfm-settings-panel .cwfm-panel-header .cwfm-close-btn')?.click()"); pg.wait_for_timeout(400)


def bump_font(pg, times=1):  # 用面板上字級的數值框調整（跟使用者一樣走 change 事件）
    for _ in range(times):
        pg.evaluate("""(()=>{const f=[...document.querySelectorAll('.cwfm-settings-panel .cwfm-field')].find(f=>/^字級/.test(f.querySelector('label')?.textContent||''));
            const i=f.querySelector('.cwfm-value-input');i.value=String(parseFloat(i.value)+10);i.dispatchEvent(new Event('change',{bubbles:true}))})()"""); pg.wait_for_timeout(500)


def state(pg):
    return pg.evaluate(f"""(()=>{{const g={PROF};const sel=[...g.querySelectorAll('.cwfm-keychip-selected')];
        const st=g.querySelector('.cwfm-prof-status');const hb=document.querySelector('.cwfm-panel-header .cwfm-prof-restore-hdr');const ls={LS};
        return {{ref:sel.map(c=>c.dataset.cwfmProfile), selName:sel.map(c=>c.querySelector('.cwfm-keychip-text').textContent), dot:sel.map(c=>c.classList.contains('cwfm-keychip-adjusted')),
          status:st.style.display!=='none'?st.querySelector('.cwfm-prof-status-text').textContent:null, hdr:hb.style.display!=='none'?hb.textContent:null,
          themes:(ls.savedThemes||[]).map(x=>x.name), font:{S}.fontSize, book:(ls.bookSettings||{{}})['{BOOK_ID}']||null,
          saved:Object.fromEntries((ls.savedThemes||[]).map(x=>[x.name,x.values.fontSize]))}}}})()""")


with sync_playwright() as p:
    BR = sys.argv[3]; b = getattr(p, BR).launch()
    errs = []

    def page(ctx, settings=None):
        pg = ctx.new_page()
        pg.on('pageerror', lambda e: errs.append(str(e)[:300]))
        pg.on('console', lambda m: errs.append(m.text[:300]) if m.type == 'error' and 'lock initial anchor' not in m.text and '初始鎖定' not in m.text and '404' not in m.text else None)
        if settings is not None:
            pg.add_init_script("if(!sessionStorage.getItem('seeded')){localStorage.setItem('cwfm-settings', %s);sessionStorage.setItem('seeded','1')}" % json.dumps(json.dumps(settings)))
        pg.goto(URL); pg.wait_for_timeout(4500)
        return pg

    # ---------- 1. 文字書：內建唯讀 → 第一次調整自動建立「文字書（已調整）」 ----------
    EPUB = TEXT_EPUB
    ctx = b.new_context(viewport={'width': 1200, 'height': 800}, locale='zh-TW')
    # 舊資料：v1.84～86 的 builtinProfiles 與每本書一份設定值 v → 丟掉、回到程式預設
    pg = page(ctx, {'builtinProfiles': {'text': {'fontSize': 250}}, 'bookSettings': {str(BOOK_ID): {'v': {'fontSize': 260}, 'b': {}, 't': 1}},
                    'groupCollapsedState': {'關於': True}, 'colorPickerModeByKey': {'customTextColor': 'HSV'}, 'savedColorSchemes': [{'id': 'c1', 'name': '我的配色', 'textColor': '#111111', 'backgroundColor': '#eeeeee'}], 'uiLanguage': 'zh'})
    font0 = pg.evaluate(f"{S}.fontSize")
    check('舊的 builtinProfiles 與 bookSettings[書].v 丟掉：用內建文字書的程式預設（不是 250／260）', font0 not in (250, 260), font0)
    open_panel(pg)
    s = state(pg)
    check('開書用內建文字書：標籤選中（藍框）、沒有調整時不顯示狀態列與標題列還原', s['ref'] == ['builtin:text'] and s['status'] is None and s['hdr'] is None and s['dot'] == [False], s)
    sel_css = pg.evaluate(f"(()=>{{const c={PROF}.querySelector('.cwfm-keychip-selected');const cs=getComputedStyle(c);const o=[...document.querySelectorAll('.cwfm-keychip-option.cwfm-keychip-selected, .cwfm-keychip-selected')].find(x=>x!==c);return [cs.borderTopColor, o?getComputedStyle(o).borderTopColor:cs.borderTopColor]}})()")
    check('選中樣式跟配色選中同一套藍框', sel_css[0] == sel_css[1] and sel_css[0] != 'rgba(0, 0, 0, 0)', sel_css)
    icons = pg.evaluate(f"""(()=>{{const q=s=>[...document.querySelectorAll(s)].map(e=>{{const r=e.querySelector('svg').getBoundingClientRect();return [r.width,r.height]}});
        const chipH=[...{PROF}.querySelectorAll('.cwfm-keychip')].map(c=>c.getBoundingClientRect().height);
        return {{prof:q('.cwfm-settings-panel .cwfm-keychip-builtin .cwfm-keychip-bicon'), chipH}}}})()""")
    check('設定檔與配色的內建標籤前置圖示 14px', all(abs(w - 14) <= 0.5 and abs(h - 14) <= 0.5 for w, h in icons['prof']) and len(icons['prof']) >= 7, icons['prof'])
    check('標籤高度沒被撐高（內建與一般標籤同高）', max(icons['chipH']) - min(icons['chipH']) <= 0.5, icons['chipH'])
    check('沒有磁碟（覆蓋更新）鈕、沒有恢復預設值鈕', pg.evaluate(f"{PROF}.querySelectorAll('.cwfm-keychip-builtin .cwfm-keychip-rename').length") == 0)
    bump_font(pg)
    s = state(pg)
    check('第一次調整 → 自動建立「文字書（已調整）」並切過去、存下調整後的值', s['themes'] == ['文字書（已調整）'] and s['selName'] == ['文字書（已調整）'] and s['saved']['文字書（已調整）'] == s['font'] != font0, s)
    check('這本書指向新建的設定檔（沒有 v）', s['book'] and s['book']['profile'].startswith('theme:') and 'v' not in s['book'], s['book'])
    check('狀態列：「已從文字書建立『文字書（已調整）』」＋橘點＋標題列〔還原這次調整〕', s['status'] == '已從文字書建立「文字書（已調整）」' and s['dot'] == [True] and s['hdr'] == '還原這次調整', s)
    pg.screenshot(path=f'{OUT_DIR}/v187_created_{BR}.png')
    pg.evaluate(f"{PROF}.querySelector('.cwfm-prof-status').scrollIntoView({{block:'center'}})"); pg.wait_for_timeout(200)
    pg.screenshot(path=f'{OUT_DIR}/v187_status_{BR}.png')
    bump_font(pg)
    s = state(pg)
    check('之後的調整存進同一份副本（不再建新的）', s['themes'] == ['文字書（已調整）'] and s['saved']['文字書（已調整）'] == s['font'], s)
    # 還原（標題列）：切回內建並刪掉副本
    pg.evaluate("document.querySelector('.cwfm-panel-header .cwfm-prof-restore-hdr').click()"); pg.wait_for_timeout(800)
    s = state(pg)
    check('還原（含刪副本）：切回內建文字書、副本刪掉、字級回到原本、兩處按鈕消失', s['ref'] == ['builtin:text'] and s['themes'] == [] and s['font'] == font0 and s['status'] is None and s['hdr'] is None, s)
    # 編號：建一份、關面板（起點清掉）、切回內建再調整 → 「（已調整 2）」
    bump_font(pg); close_panel(pg); open_panel(pg)
    s = state(pg)
    check('關面板再打開：沒有還原（起點重記）', s['status'] is None and s['hdr'] is None and s['themes'] == ['文字書（已調整）'], s)
    pg.evaluate(f"{PROF}.querySelector('.cwfm-keychip[data-cwfm-profile=\"builtin:text\"] .cwfm-keychip-text').click()"); pg.wait_for_timeout(800)
    bump_font(pg, 2)
    s = state(pg)
    check('同名依序「文字書（已調整 2）」', s['themes'] == ['文字書（已調整）', '文字書（已調整 2）'] and s['selName'] == ['文字書（已調整 2）'], s)

    # ---------- 2. 自訂設定檔：自動存回＋區塊〔還原〕 ----------
    pg.evaluate(f"[...{PROF}.querySelectorAll('.cwfm-keychip')].find(c=>c.textContent==='文字書（已調整）').querySelector('.cwfm-keychip-text').click()"); pg.wait_for_timeout(800)
    s = state(pg)
    start_font = s['font']
    check('面板開著時切換設定檔：起點改成切換當下（沒有還原）', s['selName'] == ['文字書（已調整）'] and s['status'] is None, s)
    bump_font(pg)
    s = state(pg)
    check('自訂設定檔：調整直接存回、沒有建新的；狀態列「文字書（已調整）：這次有調整（已自動儲存）」', s['saved']['文字書（已調整）'] == s['font'] != start_font and len(s['themes']) == 2
          and s['status'] == '文字書（已調整）：這次有調整（已自動儲存）' and s['dot'] == [True], s)
    pg.evaluate(f"{PROF}.querySelector('.cwfm-prof-status .cwfm-prof-restore').click()"); pg.wait_for_timeout(800)
    s = state(pg)
    check('區塊〔還原〕：回到起點並存回、按鈕消失', s['font'] == start_font and s['saved']['文字書（已調整）'] == start_font and s['status'] is None and s['hdr'] is None and s['dot'] == [False], s)
    # 介面狀態／素材庫／語言不跟設定檔（使用者定案：介面狀態不納入）
    vals = pg.evaluate(f"{LS}.savedThemes[0].values")
    check('設定檔不含介面狀態、素材庫、語言、錯誤紀錄', not any(k in vals for k in ['groupCollapsedState', 'colorPickerModeByKey', 'tocFilter', 'savedColorSchemes', 'fontNameHistory', 'uploadedFonts', 'uiLanguage', 'errlogUpload']), sorted(vals))
    pg.evaluate(f"{PROF}.querySelector('.cwfm-keychip[data-cwfm-profile=\"builtin:text\"] .cwfm-keychip-text').click()"); pg.wait_for_timeout(800)
    g = pg.evaluate(f"[{S}.groupCollapsedState['關於'], {S}.colorPickerModeByKey.customTextColor, {S}.savedColorSchemes.length, {S}.uiLanguage]")
    check('切換設定檔後：分組收合、取色器模式、自訂配色、語言都不變', g == [True, 'HSV', 1, 'zh'], g)
    close_panel(pg); pg.close()

    # ---------- 3. 書指向設定檔、共用：重開記得用哪個；另一本指向同一份的書拿到同樣的值 ----------
    pg = page(ctx)
    open_panel(pg)
    pg.evaluate(f"[...{PROF}.querySelectorAll('.cwfm-keychip')].find(c=>c.textContent==='文字書（已調整 2）').querySelector('.cwfm-keychip-text').click()"); pg.wait_for_timeout(800)
    close_panel(pg)
    ls = pg.evaluate(LS)
    tid = next(x['id'] for x in ls['savedThemes'] if x['name'] == '文字書（已調整 2）')
    f2 = next(x['values']['fontSize'] for x in ls['savedThemes'] if x['name'] == '文字書（已調整 2）')
    pg.close()
    pg = page(ctx)
    s = pg.evaluate(f"[{S}.fontSize, {LS}.bookSettings['{BOOK_ID}'].profile]")
    check('重開同一本：用它指向的設定檔', s == [f2, 'theme:' + tid], [s, f2, tid])
    # 模擬另一本書：把這本書的紀錄換成「另一本書號指向同一份」再加調整，存回的值共用
    open_panel(pg); bump_font(pg); close_panel(pg)
    s = pg.evaluate(f"[{S}.fontSize, {LS}.savedThemes.find(x=>x.id==='{tid}').values.fontSize]")
    check('同一個設定檔的書共用調整（存回設定檔本身）', s[0] == s[1] != f2, s)
    # 刪掉使用中的設定檔 → 退回新書預設（內建文字書）
    open_panel(pg)
    pg.evaluate(f"[...{PROF}.querySelectorAll('.cwfm-keychip')].find(c=>c.textContent==='文字書（已調整 2）').querySelector('.cwfm-keychip-remove').click()"); pg.wait_for_timeout(400)
    pg.click('.cwfm-confirm-overlay .cwfm-confirm-ok'); pg.wait_for_timeout(900)
    s = state(pg)
    check('刪掉使用中的設定檔：退回新書預設（內建文字書）、沒有因此建立副本', s['ref'] == ['builtin:text'] and s['themes'] == ['文字書（已調整）'] and s['book']['profile'] == 'builtin:text', s)
    close_panel(pg); pg.close(); ctx.close()

    # ---------- 4. 圖片書：內建動畫黑色、調整建立「圖片書（已調整）」 ----------
    EPUB = IMG_EPUB
    ctx = b.new_context(viewport={'width': 1200, 'height': 800}, locale='zh-TW')
    pg = page(ctx)
    a = pg.evaluate(f"[!!window.__cwfm.imageBook, {S}.pageFlipAnimColor, {S}.tapZoneVisible]")
    check('內建圖片書：翻頁動畫顏色黑色（不是 AUTO）、點擊區提示照常顯示', a == [True, '#000000', True], a)
    open_panel(pg)
    s = state(pg)
    check('圖片書開書：選中內建圖片書', s['ref'] == ['builtin:image'], s)
    bump_font(pg)
    s = state(pg)
    check('圖片書調整 → 「圖片書（已調整）」', s['themes'] == ['圖片書（已調整）'] and s['status'] == '已從圖片書建立「圖片書（已調整）」', s)
    pg.screenshot(path=f'{OUT_DIR}/v187_image_{BR}.png')
    close_panel(pg); pg.close(); ctx.close()
    b.close()
check('沒有頁面錯誤', not errs, errs)
print('SUMMARY', sum(results), '/', len(results))
