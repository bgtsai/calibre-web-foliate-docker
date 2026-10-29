# v1.82.1：標籤上的小圖示（改名、覆蓋更新、刪除、上傳徽章）與步進器 − ＋ 都是 SVG，
# 墨水的垂直中心要跟所在標籤／步進器的中心一致（±0.5px；放大 4 倍截圖逐像素量）
# 用法：python3 ft_icons.py <dp.html> <dr.js> <瀏覽器>
import sys,io,os
BR=sys.argv[3] if len(sys.argv)>3 else 'chromium'; OUTDIR=os.environ.get('OUT_DIR','/tmp')
exec(open('ft180.py').read().split("SET = \"window.__cwfm.settings\"")[0])
from PIL import Image
def measure(pg, parent_js, name):
    # parent_js：回傳父元素（標籤或步進器）的 JS 運算式；量父元素內每個按鈕／圖示的墨水，相對父元素中心
    pg.evaluate(f"window.__mp = {parent_js}")
    # v1.85.0：設定檔分組多了「新書開啟時套用」，下面的分組可能在畫面外——先捲進畫面再截圖
    pg.evaluate("__mp.scrollIntoView({block:'center'})"); pg.wait_for_timeout(200)
    # 量的是截圖上的墨水：元素落在小數像素位置時，WebKit 的反鋸齒會讓墨水中心偏 0.5px 左右，捲動量對齊到元素在整數像素上
    pg.evaluate("(()=>{let s=__mp.parentElement;while(s&&s.scrollHeight<=s.clientHeight)s=s.parentElement;const y=__mp.getBoundingClientRect().y;if(s)s.scrollTop+=y-Math.round(y);})()"); pg.wait_for_timeout(200)
    pb=pg.evaluate("(()=>{const r=__mp.getBoundingClientRect();return [r.x,r.y,r.width,r.height]})()")
    kids=pg.evaluate("""(()=>{const r0=__mp.getBoundingClientRect();return [...__mp.querySelectorAll('button,.cwfm-keychip-icon')].map(e=>{const r=e.getBoundingClientRect();return [e.className.split(' ')[0],r.x-r0.x,r.y-r0.y,r.width,r.height]})})()""")
    png=pg.screenshot(clip=dict(x=pb[0],y=pb[1],width=pb[2],height=pb[3])); im=Image.open(io.BytesIO(png)).convert('RGB'); s=im.size[0]/pb[2]
    res=[]
    for cls,x,y,w,h in kids:
        X0,X1,Y0,Y1=int(x*s)+2,int((x+w)*s)-2,int(y*s)+2,int((y+h)*s)-2
        bg=im.getpixel((X0,Y0))
        pts=[(a,c) for c in range(Y0,Y1) for a in range(X0,X1) if sum(abs(u-v) for u,v in zip(im.getpixel((a,c)),bg))>150]
        if not pts: res.append((cls,'no ink')); continue
        ys=[q[1] for q in pts]; xs=[q[0] for q in pts]
        dy=((min(ys)+max(ys)+1)/2)/s-pb[3]/2
        res.append((cls, round(dy,2)))
        check(f'{name} {cls} 垂直置中', abs(dy) <= 0.5, round(dy,2))
    im.save(f'{OUTDIR}/icons_{name}_{BR}.png')
with sync_playwright() as p:
    b=getattr(p,BR).launch(); ctx=b.new_context(viewport={'width':1400,'height':900},device_scale_factor=4); pg=ctx.new_page()
    pg.goto(URL); pg.wait_for_timeout(3500)
    pg.click('button[aria-label="Settings"]',force=True); pg.wait_for_timeout(600)
    pg.click("text=+ New / Save As Profile"); pg.wait_for_timeout(300); pg.fill('.cwfm-prompt-input','Novel'); pg.click('.cwfm-confirm-ok'); pg.wait_for_timeout(400)
    pg.evaluate("""(()=>{const s=window.__cwfm.settings; s.uploadedFonts.push({id:'f1',fileName:'a.ttf',format:'ttf',name:'TestFont'}); window.__cwfm.refreshSettingsPanel();})()"""); pg.wait_for_timeout(300)
    pg.add_style_tag(content='.cwfm-keychip-rename{opacity:1!important;transition:none!important}'); pg.mouse.move(5,5); pg.wait_for_timeout(300)
    measure(pg,"document.querySelector('.cwfm-group .cwfm-keychip')",'profile')
    measure(pg,"document.querySelector('.cwfm-keychip-icon').closest('.cwfm-keychip')",'font')
    measure(pg,"[...document.querySelectorAll('.cwfm-keylist .cwfm-keychip')].find(c=>c.textContent.includes('ArrowLeft'))",'key')
    measure(pg,"document.querySelector('.cwfm-stepper')",'stepper')
    check('圖示都是 SVG（沒有文字符號）', pg.evaluate("[...document.querySelectorAll('.cwfm-keychip-rename,.cwfm-keychip-remove,.cwfm-keychip-icon,.cwfm-stepper-btn')].every(e=>e.querySelector('svg') && !e.textContent.trim())"))
    print('SUMMARY', sum(results), '/', len(results)); b.close()
