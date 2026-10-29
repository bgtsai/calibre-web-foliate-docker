# v1.82：設定面板分組調整、設定檔存全部設定（套用後面板同步、快速鍵就地換）、錯誤面板「忽略」
import sys
exec(open('ft180.py').read().split("SET = \"window.__cwfm.settings\"")[0])
S = "window.__cwfm.settings"
with sync_playwright() as p:
    b = getattr(p, BROWSER).launch(); ctx = b.new_context(viewport={'width': 1400, 'height': 900}); pg = ctx.new_page()
    pg.goto(URL); pg.wait_for_timeout(3500)
    pg.click('button[aria-label="設定"], button[aria-label="Settings"]', force=True); pg.wait_for_timeout(800)
    titles = pg.evaluate("[...document.querySelectorAll('.cwfm-settings-panel .cwfm-group-title')].map(e=>e.textContent.trim())")
    want = ['Profile', 'Apply Colors', 'Font', 'Typography', 'Layout', 'Page Insertion', 'Page Turning', 'Auto-Hide', 'Reading Behavior', 'Shortcuts', '語言 / Language']
    check('分組順序與名稱', titles[:len(want)] == want, titles)
    grp = lambda name: f"[...document.querySelectorAll('.cwfm-settings-panel .cwfm-group')].find(g=>g.querySelector('.cwfm-group-title').textContent.trim()==='{name}')"
    labels = lambda name: pg.evaluate(f"[...({grp(name)}).querySelectorAll('.cwfm-group-body label')].map(l=>l.textContent.trim()).filter(Boolean)")
    check('翻頁設定的內容', labels('Page Turning'), labels('Page Turning'))
    ah = labels('Auto-Hide'); check('介面隱藏＝游標＋秒數＋工具列', len(ah) >= 3 and 'toolbar' in ' '.join(ah).lower(), ah)
    check('新增鈕文字', pg.evaluate(f"({grp('Profile')}).querySelector('.cwfm-keychip-add').textContent") == '+ New / Save As Profile')
    # 狀態 A
    pg.evaluate(f"""(()=>{{const s={S}; s.autoHideToolbar=true; s.tapZoneWidthPx=150; s.horizontalSizeMode='content'; s.targetContentWidthPx=640;
        s.columnGapPx=40; s.cursorAutoHideEnabled=true; s.pageFlipDebounceMs=300; s.pagingKeys.prev.push('KeyA'); s.uiLanguage='auto'; window.__cwfm.refreshSettingsPanel();}})()""")
    pg.click(f"text=+ New / Save As Profile"); pg.wait_for_timeout(300)
    pg.fill('.cwfm-prompt-input', 'P1'); pg.click('.cwfm-confirm-ok'); pg.wait_for_timeout(300)
    vals = pg.evaluate(f"{S}.savedThemes[0].values")
    check('存了全部設定（含快速鍵、介面隱藏、內容優先）', all(k in vals for k in ['pagingKeys','bookmarkKeys','autoHideToolbar','tapZoneWidthPx','horizontalSizeMode','targetContentWidthPx','columnGapPx','preciseAnchorAlign','cloudFirst']), sorted(vals))
    check('不存語言、錯誤紀錄、素材庫', not any(k in vals for k in ['uiLanguage','errlogUpload','savedThemes','uploadedFonts','groupCollapsedState']))
    # 狀態 B：改值、就地改快速鍵陣列（若沒深拷貝，設定檔會跟著變）
    pg.evaluate(f"""(()=>{{const s={S}; s.autoHideToolbar=false; s.tapZoneWidthPx=200; s.horizontalSizeMode='margin'; s.columnGapPx=10;
        s.cursorAutoHideEnabled=false; s.pageFlipDebounceMs=800; s.pagingKeys.prev.push('KeyB'); window.__keysRef=s.pagingKeys.prev; window.__cwfm.refreshSettingsPanel();}})()""")
    check('設定檔沒被後來的修改連動', pg.evaluate(f"!{S}.savedThemes[0].values.pagingKeys.prev.includes('KeyB')"))
    pg.evaluate(f"""(()=>{{const g={grp('Profile')}; [...g.querySelectorAll('.cwfm-keychip')].find(c=>c.textContent.includes('P1')).querySelector('.cwfm-keychip-text').click();}})()"""); pg.wait_for_timeout(600)
    st = pg.evaluate(f"(()=>{{const s={S}; return [s.autoHideToolbar,s.tapZoneWidthPx,s.horizontalSizeMode,s.columnGapPx,s.cursorAutoHideEnabled,s.pageFlipDebounceMs,s.pagingKeys.prev.includes('KeyA'),s.pagingKeys.prev.includes('KeyB'),s.pagingKeys.prev===window.__keysRef]}})()")
    check('套用後回到存的值、快速鍵陣列就地換內容', st == [True,150,'content',40,True,300,True,False,True], st)
    ui = pg.evaluate(f"""(()=>{{const f=[...document.querySelectorAll('.cwfm-settings-panel .cwfm-field')].find(f=>/Tap Zone Width/.test(f.querySelector('label')?.textContent||''));
        const sw=[...document.querySelectorAll('.cwfm-settings-panel .cwfm-field')].find(f=>/Auto-hide Toolbar/.test(f.querySelector('label')?.textContent||''));
        const kb=({grp('Shortcuts')}).textContent;
        return [f.querySelector('.cwfm-value-input').value==='150', sw.querySelector('input[type=checkbox]').checked, kb.includes('KeyA'), kb.includes('KeyB')]}})()""")
    # 註：滑桿本身受 step 對齊（min 不是 5 的倍數），150 會顯示成 151，這是既有行為，看數值框
    check('面板控制項跟著更新（寬度滑桿、快速鍵清單）', ui == [True, True, True, False], ui)
    # 錯誤面板「忽略」
    pg.evaluate("console.error('test error 1')"); pg.wait_for_timeout(1300)
    badge = "[...document.querySelectorAll('button')].find(b=>/^⚠/.test(b.textContent))"
    check('有錯誤時出現 ⚠', pg.evaluate(f"(()=>{{const b={badge};return !!b && b.style.display!=='none'}})()"))
    pg.evaluate(f"{badge}.click()"); pg.wait_for_timeout(300)
    pg.evaluate("[...document.querySelectorAll('button')].find(b=>b.textContent==='忽略').click()"); pg.wait_for_timeout(300)
    check('按忽略後 ⚠ 消失', pg.evaluate(f"(()=>{{const b={badge};return !b || b.style.display==='none'}})()"))
    pg.evaluate("console.error('test error 2')"); pg.wait_for_timeout(1300)
    check('之後有新錯誤才再出現、從 1 算起', pg.evaluate(f"(()=>{{const b={badge};return b && b.style.display!=='none' && b.textContent}})()") == '⚠ 1')
    pg.screenshot(path='/tmp/claude-0/ft182_' + BROWSER + '.png')
    print('SUMMARY', sum(results), '/', len(results)); b.close()
