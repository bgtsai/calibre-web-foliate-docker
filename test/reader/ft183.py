# v1.83.0：跳轉紀錄上限 99 步＋「99+」＋提示、記錄時「上一步」存檔動畫、加書籤時書籤鈕動畫、減少動態效果改淡入
# 用法：python3 ft183.py <dp.html> <dr.js> <瀏覽器>
import sys, os
exec(open('ft180.py').read().split("SET = \"window.__cwfm.settings\"")[0])
STATE['bookmark'] = 'epubcfi(/6/2!/4/40)'
OUT_DIR = os.environ.get('OUT_DIR', '/tmp')
BACK = ".cwfm-toolbar-top .cwfm-nav-group[data-nav-kind=toc] .cwfm-nav-btn"
CNT = f"document.querySelector('{BACK}').querySelector('.cwfm-nav-count').textContent"
TITLE = f"document.querySelector('{BACK}').title"
ANIM = f"(()=>{{const b=document.querySelector('{BACK}');return [!!b.dataset.cwfmAnim, !!b.querySelector('clipPath')]}})()"
BMB = 'button[aria-label="加入書籤"], button[aria-label="Add bookmark"]'
BMANIM = f"(()=>{{const b=document.querySelector('{BMB}');return [!!b.dataset.cwfmAnim, !!b.querySelector('clipPath'), b.querySelector('svg').getAttribute('fill')]}})()"

def seed(back, trimmed=False):
    STATE['navhist'] = {'toc': {'entries': ['epubcfi(/6/2!/4/%d)' % (2 * (i % 20 + 1)) for i in range(back + 1)], 'idx': back, 'trimmed': trimmed}}

def drag(pg):
    s = pg.query_selector('.cwfm-progress-wrap input[type=range]'); bx = s.bounding_box(); y = bx['y'] + bx['height'] / 2
    a = 0.05 if pg.evaluate("parseFloat(document.querySelector('.cwfm-progress-wrap input[type=range]').value)") > 0.4 else 0.6
    z = 0.6 if a < 0.4 else 0.05
    pg.mouse.move(bx['x'] + bx['width'] * a, y); pg.mouse.down()
    for i in range(1, 9): pg.mouse.move(bx['x'] + bx['width'] * (a + (z - a) * i / 8), y); pg.wait_for_timeout(20)
    pg.mouse.up()

with sync_playwright() as p:
    BR = sys.argv[3]; b = getattr(p, BR).launch()
    for motion in ('no-preference', 'reduce'):
        ctx = b.new_context(viewport={'width': 1200, 'height': 800}, reduced_motion=motion, locale='zh-TW')
        seed(98); pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
        pg.goto(URL); pg.wait_for_timeout(4000)
        tag = '' if motion == 'no-preference' else '（減少動態效果）'
        if motion == 'no-preference':
            check('讀回 98 步：顯示 98、提示只有一行', pg.evaluate(CNT) == '98' and '\n' not in pg.evaluate(TITLE), [pg.evaluate(CNT), pg.evaluate(TITLE)])
        drag(pg); pg.wait_for_timeout(120)
        mid = pg.evaluate(ANIM)
        anim_name = pg.evaluate(f"getComputedStyle(document.querySelector('{BACK} svg')).animationName")
        top_anim = pg.evaluate(f"getComputedStyle(document.querySelector('{BACK} .cwfm-anim-top')).animationName")
        if motion == 'no-preference': pg.screenshot(path=f'{OUT_DIR}/v183_anim_{BR}.png', clip={'x': 1000, 'y': 0, 'width': 200, 'height': 48})
        check('拖動放開：上一步播動畫（換上動畫圖示）' + tag, mid == [True, True], mid)
        if motion == 'no-preference':
            check('一般：放大動畫', anim_name == 'cwfm-anim-pulse', anim_name)
        else:
            check('減少動態效果：不放大、改淡入', anim_name == 'none' and top_anim == 'cwfm-anim-glow', [anim_name, top_anim])
        pg.wait_for_timeout(800)
        check('動畫播完換回一般圖示' + tag, pg.evaluate(ANIM) == [False, False], pg.evaluate(ANIM))
        if motion == 'no-preference':
            check('98 → 99（還沒丟過舊紀錄，不顯示 99+）', pg.evaluate(CNT) == '99' and '\n' not in pg.evaluate(TITLE), pg.evaluate(CNT))
            drag(pg); pg.wait_for_timeout(1200)
            c, tt = pg.evaluate(CNT), pg.evaluate(TITLE)
            check('滿了：顯示 99+、提示多一行上限說明', c == '99+' and '99' in tt.split('\n')[-1] and tt.count('\n') == 1, [c, tt])
            drag(pg); pg.wait_for_timeout(300)
            check('滿了再拖：照樣播動畫、維持 99+', pg.evaluate(ANIM)[0] and pg.evaluate(CNT) == '99+', [pg.evaluate(ANIM), pg.evaluate(CNT)])
            pg.wait_for_timeout(1500)
            snap = STATE['navhist'] or {}
            check('99+ 狀態有存進紀錄（重新整理後保留）', (snap.get('toc') or {}).get('trimmed') is True and len(snap['toc']['entries']) == 100, (snap.get('toc') or {}).get('trimmed'))
            pg.screenshot(path=f'{OUT_DIR}/v183_full_{BR}.png', clip={'x': 1000, 'y': 0, 'width': 200, 'height': 48})
            # 書籤：加第一個（按鈕從空心變紅）、再加第二個（已經是紅的）都播動畫，播完是實心紅
            for k in (1, 2):
                pg.click(BMB); pg.wait_for_timeout(300); pg.click('.cwfm-bm-dialog .cwfm-ok-primary'); pg.wait_for_timeout(120)
                m = pg.evaluate(BMANIM)
                check(f'加第 {k} 個書籤：書籤鈕播動畫', m[0] and m[1], m)
                pg.wait_for_timeout(800)
                e = pg.evaluate(BMANIM)
                check(f'加第 {k} 個書籤：播完是實心紅色書籤', e == [False, False, '#E24B4A'], e)
        else:
            pg.click(BMB); pg.wait_for_timeout(300); pg.click('.cwfm-bm-dialog .cwfm-ok-primary'); pg.wait_for_timeout(120)
            ta = pg.evaluate(f"getComputedStyle(document.querySelector('{BMB}').querySelector('.cwfm-anim-top')).animationName")
            check('減少動態效果：書籤也改淡入', ta == 'cwfm-anim-glow', ta)
        ctx.close()
    b.close()
check('沒有頁面錯誤', not errs, errs)
print('ALL OK' if all(r[1] for r in RESULTS) else 'HAS FAIL') if 'RESULTS' in globals() else None
