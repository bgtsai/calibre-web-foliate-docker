import sys
import os
exec(open('ft180.py').read().split("SET = \"window.__cwfm.settings\"")[0])
USERJS = open(os.environ.get('CWFM_MOD_DIR', '../calibre-web-foliate-mod') + '/calibre-web-foliate-mod.user.js', encoding='utf-8').read()
GM = "window.GM_getValue=(k,d)=>d;window.GM_setValue=()=>{};window.GM_addElement=(t,a)=>{const e=document.createElement(t);Object.assign(e,a);(document.head||document.documentElement).appendChild(e);return e;};"
with sync_playwright() as p:
    b = getattr(p, BROWSER).launch()
    for tm in (False, True):
        ctx = b.new_context(viewport={'width': 1100, 'height': 780})
        pg = ctx.new_page(); logs = []
        pg.on('console', lambda m: logs.append(m.text))
        import time as _t
        pg.route('**/file.epub', lambda route: (_t.sleep(1.2), route.continue_()))  # 模擬大檔案下載慢
        if tm: pg.add_init_script(GM + "(function(){function run(){" + USERJS + "\n}if(document.documentElement)run();else{const mo=new MutationObserver(()=>{if(document.documentElement){mo.disconnect();run();}});mo.observe(document,{childList:true});}})();")
        n0 = len([h for h in hits if '/file.epub' in h[1]])
        pg.goto(URL, wait_until='commit'); pg.wait_for_timeout(150)
        early = pg.evaluate("!!document.getElementById('cwfm-loading')")
        pg.wait_for_timeout(4000)
        books = len([h for h in hits if '/file.epub' in h[1]]) - n0
        badge = pg.evaluate("[...document.querySelectorAll('button')].filter(b=>/^⚠/.test(b.textContent)&&getComputedStyle(b).display!=='none').length")
        tag = 'TM+Docker' if tm else 'Docker'
        gone = pg.evaluate("!document.getElementById('cwfm-loading')")
        check(tag + '：一開頁就有載入提示、開好書後移除', early and gone, (early, gone))
        check(tag + '：書檔只下載一次（預先下載被閱讀器接用）', books == 1, books)
        # 純 Docker 從頭開書時有一則已知的「初始鎖定失敗」（CLAUDE.md 記載，舊版也有）；TM+Docker 不能比純 Docker 多
        if not tm: base_badge = badge
        check(tag + '：書有開起來、⚠ 沒有比純 Docker 多', pg.evaluate("!!document.querySelector('foliate-view')?.lastLocation") and badge <= base_badge, badge)
        if tm: check('Tampermonkey 版偵測到 Docker 版、自動停止', any('Tampermonkey 版停止執行' in l for l in logs), [l for l in logs if 'cwfm]' in l][:3])
        ctx.close()
    print('SUMMARY', sum(results), '/', len(results)); b.close()
