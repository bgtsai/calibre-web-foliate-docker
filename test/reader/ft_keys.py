# v1.82.2：快速鍵在各種介面狀態下該不該翻頁（三瀏覽器）
# 用法：python3 ft_keys.py <dp.html> <dr.js> <瀏覽器>
# A：第一章 iframe 漏掛監聽（Firefox／WebKit 開書後焦點在書本裡，按鍵沒反應）
# B：焦點在底部進度條時，快速鍵要照常（不是瀏覽器原生推滑桿），Ctrl+M 也要能開書籤
import sys
exec(open('ft180.py').read().split("SET = \"window.__cwfm.settings\"")[0])
V="document.querySelector('foliate-view')"
POS=f"(()=>{{const r={V}.renderer;return [{V}.lastLocation?.index??-1, r.page, r.pages]}})()"
def flips(pg):
    a=pg.evaluate(POS)
    if a[1] >= a[2]-3 and not pg.evaluate("!!document.querySelector('.cwfm-settings-panel.cwfm-open,.cwfm-confirm-overlay')"):  # 快到章尾：先跳回第一章中段，避免碰到全書結尾
        f=pg.evaluate("document.activeElement"); pg.evaluate(f"{V}.goTo('epubcfi(/6/2!/4/40)')"); pg.wait_for_timeout(1200); a=pg.evaluate(POS)
    pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(700); c=pg.evaluate(POS)
    nxt = (c[0]==a[0] and c[1]==a[1]+1) or (c[0]==a[0]+1 and a[1]>=a[2]-2)  # 剛好下一頁（或跨到下一章開頭）
    where=pg.evaluate("(()=>{const ae=document.activeElement;const d=document.querySelector('foliate-view').renderer.getContents()[0]?.doc;return (ae?.tagName||'')+(ae?.className?'.'+String(ae.className).split(' ')[0]:'')+(d&&d.hasFocus()?' [iframe]':'')})()")
    return nxt, where+' '+str(a)+'->'+str(c)
def btn(pg,label): pg.click(f'button[aria-label="{label}"]',force=True); pg.wait_for_timeout(500)
# 有閱讀進度（伺服器書籤）才會觸發 A：開書時先還原位置、第一章在掛監聽之前就載入完；從頭開書時剛好晚於掛監聽，測不出來
STATE['bookmark'] = 'epubcfi(/6/2!/4/40)'
with sync_playwright() as p:
  for BR in [sys.argv[3]]:
    b=getattr(p,BR).launch(); ctx=b.new_context(viewport={'width':1200,'height':800}); pg=ctx.new_page()
    pg.goto(URL); pg.wait_for_timeout(4000)
    print('==',BR, pg.evaluate("[...document.querySelectorAll('button[aria-label]')].map(b=>b.getAttribute('aria-label')).slice(0,14).join('|')"))
    R=[]
    def run(name,expect=True): ok,w=flips(pg); R.append((name,ok==expect,ok,w)); print(('OK  ' if ok==expect else 'FAIL'),name,'flipped=',ok,'focus=',w)
    run('1 開書後直接按')
    # 滾輪：滑鼠在第一章內文上滾一下要翻頁（同一個漏掛）
    a=pg.evaluate(POS); pg.mouse.move(600,400); pg.mouse.wheel(0,120); pg.wait_for_timeout(900); c=pg.evaluate(POS)
    R.append(('1b 第一章內文上滾輪',c!=a,0,'')); print(('OK  ' if c!=a else 'FAIL'),'1b 第一章內文上滾輪',a,'->',c)
    pg.mouse.click(600,400); pg.wait_for_timeout(500); run('2 點內文後')
    pg.evaluate(f"{V}.goTo('epubcfi(/6/4!/4/20)')"); pg.wait_for_timeout(1500); pg.mouse.click(600,400); pg.wait_for_timeout(400); run('3 換章後點內文')
    btn(pg,'Table of Contents'); run('4 目錄開著')
    pg.click('.cwfm-panel.cwfm-open a, .cwfm-panel.cwfm-open [role=treeitem], .cwfm-panel.cwfm-open li >> nth=0',force=True); pg.wait_for_timeout(1200); run('5 點目錄項目跳轉後')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    sl=pg.locator('.cwfm-progress-wrap input[type=range]'); bb=sl.bounding_box(); pg.mouse.click(bb['x']+bb['width']*0.3,bb['y']+bb['height']/2); pg.wait_for_timeout(1200); run('6 拖／點進度條後')
    for k,d in (('ArrowRight',1),('ArrowLeft',-1),('PageDown',1),('PageUp',-1)):
        a=pg.evaluate(POS); pg.keyboard.press(k); pg.wait_for_timeout(900); c=pg.evaluate(POS); ok=c[1]==a[1]+d and c[0]==a[0]
        R.append(('6'+k,ok,0,'')); print(('OK  ' if ok else 'FAIL'),'6 焦點在進度條：'+k+' 剛好翻一頁',a,'->',c, pg.evaluate("document.activeElement.tagName"))
    pg.keyboard.press('Control+m'); pg.wait_for_timeout(600); ok=pg.evaluate("!!document.querySelector('.cwfm-confirm-overlay')")
    R.append(('6bm',ok,0,'')); print(('OK  ' if ok else 'FAIL'),'6 焦點在進度條：Ctrl+M 開書籤對話框')
    if ok: pg.click('.cwfm-confirm-overlay .cwfm-confirm-cancel'); pg.wait_for_timeout(400)
    btn(pg,'Settings'); run('7 設定面板開著（應該不翻）',expect=False)
    pg.locator('.cwfm-settings-panel .cwfm-value-input').first.click(); pg.wait_for_timeout(200)
    btn(pg,'Settings'); run('8 改數值框後用工具列鈕關設定')
    btn(pg,'Settings'); pg.locator('.cwfm-settings-panel .cwfm-value-input').first.click(); pg.click('.cwfm-settings-panel .cwfm-close-btn'); pg.wait_for_timeout(400); run('9 改數值框後用 ✕ 關設定')
    btn(pg,'Search'); pg.fill('.cwfm-search-panel input','天地'); pg.press('.cwfm-search-panel input','Enter'); pg.wait_for_timeout(2000)
    pg.locator('.cwfm-search-hit').nth(3).click(); pg.wait_for_timeout(1200); run('10 點搜尋結果後（搜尋面板開著）')
    pg.click('.cwfm-search-panel .cwfm-close-btn'); pg.wait_for_timeout(400); run('11 關搜尋面板後')
    pg.keyboard.press('Control+m'); pg.wait_for_timeout(600); run('12 書籤對話框開著（應該不翻）',expect=False)
    pg.click('.cwfm-confirm-overlay .cwfm-confirm-cancel'); pg.wait_for_timeout(500); run('13 取消書籤對話框後')
    btn(pg,'Table of Contents'); pg.keyboard.press('Escape'); pg.wait_for_timeout(400); run('14 Esc 關目錄後')
    pg.mouse.click(600,400); pg.wait_for_timeout(300); btn(pg,'Table of Contents'); run('15 先點內文、再開目錄')
    print('SUMMARY',sum(r[1] for r in R),'/',len(R)); b.close()
