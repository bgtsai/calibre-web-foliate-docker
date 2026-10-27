import sys, json
exec(open('feat_test.py').read().split("OUT = os.environ")[0])
with sync_playwright() as p:
    b=getattr(p,BROWSER).launch()
    for touch in (True, False):
        c=b.new_context(viewport={'width':1000,'height':800},has_touch=touch)
        pg=c.new_page(); pg.add_init_script("localStorage.setItem('cwfm-settings', %s)"%json.dumps(json.dumps({"autoHideToolbar":True})))
        pg.goto(url); pg.wait_for_timeout(4000); pg.mouse.move(500,400); pg.wait_for_timeout(200)
        # key paging without any click
        s0=pg.evaluate("document.querySelector('foliate-view').renderer.start"); pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(600)
        s1=pg.evaluate("document.querySelector('foliate-view').renderer.start")
        pg.evaluate("document.dispatchEvent(new Event('fullscreenchange'))"); pg.wait_for_timeout(300)
        h0=pg.evaluate("document.querySelectorAll('.cwfm-autohidden').length")
        box=pg.locator('.cwfm-toolbar').first.bounding_box()
        x,y=box['x']+3, box['y']+box['height']/2
        print("at",pg.evaluate(f"(e=>e.className+'|'+e.tagName)(document.elementFromPoint({x},{y}))"))
        if touch: pg.touchscreen.tap(x,y)
        else: pg.mouse.move(x,y)
        pg.wait_for_timeout(4500)
        n=pg.evaluate("document.querySelectorAll('.cwfm-autohidden').length")
        print(BROWSER,'touch' if touch else 'mouse','shownAfterWake=',h0==0,'hidden=',n,'OK' if (n>0)==touch else 'FAIL','key-page',s0,'->',s1)
        if not touch:
            pg.mouse.move(500,400); pg.wait_for_timeout(4000); a=pg.evaluate("document.querySelectorAll('.cwfm-autohidden').length")
            pg.mouse.move(500,798); pg.wait_for_timeout(400); bb=pg.evaluate("document.querySelectorAll('.cwfm-autohidden').length")
            print('mouse edge wake: hidden',a,'-> after edge',bb,'OK' if a>0 and bb==0 else 'FAIL')
        else:
            pg.wait_for_timeout(1000); pg.touchscreen.tap(500,795); pg.wait_for_timeout(400); bb=pg.evaluate("document.querySelectorAll('.cwfm-autohidden').length")
            print('touch edge tap wake: after tap hidden',bb,'OK' if bb==0 else 'FAIL')
        c.close()
    b.close()
