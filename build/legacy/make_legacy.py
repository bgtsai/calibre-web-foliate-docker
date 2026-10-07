#!/usr/bin/env python3
"""把 cwfm-reader.js 轉成舊版 Safari（iOS 15）也能執行的版本。

用法：python3 make_legacy.py <輸入 js> <輸出 js> <node_modules 所在目錄>

步驟（每一步失敗都中止建置）：
1. 手動改寫唯一一處正規表示式往回比對（esbuild 不會轉換正規表示式）
2. esbuild 以 target=safari15 轉譯語法（主要是 class static 區塊）
   不壓縮、保留排版：iPad 錯誤面板回報的行號，要能在這邊重現同一份檔案後對回原始碼
3. check_output.mjs 用語法樹確認沒有殘留 Safari 15 看不懂的語法
4. 最前面接上 polyfills.js（缺少的內建函式代用品）

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

    tmp_in = out_path.with_suffix(".pre.js")
    tmp_out = out_path.with_suffix(".esb.js")
    tmp_in.write_text(text, encoding="utf-8")

    run([str(nm / ".bin" / "esbuild"), str(tmp_in), "--format=esm", "--target=safari15",
         "--charset=utf8", "--log-level=warning", f"--outfile={tmp_out}"], "esbuild 轉譯")
    run(["node", str(HERE / "check_output.mjs"), str(tmp_out)], "語法檢查")
    if os.environ.get("CWFM_CHECKPOINTS") == "1":
        run(["node", str(HERE / "add_checkpoints.mjs"), str(tmp_out), str(tmp_out)], "插入檢查點")

    poly = (HERE / "polyfills.js").read_text(encoding="utf-8")
    out_path.write_text(poly + "\n" + tmp_out.read_text(encoding="utf-8"), encoding="utf-8")
    tmp_in.unlink()
    tmp_out.unlink()
    print(f"[make_legacy] OK → {out_path}（{out_path.stat().st_size} bytes）")


if __name__ == "__main__":
    main(sys.argv[1:])
