# v1.88.0：① 滑桿停頓即重排、按住時面板透明、觸控放大版滑桿（刻度尺，相對拖動、兩側自動縮格距、預設值標示）、長按不選取
# 用法：python3 ft188.py <dp.html> <dr.js> <瀏覽器>（截圖寫到 OUT_DIR，預設 /tmp）
import sys, os, json
exec(open('ft180.py').read().split("with sync_playwright() as p:")[0])
OUT_DIR = os.environ.get('OUT_DIR', '/tmp')
SETBTN = 'button[aria-label="設定"], button[aria-label="Settings"]'
FONT = "[...document.querySelectorAll('.cwfm-settings-panel input[type=range]')].find(x=>/^字級/.test(x.closest('.cwfm-field').querySelector('label').textContent))"


def open_panel(pg):  # v1.88 起工具列預設自動隱藏，用 JS 點
    pg.evaluate("document.querySelector('[data-cwfm-tut=\"gear\"]').click()"); pg.wait_for_timeout(700)


def touch_js(kind, x, y, pid=7):  # 觸控用合成 PointerEvent（pointerType=touch）；放大版只看 pointer 事件
    return f"""(()=>{{const t={'(' + FONT + ')' if kind == 'pointerdown' else 'window'};
        t.dispatchEvent(new PointerEvent('{kind}',{{bubbles:true,cancelable:true,pointerId:{pid},pointerType:'touch',clientX:{x},clientY:{y},isPrimary:true}}))}})()"""


