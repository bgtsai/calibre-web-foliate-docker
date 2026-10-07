#!/usr/bin/env python3
"""從 calibre-web-foliate-mod 的原始碼組出 Docker 版用的 cwfm-reader.js。

用法：python3 make_reader.py <mod_dir> <output_js> <version_label>

組法跟 mod 的部署腳本（calibre-web-foliate-mod.user.js 的
buildCombinedScriptSource()）完全相同：foliate-js 本體 + 換行 + 應用程式
邏輯，合併成同一個 ES module。差別只在佔位字串換成什麼：

  Tampermonkey 版：插入頁面前，外層腳本把 GM_getValue 讀到的值直接寫死進去
  Docker 版　　　：改成讀 read.html 開機段落準備好的 window.__cwfmBoot

為什麼不另寫一份 Docker 專用的 app-ui.js：mod 的 src/ 是唯一來源，在這裡
複製一份就會跟 mod 脫節（mod v1.76.7～15 被整批覆蓋就是這種事）。

每個替換都檢查「剛好命中 1 次」，命中 0 次或多次一律中止建置——mod 那邊
改了宣告寫法時，寧可 build 失敗，也不要產出一份佔位字串沒換到、執行時才
壞掉的檔案（舊版 Docker 黑畫面就是佔位字串沒換到造成的）。
"""
import json
import pathlib
import re
import sys


def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        sys.exit(f"[make_reader] 錯誤：{label} 應該剛好出現 1 次，實際 {n} 次：{old!r}")
    return text.replace(old, new)


def main(argv):
    if len(argv) != 3:
        sys.exit(__doc__)
    mod_dir, out_path, version = pathlib.Path(argv[0]), pathlib.Path(argv[1]), argv[2]

    bundle = (mod_dir / "foliate-src" / "bundle.js").read_text(encoding="utf-8")
    app = (mod_dir / "src" / "app-ui.js").read_text(encoding="utf-8")

    # 跟 mod 外層腳本一樣：VIEWER_SELECTOR 全部替換（mod 用 /g）。
    if "__VIEWER_SELECTOR__" not in app:
        sys.exit("[make_reader] 錯誤：app-ui.js 找不到 __VIEWER_SELECTOR__")
    app = app.replace("__VIEWER_SELECTOR__", "#viewer")

    # 以下全部連等號、分號一起比對，理由同 mod：說明註解裡可能提到同一串文字。
    app = replace_once(app, "const BOOK_ID = '__BOOK_ID__';",
                       "const BOOK_ID = String(window.__cwfmBoot.bookId);", "BOOK_ID 宣告")
    app = replace_once(app, '= "__INITIAL_SETTINGS__";',
                       "= window.__cwfmBoot.settings;", "INITIAL_SETTINGS 宣告")
    app = replace_once(app, '= "__INITIAL_POSITION__";',
                       "= window.__cwfmBoot.position;", "INITIAL_POSITION 宣告")
    app = replace_once(app, '= "__CWFM_VERSION__";',
                       "= " + json.dumps(version) + ";", "CWFM_VERSION 宣告")

    leftover = sorted(set(re.findall(
        r"__(?:BOOK_ID|VIEWER_SELECTOR|INITIAL_SETTINGS|INITIAL_POSITION|CWFM_VERSION)__", app)))
    if leftover:
        sys.exit(f"[make_reader] 錯誤：替換後仍有佔位字串殘留：{leftover}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(bundle + "\n" + app, encoding="utf-8")
    print(f"[make_reader] OK → {out_path}（{out_path.stat().st_size} bytes，版本 {version}）")


if __name__ == "__main__":
    main(sys.argv[1:])
