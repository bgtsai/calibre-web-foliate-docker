#!/usr/bin/env python3
"""把 cwfm-reader.js 轉成舊版 Safari（iOS 15）也能執行的版本。

用法：python3 make_legacy.py <輸入 js> <輸出 js> <node_modules 所在目錄>

步驟（每一步失敗都中止建置）：
1. 手動改寫唯一一處正規表示式往回比對（esbuild 不會轉換正規表示式），
   並拿掉全檔唯一的頂層 await（見下方 TLA_OLD 的說明）
2. esbuild 以 target=safari15 轉譯語法（主要是 class static 區塊）
   不壓縮、保留排版：iPad 錯誤面板回報的行號，要能在這邊重現同一份檔案後對回原始碼
3. check_output.mjs 用語法樹確認沒有殘留 Safari 15 看不懂的語法
4. 最前面接上 polyfills.js（缺少的內建函式代用品）與 decompression_polyfill.mjs
   （DecompressionStream，用 fflate 實作，esbuild 打包成 IIFE）

【診斷用】環境變數 CWFM_CHECKPOINTS=1 時，在第 3 步之後插入檢查點
（add_checkpoints.mjs），用來找 iOS 15 載入時引擎當掉的位置。找到原因後移除。
"""
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent

# 往回比對 (?<=X)-epub- 只要求前面是 X、不吃掉 X；改成把 X 一起比對再用 $1 放回去，
# 結果相同。X 是 { 空白 ; 其中一個字元，兩次命中之間不會共用同一個字元，所以不會漏換。
LOOKBEHIND_OLD = '.replace(/(?<=[{\\s;])-epub-/gi, "")'
LOOKBEHIND_NEW = '.replace(/([{\\s;])-epub-/gi, "$1")'


# 頂層 await：foliate-js 自帶的 PDF 支援在模組載入時就 await 下載兩個 pdf.js 樣式檔。
# iOS 15.3 的 WebKit 執行到這裡整個頁面當掉（沒有任何錯誤訊息；用檢查點定位到這個敘述）。
# 在 Calibre-Web 裡這段程式用不到：epub 頁只會開 epub，PDF 由 Calibre-Web 自己的
# readpdf.html 處理；而且這兩個檔案本來就沒有隨附（一直是 404），拿到的是錯誤頁文字。
# 改成空字串：不下載、不 await，對 EPUB 與實際的 PDF 閱讀都沒有影響。
TLA_OLD = (
    '  Sc = await Ac(vc("text_layer_builder.css")),\n'
    '  Tc = await Ac(vc("annotation_layer_builder.css")),\n'
)
TLA_NEW = (
    '  Sc = "", // [cwfm-docker] 原為頂層 await 下載 pdf.js 樣式，iOS 15 會當機，見 make_legacy.py\n'
    '  Tc = "",\n'
)


def run(cmd, label):
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if out:
        print(out)
    if r.returncode != 0:
        sys.exit(f"[make_legacy] 錯誤：{label} 失敗（exit {r.returncode}）")


def main(argv):
    if len(argv) != 3:
        sys.exit(__doc__)
    src_path, out_path, nm = pathlib.Path(argv[0]), pathlib.Path(argv[1]), pathlib.Path(argv[2])

    text = src_path.read_text(encoding="utf-8")
    n = text.count(LOOKBEHIND_OLD)
    if n != 1:
        sys.exit(f"[make_legacy] 錯誤：往回比對那一行應該剛好 1 處，實際 {n} 處（引擎改版了，要重新確認改寫方式）")
    text = text.replace(LOOKBEHIND_OLD, LOOKBEHIND_NEW)
    n = text.count(TLA_OLD)
    if n != 1:
        sys.exit(f"[make_legacy] 錯誤：頂層 await 那兩行應該剛好 1 處，實際 {n} 處（引擎改版了，要重新確認）")
    text = text.replace(TLA_OLD, TLA_NEW)

    tmp_in = out_path.with_suffix(".pre.js")
    tmp_out = out_path.with_suffix(".esb.js")
    tmp_in.write_text(text, encoding="utf-8")

    run([str(nm / ".bin" / "esbuild"), str(tmp_in), "--format=esm", "--target=safari15",
         "--charset=utf8", "--log-level=warning", f"--outfile={tmp_out}"], "esbuild 轉譯")
    run(["node", str(HERE / "check_output.mjs"), str(tmp_out)], "語法檢查")
    if os.environ.get("CWFM_CHECKPOINTS") == "1":
        run(["node", str(HERE / "add_checkpoints.mjs"), str(tmp_out), str(tmp_out)], "插入檢查點")

    tmp_dec = out_path.with_suffix(".dec.js")
    run([str(nm / ".bin" / "esbuild"), str(HERE / "decompression_polyfill.mjs"), "--bundle", "--format=iife",
         "--target=safari15", "--minify", "--legal-comments=inline", "--log-level=warning",
         f"--outfile={tmp_dec}"], "打包 DecompressionStream 代用品")
    poly = (HERE / "polyfills.js").read_text(encoding="utf-8")
    dec = tmp_dec.read_text(encoding="utf-8")
    out_path.write_text(poly + "\n" + dec + "\n" + tmp_out.read_text(encoding="utf-8"), encoding="utf-8")
    tmp_dec.unlink()
    tmp_in.unlink()
    tmp_out.unlink()
    print(f"[make_legacy] OK → {out_path}（{out_path.stat().st_size} bytes）")


if __name__ == "__main__":
    main(sys.argv[1:])
