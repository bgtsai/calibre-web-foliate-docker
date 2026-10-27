"""v1.81.2：第一個畫面就看不到 Calibre-Web 原生閱讀介面（側邊欄、設定視窗、遮罩、#main 裡 #viewer 以外的東西）。
用法：python3 ft_earlyhide.py <patched read.html> <reader.js> <browser>
  Docker：擋掉閱讀器程式（cwfm-reader.js），看只靠 read.html 裡的 cwfm-early-hide 能不能藏住。
  Tampermonkey：上游原版 read.html（read-0.6.27.html）＋只跑 user.js 外殼（不注入閱讀器），看 document-start 的樣式能不能藏住。
  最後跑一次完整開書，確認最後畫面跟原本一樣（書有開、閱讀區可見）。
"""
import sys, os
exec(open('ft180.py').read().split("SET = \"window.__cwfm.settings\"")[0])
USERJS = open(os.environ.get('CWFM_MOD_DIR', '../calibre-web-foliate-mod') + '/calibre-web-foliate-mod.user.js', encoding='utf-8').read()
# 只跑外殼：GM_addElement 對 script 不做事（閱讀器不會載入），其他照常
GM = "window.GM_getValue=(k,d)=>d;window.GM_setValue=()=>{};window.GM_addElement=(t,a)=>{const e=document.createElement(t);if(t!=='script'){Object.assign(e,a);(document.head||document.documentElement).appendChild(e);}return e;};"
VIS = """[...document.querySelectorAll('#sidebar, #settings-modal, body > div.overlay, #main > :not(#viewer)')]
  .filter(e=>{const s=getComputedStyle(e);const r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0}).map(e=>e.id||e.className||e.tagName)"""
UPSTREAM = open('read-0.6.27.html', encoding='utf-8').read()
with sync_playwright() as p:
    b = getattr(p, BROWSER).launch()
    # ---- Docker：擋掉閱讀器 ----
    ctx = b.new_context(viewport={'width': 1100, 'height': 780}); pg = ctx.new_page()
    pg.route('**/cwfm-reader.js*', lambda r: r.abort())
    pg.goto(URL); pg.wait_for_timeout(1200)
    v = pg.evaluate(VIS)
    check('Docker：閱讀器還沒執行時，原生介面已經看不到', v == [], v)
    check('Docker：載入提示仍顯示', pg.evaluate("!!document.getElementById('cwfm-loading')"))
    ctx.close()
    # ---- Tampermonkey：上游原版頁面＋只跑外殼 ----
    TPLSRC = UPSTREAM  # render() 讀這個全域
    ctx = b.new_context(viewport={'width': 1100, 'height': 780}); pg = ctx.new_page()
    pg.add_init_script(GM + "(function(){function run(){" + USERJS + "\n}if(document.documentElement)run();else{const mo=new MutationObserver(()=>{if(document.documentElement){mo.disconnect();run();}});mo.observe(document,{childList:true});}})();")
    pg.goto(URL); pg.wait_for_timeout(1200)
    v = pg.evaluate(VIS)
    check('Tampermonkey：document-start 樣式藏住原生介面', v == [] and pg.evaluate("!!document.getElementById('cwfm-early-hide')"), v)
    ctx.close()
    TPLSRC = open(TPL, encoding='utf-8').read()
    # ---- 完整開書：最後畫面不受影響 ----
    ctx = b.new_context(viewport={'width': 1100, 'height': 780}); pg = ctx.new_page()
    pg.goto(URL); pg.wait_for_timeout(3500)
    ok = pg.evaluate("(()=>{const v=document.querySelector('#viewer');const r=v.getBoundingClientRect();return !!document.querySelector('foliate-view')?.lastLocation && r.width>1000 && r.height>700})()")
    check('完整開書：書有開、閱讀區佔滿畫面', ok)
    pg.screenshot(path=f'v1812_final_{BROWSER}.png')
    ctx.close()
    print('SUMMARY', sum(results), '/', len(results)); b.close()