with sync_playwright() as p:
    BR = sys.argv[3]; b = getattr(p, BR).launch()
    errs = []
    ctx = b.new_context(viewport={'width': 1180, 'height': 820}, locale='zh-TW')
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errs.append(str(e)[:300]))
    pg.goto(URL); pg.wait_for_timeout(4500)
    open_panel(pg)
    pg.evaluate(f"{FONT}.scrollIntoView({{block:'center'}})"); pg.wait_for_timeout(300)

    # 1. 停頓即重排：連續拖（每 100ms 一格）只更新數字、不重排；停 280ms 後重排一次；放開存檔
    r = pg.evaluate(f"""(async()=>{{const sl={FONT};const n0=window.__cwfm.applyCount||0;const W=ms=>new Promise(r=>setTimeout(r,ms));
        for(let i=1;i<=8;i++){{sl.value=String(100+i*5);sl.dispatchEvent(new Event('input',{{bubbles:true}}));await W(100);}}
        const during=(window.__cwfm.applyCount||0)-n0; await W(400); const afterPause=(window.__cwfm.applyCount||0)-n0;
        sl.value='150';sl.dispatchEvent(new Event('input',{{bubbles:true}}));sl.dispatchEvent(new Event('change',{{bubbles:true}}));await W(500);
        return {{during, afterPause, shown:sl.closest('.cwfm-field').querySelector('.cwfm-value-input').value, setting:window.__cwfm.settings.fontSize}}}})()""")
    check('停頓即重排：連續拖 8 格（每 100ms）中途 0 次重排、停住後 1 次；放開套用最終值', r['during'] == 0 and r['afterPause'] == 1 and r['shown'] == '150' and r['setting'] == 150, r)

    # 2. 滑鼠按住滑桿：面板 5%，放開恢復；沒有放大版
    box = pg.evaluate(f"(()=>{{const r={FONT}.getBoundingClientRect();return [r.x,r.y,r.width,r.height]}})()")
    pg.mouse.move(box[0] + box[2] * 0.3, box[1] + box[3] / 2); pg.mouse.down(); pg.wait_for_timeout(450)
    op = pg.evaluate("getComputedStyle(document.querySelector('.cwfm-settings-panel')).opacity")
    mag = pg.evaluate("!!document.querySelector('.cwfm-mag')")
    pg.mouse.move(box[0] + box[2] * 0.5, box[1] + box[3] / 2, steps=5); pg.mouse.up(); pg.wait_for_timeout(300)
    op2 = pg.evaluate("getComputedStyle(document.querySelector('.cwfm-settings-panel')).opacity")
    check('滑鼠按住：設定面板 opacity 0.05、沒有放大版；放開恢復 1', abs(float(op) - 0.05) < 0.01 and not mag and op2 == '1', [op, mag, op2])

    # 3. 觸控按下：彈出放大版，值不跳、指針對準手指；相對拖動每格 12px；上下移動不影響
    pg.evaluate(f"{FONT}.value='150';{FONT}.dispatchEvent(new Event('change',{{bubbles:true}}))"); pg.wait_for_timeout(500)
    fx = box[0] + box[2] * 0.8; fy = box[1] + box[3] / 2  # 故意按在離目前值很遠的位置
    pg.evaluate(touch_js('pointerdown', fx, fy)); pg.wait_for_timeout(450)
    m = pg.evaluate("""(()=>{const m=document.querySelector('.cwfm-mag');if(!m)return null;const n=m.querySelector('.cwfm-mag-needle').getBoundingClientRect();
        const bb=document.querySelector('.cwfm-mag-bubble');const mr=m.getBoundingClientRect();
        return {needleX:n.x+n.width/2, opacity:getComputedStyle(m).opacity, val:bb.querySelector('b').textContent, name:bb.querySelector('small').textContent,
          bubbleBottom:bb.getBoundingClientRect().bottom, magTop:mr.top, magH:mr.height, panelOp:getComputedStyle(document.querySelector('.cwfm-settings-panel')).opacity,
          labs:[...m.querySelectorAll('.cwfm-mag-lab')].map(l=>l.textContent), font:window.__cwfm.settings.fontSize}})()""")
    check('觸控按下：放大版出現、按下那刻值不變（150）、指針對準手指 x', m and m['val'] == '150' and m['font'] == 150 and abs(m['needleX'] - fx) <= 2, m)
    check('放大版不透明、面板 5%；名稱＋數值在放大版上方；標出最小／最大／預設', m and m['opacity'] == '1' and abs(float(m['panelOp']) - 0.05) < 0.01 and m['bubbleBottom'] <= m['magTop'] and m['name'].startswith('字級')
          and any(l.startswith('預設') for l in m['labs']), m)
    pg.screenshot(path=f'{OUT_DIR}/v188_mag_{BR}.png')
    pg.evaluate(touch_js('pointermove', fx - 24, fy + 60)); pg.wait_for_timeout(100)  # 左 2 格（每格 5%），同時往下 60px
    v1 = pg.evaluate("document.querySelector('.cwfm-mag-bubble b').textContent")
    check('相對拖動：左移 24px＝2 格（150→140），上下移動不算', v1 == '140', v1)
    pg.evaluate(touch_js('pointermove', 0, fy)); pg.wait_for_timeout(100)
    v2 = pg.evaluate("document.querySelector('.cwfm-mag-bubble b').textContent")
    check('左側空間不夠時自動縮格距：拖到視窗左緣就到最小值 70', v2 == '70', v2)
    pg.evaluate(touch_js('pointermove', fx + 12, fy)); pg.wait_for_timeout(100)
    pg.evaluate(touch_js('pointerup', fx + 12, fy)); pg.wait_for_timeout(600)
    e = pg.evaluate("({mag:!!document.querySelector('.cwfm-mag'), font:window.__cwfm.settings.fontSize, op:getComputedStyle(document.querySelector('.cwfm-settings-panel')).opacity})")
    check('放開：放大版收起、面板恢復、套用最終值（右移 1 格＝155）', not e['mag'] and e['op'] == '1' and e['font'] == 155, e)

    # 4. 長按不選取文字、不跳長按選單
    us = pg.evaluate(f"(()=>{{const r={FONT}.closest('.cwfm-slider-row');const cs=getComputedStyle(r);return [cs.userSelect||cs.webkitUserSelect, getComputedStyle({FONT}).touchAction]}})()")
    check('滑桿列不能選取、滑桿 touch-action:none', us[0] == 'none' and us[1] == 'none', us)
    check('沒有頁面錯誤', not errs, errs)
    pg.close(); ctx.close(); b.close()
print('DONE')

