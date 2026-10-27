import sys
sys.argv=[sys.argv[0], sys.argv[1], sys.argv[2], 'chromium']
exec(open('ft180.py').read().split("SET = \"window.__cwfm.settings\"")[0])
STATE['bookmarks'] = {
  'b1': {'id':'b1','cfi':'epubcfi(/6/2!/4/106)','chapter':'第一章','fraction':0.29,'created':1760000000000,'modified':1760000000000},
  'b2': {'id':'b2','cfi':'epubcfi(/6/2!/4/4,/1:2,/1:9)','excerpt':'章第1段：天地','chapter':'第一章','fraction':0.05,'created':1760000001000,'modified':1760000001000},
  'b3': {'id':'b3','cfi':'epubcfi(/6/2!/4/8,/1:0,/1:12)','excerpt':'第1章第3段：天地玄黃，宇宙','note':'這段可以引用','chapter':'第一章','fraction':0.08,'created':1760000002000,'modified':1760000002000},
}
def st(lang):
    return {'uiLanguage':lang,'themeName':'custom','customTextColor':'#A5803A','customBackgroundColor':'#060811','customTextColorEnabled':True,'customBackgroundColorEnabled':True,
            'fontSize':150 if lang=='zh' else 130,'letterSpacing':0.2 if lang=='zh' else 0,'lineSpacing':1.8,'maxColumnCount':1,'horizontalSizeMode':'content','targetContentWidthPx':640,'verticalSizeMode':'content','targetContentHeightPx':640,'tapZoneVisible':False}
import os; TM = os.environ.get('SHOT_TM') == '1'

def make_epub_en():
    import io, zipfile
    P = ["It was the best of times, it was the worst of times, it was the age of wisdom, it was the age of foolishness.",
         "It was the epoch of belief, it was the epoch of incredulity, it was the season of Light, it was the season of Darkness.",
         "There were a king with a large jaw and a queen with a plain face, on the throne of England.",
         "It was clearer than crystal to the lords of the State preserves of loaves and fishes, that things in general were settled for ever."]
    buf = io.BytesIO(); z = zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED)
    z.writestr(zipfile.ZipInfo('mimetype'), 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
    z.writestr('META-INF/container.xml', '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/c.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
    z.writestr('OEBPS/c.opf', '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="id">cwfm-test-en</dc:identifier><dc:title>A Tale of Two Cities</dc:title><dc:creator>Charles Dickens</dc:creator><dc:language>en</dc:language><meta property="dcterms:modified">2026-10-07T00:00:00Z</meta></metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="c1" href="c1.xhtml" media-type="application/xhtml+xml"/><item id="c2" href="c2.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="c1"/><itemref idref="c2"/></spine></package>')
    z.writestr('OEBPS/nav.xhtml', '<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><body><nav epub:type="toc"><ol><li><a href="c1.xhtml">Chapter 1. The Period</a></li><li><a href="c2.xhtml">Chapter 2. The Mail</a></li></ol></nav></body></html>')
    for i in (1, 2):
        paras = ''.join('<p>' + P[n % 4] + '</p>' for n in range(1, 120))
        z.writestr(f'OEBPS/c{i}.xhtml', f'<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"><head><title>c{i}</title></head><body><h1>Chapter {i}</h1>{paras}</body></html>')
    z.close(); return buf.getvalue()
EPUB_ZH = EPUB
EPUB_EN = make_epub_en()
BM_ZH = dict(STATE['bookmarks'])
BM_EN = {
  'b1': {'id':'b1','cfi':'epubcfi(/6/2!/4/106)','chapter':'Chapter 1. The Period','fraction':0.29,'created':1760000000000,'modified':1760000000000},
  'b2': {'id':'b2','cfi':'epubcfi(/6/2!/4/4,/1:0,/1:26)','excerpt':'It was the epoch of belief','chapter':'Chapter 1. The Period','fraction':0.05,'created':1760000001000,'modified':1760000001000},
  'b3': {'id':'b3','cfi':'epubcfi(/6/2!/4/8,/1:0,/1:43)','excerpt':'It was clearer than crystal to the lords of','note':'Good opening line to quote','chapter':'Chapter 1. The Period','fraction':0.08,'created':1760000002000,'modified':1760000002000},
}

with sync_playwright() as p:
    b=p.chromium.launch()
    for lang in ('zh','en'):
        globals()['EPUB'] = EPUB_EN if lang == 'en' else EPUB_ZH
        STATE['bookmarks'] = dict(BM_EN if lang == 'en' else BM_ZH)
        STATE['bookmark'] = None
        ctx=b.new_context(viewport={'width':1480,'height':1000}, device_scale_factor=2)
        pg=ctx.new_page(); pg.add_init_script("localStorage.setItem('cwfm-settings', %s)" % json.dumps(json.dumps(st(lang))))
        if TM: pg.add_init_script("Object.defineProperty(window,'__cwfmBoot',{configurable:true,get(){return this.__b},set(v){if(v)delete v.api;this.__b=v}})")  # 模擬 Tampermonkey 版：沒有伺服器 API
        pg.goto(URL); pg.wait_for_timeout(3500); pg.mouse.move(620,500)
        pg.evaluate("[...document.querySelectorAll('button')].filter(b=>/^⚠/.test(b.textContent)).forEach(b=>b.style.visibility='hidden')")  # 測試環境已知的初始鎖定訊息，截圖不需要
        # 設定面板
        btns='document.querySelectorAll(".cwfm-toolbar-top button")'
        pg.evaluate(btns+"["+btns+".length-2].click()"); pg.wait_for_timeout(900)
        pg.screenshot(path=f'readme_settings_{lang}' + ('_tm' if TM else '') + '.png')
        if TM: ctx.close(); continue
        # 錯誤紀錄卡（設定面板最後一組）
        pg.evaluate("document.querySelector('.cwfm-errlog-card').scrollIntoView({block:'center'})"); pg.wait_for_timeout(300)
        pg.evaluate("(()=>{const a=document.querySelector('.cwfm-errlog-card .cwfm-field-hint a');a.textContent='http://<calibre-web>/cwfm/api/errlog'})()")
        bx=pg.evaluate("(()=>{const r=document.querySelector('.cwfm-errlog-card').closest('.cwfm-group').getBoundingClientRect();return [r.x,r.y,r.width,r.height]})()")
        pg.screenshot(path=f'readme_errlog_{lang}.png', clip={'x':bx[0]-8,'y':bx[1]-8,'width':bx[2]+16,'height':bx[3]+16})
        pg.keyboard.press('Escape'); pg.evaluate("document.querySelectorAll('.cwfm-panel.cwfm-open').forEach(p=>p.classList.remove('cwfm-open'))"); pg.wait_for_timeout(300)
        # 目錄＋書籤卡片
        pg.evaluate(f"{VIEW}.goTo('epubcfi(/6/2!/4/2)')"); pg.wait_for_timeout(600)
        pg.click('button[aria-label="目錄"], button[aria-label="Table of Contents"]', force=True); pg.wait_for_timeout(900)
        rows=pg.query_selector_all('.cwfm-bm-row'); r=rows[1].bounding_box()
        pg.mouse.move(r['x']+60, r['y']+r['height']/2); pg.wait_for_timeout(600)
        pg.screenshot(path=f'readme_bookmarks_{lang}.png')
        ctx.close()
    b.close()
