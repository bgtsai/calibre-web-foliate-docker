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
            position: read('cwfm-position-' + bookId)
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
    }})();
    </script>
    <script type="module" src="{{{{ url_for('static', filename='js/cwfm/cwfm-reader.js') }}}}?v={bust}"></script>
"""


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

    body_end = [i for i, l in enumerate(lines) if l.strip() == "</body>"]
    if len(body_end) != 1:
        sys.exit(f"[patch_read_html] 錯誤：</body> 應該剛好 1 行，實際 {len(body_end)} 行")
    lines.insert(body_end[0], BOOT.format(marker=MARKER, bust=bust).rstrip("\n"))

    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[patch_read_html] OK → {path}（移除 {len(OLD_READER_FILES)} 個舊資源，cache_bust={bust}）")


if __name__ == "__main__":
    main(sys.argv[1:])