# ---------- ②③④：觸控放大、預設值與收合、首次教學 ----------
with sync_playwright() as p:
    BR = sys.argv[3]; b = getattr(p, BR).launch()
    errs = []
    # ③ 預設收合（沒有紀錄）＋內建值；② 電腦不放大
    ctx = b.new_context(viewport={'width': 1280, 'height': 800}, locale='zh-TW')
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)[:300]))
    pg.add_init_script("sessionStorage.setItem('cwfm-v188-test','1')")
    pg.goto(URL); pg.wait_for_timeout(4500)
    open_panel(pg)
    g = pg.evaluate("""(()=>Object.fromEntries([...document.querySelectorAll('.cwfm-settings-panel .cwfm-group')].map(g=>[g.querySelector('.cwfm-group-title').textContent.trim(), g.querySelector('.cwfm-group-body').style.display!=='none'])))()""")
    check('沒有收合紀錄：只展開「設定檔」「翻頁設定」「教學」，其他收合', all(v == (k in ('設定檔', '翻頁設定', '教學')) for k, v in g.items()) and g.get('教學') is True, g)
    order = list(g.keys())
    check('「教學」在「關於」前面、「錯誤紀錄」後面', order.index('教學') == order.index('關於') - 1 and order.index('錯誤紀錄') < order.index('教學'), order)
    d = pg.evaluate("({a:window.__cwfm.settings.autoHideToolbar, v:window.__cwfm.settings.tapZoneVisible, z:document.querySelector('.cwfm-fields-wrap').style.zoom||'1'})")
    check('內建文字書：工具列自動隱藏開、點擊區不顯示；電腦不放大', d['a'] is True and d['v'] is False and d['z'] == '1', d)
    pg.close(); ctx.close()
    # 有收合紀錄的照紀錄
    ctx = b.new_context(viewport={'width': 1280, 'height': 800}, locale='zh-TW')
    pg = ctx.new_page()
    pg.add_init_script("sessionStorage.setItem('cwfm-v188-test','1')")
    pg.add_init_script("if(!sessionStorage.getItem('seeded')){localStorage.setItem('cwfm-settings', JSON.stringify({groupCollapsedState:{'字體':false,'設定檔':true}}));sessionStorage.setItem('seeded','1')}")
    pg.goto(URL); pg.wait_for_timeout(4500); open_panel(pg)
    g2 = pg.evaluate("""(()=>Object.fromEntries([...document.querySelectorAll('.cwfm-settings-panel .cwfm-group')].map(g=>[g.querySelector('.cwfm-group-title').textContent.trim(), g.querySelector('.cwfm-group-body').style.display!=='none'])))()""")
    check('有收合紀錄的分組照紀錄（字體展開、設定檔收合）', g2['字體'] is True and g2['設定檔'] is False, g2)
    pg.close(); ctx.close()
    # 首次教學：沒看過自動出現、三步、跳過／確定都記住、〔重新看教學〕
    kw = {'viewport': {'width': 1180, 'height': 820}, 'locale': 'zh-TW'}
    if BR != 'firefox': kw.update(has_touch=True)
    if BR == 'chromium': kw.update(is_mobile=True)
    ctx = b.new_context(**kw)
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)[:300]))
    pg.add_init_script("sessionStorage.setItem('cwfm-tut-test','1');sessionStorage.setItem('cwfm-v188-test','1')")
    pg.goto(URL); pg.wait_for_timeout(6000)
    st = []
    for i in range(4):
        st.append(pg.evaluate("""(()=>{const c=document.querySelector('.cwfm-tut-card');if(!c)return null;const r=c.getBoundingClientRect();
            return {t:c.querySelector('.cwfm-tut-title').textContent, n:c.querySelector('.cwfm-tut-count').textContent, btn:c.querySelector('.cwfm-tut-next').textContent,
              inView:r.left>=0&&r.top>=0&&r.right<=innerWidth&&r.bottom<=innerHeight, rings:document.querySelectorAll('.cwfm-tut-ring').length,
              barsShown:!document.documentElement.classList.contains('cwfm-bars-hidden'), panel:!!document.querySelector('.cwfm-settings-panel.cwfm-open'),
              open:[...document.querySelectorAll('.cwfm-settings-panel .cwfm-group')].filter(g=>g.querySelector('.cwfm-group-body').style.display!=='none').map(g=>g.querySelector('.cwfm-group-title').textContent.trim())}})()"""))
        if i < 3: pg.click('.cwfm-tut-next'); pg.wait_for_timeout(700)
    check('教學自動出現：三步依序、說明卡在畫面內、每步有框線', all(s and s['inView'] and s['rings'] >= 1 for s in st) and [s['t'] for s in st] == ['工具列會自動隱藏', '設定檔', '翻頁點擊區', '隨時可以重看'] and st[2]['btn'] == '下一步' and st[3]['btn'] == '確定', st)
    check('第 1 步工具列顯示、第 2 步打開設定面板', st[0]['barsShown'] and not st[0]['panel'] and st[1]['panel'], st)
    check('教學期間只展開設定檔、翻頁設定、教學', all(sorted(x['open']) == sorted(['設定檔', '翻頁設定', '教學']) for x in st[1:]), [x['open'] for x in st])
    if BR != 'firefox':
        fs = pg.evaluate("""(()=>{const P=document.querySelector('.cwfm-settings-panel');const f=s=>{const e=[...P.querySelectorAll(s)].find(x=>x.getBoundingClientRect().height>0);return e?parseFloat(getComputedStyle(e).fontSize):null};
            return {zoom:document.querySelector('.cwfm-fields-wrap').style.zoom||'', title:f('.cwfm-panel-header h3'), group:f('.cwfm-group-title'), label:f('.cwfm-field > label'), hint:f('.cwfm-field-hint')}})()""")
        check('觸控字階：不用 zoom；標題 20、分組標題＝項目名稱 17、說明 15（只靠字級與顏色分層）', fs['zoom'] == '' and fs['group'] == 17 and fs['label'] == 17 and fs['hint'] in (15, None) and fs['title'] in (20, None), fs)
    pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(300)
    check('教學中按鍵不傳到下面（不翻頁、教學還在）', pg.evaluate("!!document.querySelector('.cwfm-tut')"))
    pg.click('.cwfm-tut-next'); pg.wait_for_timeout(600)
    r = pg.evaluate("({gone:!document.querySelector('.cwfm-tut'), seen:window.__cwfm.settings.tutorialSeen, saved:JSON.parse(localStorage.getItem('cwfm-settings')||'{}').tutorialSeen, panel:!!document.querySelector('.cwfm-settings-panel.cwfm-open')})")
    check('〔確定〕：教學結束、記住看過（存檔）、教學打開的面板關掉', r['gone'] and r['seen'] == 1 and r['saved'] == 1 and not r['panel'], r)
    pg.reload(); pg.wait_for_timeout(6000)
    check('看過之後重開不再出現', pg.evaluate("!document.querySelector('.cwfm-tut')"))
    open_panel(pg)
    pg.evaluate("[...document.querySelectorAll('.cwfm-settings-panel .cwfm-group-title')].filter(h=>['字體','設定檔'].includes(h.textContent.trim())).forEach(h=>h.click())"); pg.wait_for_timeout(400)
    OPEN = "[...document.querySelectorAll('.cwfm-settings-panel .cwfm-group')].filter(g=>g.querySelector('.cwfm-group-body').style.display!=='none').map(g=>g.querySelector('.cwfm-group-title').textContent.trim()).sort()"
    before = pg.evaluate(OPEN); rec0 = pg.evaluate("JSON.stringify(window.__cwfm.settings.groupCollapsedState)")
    pg.evaluate("[...document.querySelectorAll('.cwfm-settings-panel button')].find(b=>b.textContent==='重新看教學').click()"); pg.wait_for_timeout(800)
    rp = pg.evaluate("({on:!!document.querySelector('.cwfm-tut'), n:document.querySelector('.cwfm-tut-count')?.textContent})")
    check('「教學」分組〔重新看教學〕從第 1 步開始', rp['on'] and rp['n'] == '1 / 4', rp)
    pg.click('.cwfm-tut-skip'); pg.wait_for_timeout(700)
    sk = pg.evaluate("({n:document.querySelector('.cwfm-tut-count')?.textContent, skipShown:getComputedStyle(document.querySelector('.cwfm-tut-skip')).display!=='none'})")
    check('〔跳過〕跳到最後一步（4 / 4），最後一步沒有〔跳過〕', sk['n'] == '4 / 4' and not sk['skipShown'], sk)
    pg.click('.cwfm-tut-next'); pg.wait_for_timeout(400)
    check('最後一步〔確定〕結束', pg.evaluate("!document.querySelector('.cwfm-tut')"))
    open_panel(pg)
    after = pg.evaluate(OPEN); rec1 = pg.evaluate("JSON.stringify(window.__cwfm.settings.groupCollapsedState)")
    check('教學結束後分組還原成使用者原本的展開／收合，收合紀錄沒被改', after == before and rec1 == rec0 and '字體' in before and '設定檔' not in before, [before, after, rec0, rec1])
    pg.evaluate("document.querySelector('.cwfm-settings-panel .cwfm-close-btn')?.click()"); pg.wait_for_timeout(300)
    pg.evaluate("window.__cwfm.startTutorial()"); pg.wait_for_timeout(500)
    pg.keyboard.press('Escape'); pg.wait_for_timeout(500)
    e1 = pg.evaluate("document.querySelector('.cwfm-tut-count')?.textContent")
    pg.keyboard.press('Escape'); pg.wait_for_timeout(400)
    check('Esc＝跳過：先跳到最後一步，再按一次結束', e1 == '4 / 4' and pg.evaluate("!document.querySelector('.cwfm-tut')"), e1)

    # 觸控目標至少 44×44：在元件中心往外 21px 的位置點，還是點到同一個元件（外觀大小不變）
    if BR != 'firefox':
        ctx2 = b.new_context(viewport={'width': 1180, 'height': 820}, has_touch=True, locale='zh-TW', **({'is_mobile': True} if BR == 'chromium' else {}))
        pg2 = ctx2.new_page(); pg2.on('pageerror', lambda e: errs.append('pg2:' + str(e)[:300])); pg2.add_init_script("sessionStorage.setItem('cwfm-v188-test','1')"); pg2.goto(URL); pg2.wait_for_timeout(4500)
        open_panel(pg2)
        hit = pg2.evaluate("""(()=>{const out={};const probe=(name,el,dirs)=>{if(!el)return;el.scrollIntoView({block:'center'});const r=el.getBoundingClientRect();const cx=r.left+r.width/2,cy=r.top+r.height/2;
            out[name]={size:[Math.round(r.width),Math.round(r.height)],ok:dirs.map(([dx,dy])=>{const t=document.elementFromPoint(cx+dx,cy+dy);return !!t&&(t===el||el.contains(t))})}};
          const P=document.querySelector('.cwfm-settings-panel');const vis=sel=>[...P.querySelectorAll(sel)].find(e=>e.getBoundingClientRect().height>0);
          probe('plus',vis('.cwfm-stepper-btn:last-child'),[[0,-21],[0,21],[21,0]]);
          probe('minus',vis('.cwfm-stepper-btn:first-child'),[[0,-21],[0,21],[-21,0]]);
          probe('switch',vis('.cwfm-switch'),[[0,-21],[0,21]]);
          probe('title',[...P.querySelectorAll('.cwfm-group')].find(g=>g.querySelector('.cwfm-group-body').style.display==='none').querySelector('.cwfm-group-title-collapsible'),[[0,-21],[0,21]]);
          probe('close',P.querySelector('.cwfm-close-btn'),[[0,-21],[0,21],[-21,0]]);
          probe('chip',P.querySelector('.cwfm-keychip'),[[0,-21],[0,21]]);
          return out})()""")
        check('觸控目標：− ＋、開關、分組標題、✕、標籤離中心 21px 仍點得到（≥ 44×44）', all(all(v['ok']) for v in hit.values()) and len(hit) == 6, hit)
        us2 = pg2.evaluate("getComputedStyle(document.querySelector('.cwfm-stepper-btn')).webkitTouchCallout || getComputedStyle(document.querySelector('.cwfm-stepper-btn')).userSelect")
        check('− ＋ 不能選取／不跳長按選單', us2 == 'none', us2)
        pg2.close(); ctx2.close()
    check('沒有頁面錯誤（②③④）', not errs, errs)
    b.close()
print('DONE2')
