import sys
exec(open('ft180.py').read().split("SET = \"window.__cwfm.settings\"")[0])
with sync_playwright() as p:
    b = getattr(p, BROWSER).launch(); ctx = b.new_context(viewport={'width': 1100, 'height': 780}); pg = ctx.new_page()
    pg.goto(URL); pg.wait_for_timeout(3500)
    pg.click('button[aria-label="搜尋"], button[aria-label="Search"]', force=True); pg.wait_for_timeout(400)
    inp = '.cwfm-search-panel input'
    pg.fill(inp, 'zzqqxx'); pg.press(inp, 'Enter')
    seen = set()
    for _ in range(40):
        seen.add(pg.evaluate("(()=>{const e=document.querySelector('.cwfm-search-results .cwfm-empty-state');return e&&e.style.display!=='none'?e.textContent:''})()")); pg.wait_for_timeout(50)
    final = pg.evaluate("document.querySelector('.cwfm-search-results .cwfm-empty-state')?.textContent")
    check('搜尋沒結果：顯示沒有符合搜尋條件', final == 'Nothing matches your search', (final, seen))
    pg.fill(inp, '天地'); pg.press(inp, 'Enter'); pg.wait_for_timeout(2500)
    check('有結果時不顯示空狀態', pg.evaluate("getComputedStyle(document.querySelector('.cwfm-search-results .cwfm-empty-state')).display") == 'none')
    print('SUMMARY', sum(results), '/', len(results)); b.close()
