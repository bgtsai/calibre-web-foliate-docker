#!/usr/bin/env python3
"""建置 image 時就地修改 Calibre-Web 的 epub 閱讀頁（read.html）。

用法：python3 patch_read_html.py <read.html 路徑> <cache_bust 字串>

另外在 <head> 一開頭插入同資料夾的 error_panel.html（錯誤面板，給沒有開發者
工具的 iPad 看錯誤用），它必須比任何其他腳本都早執行。

做法刻意選「修改原檔」而不是「整份換掉」：
- 新版 mod 依賴原頁面的結構：#main 底下的 #viewer（掛閱讀器）、
  input[name=csrf_token]（同步書籤）、window.calibre.bookmark（伺服器書籤）。
  保留原頁面，就跟 Tampermonkey 版實際執行的環境完全相同。
- 上游改版時，只要這幾個錨點還在就能繼續用；錨點不見了，建置直接失敗，
  不會悄悄產出一個壞掉的頁面。

拿掉的資源清單跟 mod 外層腳本的 OLD_READER_URL_PATTERNS 一致（舊 epub.js
閱讀器整套）。Tampermonkey 版是在瀏覽器端攔截移除，這裡在伺服器端直接刪掉，
瀏覽器從頭到尾不會下載、執行它們。頁面內聯的那幾段舊設定腳本保留不動——
Tampermonkey 版同樣沒有動它們，維持相同的已驗證環境。
"""
import pathlib
import re
import sys

MARKER = "<!-- cwfm: foliate-js reader -->"
ERROR_PANEL = (pathlib.Path(__file__).resolve().parent / "error_panel.html").read_text(encoding="utf-8")

OLD_READER_FILES = [
    "css/reader.css",
    "js/libs/jquery.min.js",
    "js/compress/jszip_epub.min.js",
    "js/libs/epub.min.js",
    "js/libs/reader.min.js",
    "js/reading/epub.js",
]

# 開機段落：在 module 執行前準備好 window.__cwfmBoot，並接手 mod 原本交給
# Tampermonkey GM_setValue 的寫入事件（cwfm:gm-set），改存 localStorage。
# 讀寫失敗一律印出原因，不靜默吞掉。
BOOT = """    {marker}
    <script type="text/javascript">
    (function () {{
        function read(key) {{
            try {{
                var raw = localStorage.getItem(key);
                return raw === null ? null : JSON.parse(raw);
            }} catch (e) {{
                console.error('[cwfm:storage] 讀取失敗', key, e);
                return null;
            }}
        }}
        var bookId = '{{{{ bookid }}}}';
        window.__cwfmBoot = {{
            bookId: bookId,
            settings: read('cwfm-settings'),
            position: read('cwfm-position-' + bookId),
            bookdata: read('cwfm-bookdata-' + bookId),
            api: "{{{{ url_for('cwfm_api.base') }}}}"
        }};
        document.addEventListener('cwfm:gm-set', function (e) {{
            var d = e.detail || {{}};
            if (!d.key) {{ console.warn('[cwfm:storage] 寫入請求沒有 key，略過', d); return; }}
            try {{
                localStorage.setItem(d.key, JSON.stringify(d.value));
            }} catch (err) {{
                console.error('[cwfm:storage] 寫入失敗', d.key, err);
            }}
        }});
        // 安全模式（網址加 ?cwfm=safe）不載入閱讀器，只看錯誤面板留下的上一次紀錄。
        if (window.__cwfmSafeMode) {{
            var ld = document.getElementById('cwfm-loading');
            if (ld) ld.parentNode.removeChild(ld);
        }} else {{
            var s = document.createElement('script');
            s.type = 'module';
            s.src = "{{{{ url_for('static', filename='js/cwfm/cwfm-reader.js') }}}}?v={bust}";
            document.body.appendChild(s);
        }}
    }})();
    </script>
"""


# v1.80.5：<head> 錯誤面板之後——(1) 標記這是 Docker 版（Tampermonkey 腳本看到就整支停止，兩個同時跑會互相干擾）；
# (2) 頁面一開始就先下載書檔，跟閱讀器程式本身的下載重疊（閱讀器讀 window.__cwfmBookPrefetch）。安全模式不下載。
EARLY = """    <meta name="cwfm-docker" content="1">
    <script type="text/javascript">
    if (!window.__cwfmSafeMode) {{
        try {{ window.__cwfmBookPrefetch = fetch('/show/{{{{ bookid }}}}/epub/file.epub', {{ credentials: 'same-origin' }}); }}
        catch (e) {{ console.error('[cwfm:load] 預先下載書檔失敗', e); }}
    }}
    </script>"""

# v1.80.5：載入提示——一開頁就看得到（大檔案下載、解壓期間不要一片黑），閱讀器開好書後移除（安全模式由開機段落移除）。
# 跟 mod 的 Tampermonkey 外層插入的是同一份樣子；文字之後由閱讀器更新成下載百分比。
LOADING = """    <div id="cwfm-loading" data-cwfm-owned="true" style="position:fixed;left:0;top:0;right:0;bottom:0;z-index:999990;display:flex;align-items:center;justify-content:center;pointer-events:none;font:15px/1.5 sans-serif;color:#8a8a8a"><div style="display:flex;align-items:center;gap:10px"><span style="width:18px;height:18px;border:2px solid currentColor;border-right-color:transparent;border-radius:50%;display:inline-block;animation:cwfm-spin 0.8s linear infinite"></span><span id="cwfm-loading-text">正在載入書籍… Loading…</span></div><style>@keyframes cwfm-spin{{to{{transform:rotate(360deg)}}}}</style></div>"""


def main(argv):
    if len(argv) != 2:
        sys.exit(__doc__)
    path, bust = pathlib.Path(argv[0]), argv[1]
    text = path.read_text(encoding="utf-8")

    if MARKER in text:
        sys.exit("[patch_read_html] 錯誤：已經修改過（找到標記），不重複套用")

    lines = text.split("\n")
    for f in OLD_READER_FILES:
        pat = re.compile(r"^\s*<(script|link)\b[^>]*filename='" + re.escape(f) + r"'[^>]*>(\s*</script>)?\s*$")
        hits = [i for i, l in enumerate(lines) if pat.match(l)]
        if len(hits) != 1:
            sys.exit(f"[patch_read_html] 錯誤：{f} 的標籤應該剛好 1 行，實際 {len(hits)} 行")
        del lines[hits[0]]

    for anchor in ['<div id="main">', '<div id="viewer"></div>', 'name="csrf_token"', "window.calibre = {"]:
        if sum(anchor in l for l in lines) != 1:
            sys.exit(f"[patch_read_html] 錯誤：mod 依賴的錨點不是剛好 1 個：{anchor}")

    head = [i for i, l in enumerate(lines) if l.strip() == "<head>"]
    if len(head) != 1:
        sys.exit(f"[patch_read_html] 錯誤：<head> 應該剛好 1 行，實際 {len(head)} 行")
    lines.insert(head[0] + 1, ERROR_PANEL.rstrip("\n"))
    lines.insert(head[0] + 2, EARLY.format().rstrip("\n"))
    # 放在 <body> 一開頭：放進 #main 裡會被頁面原本的樣式（隱藏未初始化的閱讀區）一起藏掉
    body_open = [i for i, l in enumerate(lines) if l.lstrip().startswith("<body")]
    if len(body_open) != 1 or not lines[body_open[0]].rstrip().endswith(">"):
        sys.exit(f"[patch_read_html] 錯誤：<body> 開頭標籤應該剛好 1 行，實際 {len(body_open)} 行")
    lines.insert(body_open[0] + 1, LOADING.format().rstrip("\n"))

    body_end = [i for i, l in enumerate(lines) if l.strip() == "</body>"]
    if len(body_end) != 1:
        sys.exit(f"[patch_read_html] 錯誤：</body> 應該剛好 1 行，實際 {len(body_end)} 行")
    lines.insert(body_end[0], BOOT.format(marker=MARKER, bust=bust).rstrip("\n"))

    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[patch_read_html] OK → {path}（移除 {len(OLD_READER_FILES)} 個舊資源，cache_bust={bust}）")


if __name__ == "__main__":
    main(sys.argv[1:])
