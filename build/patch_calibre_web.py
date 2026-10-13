#!/usr/bin/env python3
"""建置 image 時修改 Calibre-Web 本體：掛上 cwfm 的伺服器端 API，登入頁暫存定位網址。

用法：python3 patch_calibre_web.py <calibre-web 的 cps 資料夾>

1. 複製 cwfm_api.py 到 cps/，並在 cps/main.py 的 app.register_blueprint(editbook) 後面註冊。
2. login.html 結尾加一小段腳本：網址帶 #cfi=…（定位網址）而且登入後要回到閱讀頁時，
   把定位暫存在 sessionStorage——登入表單送出時 # 片段會遺失，閱讀器開書時會取回
   （見 calibre-web-foliate-mod 的 docs/spec-v1.79.md §2）。

每個插入點都必須剛好 1 處；上游改版對不上就讓建置失敗，不要悄悄產出壞掉的 image。
"""
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
MARK = "# cwfm: blueprint"
REG_ANCHOR = "    app.register_blueprint(editbook)\n"
REG_ADD = ("    " + MARK + "\n"
           "    from .cwfm_api import cwfm_api\n"
           "    app.register_blueprint(cwfm_api)\n")

LOGIN_MARK = "<!-- cwfm: login stash -->"
LOGIN_ANCHOR = "{% endblock %}"
LOGIN_ADD = LOGIN_MARK + """
<script>
(function () {
  try {
    var m = /^#cfi=(.+)$/.exec(location.hash || '');
    var next = document.querySelector('input[name="next"]');
    var b = next && /\\/read\\/(\\d+)\\/epub/.exec(next.value || '');
    if (!m || !b) return;
    var cfi = decodeURIComponent(m[1]);
    if (!/^epubcfi\\(.+\\)$/.test(cfi)) return;
    sessionStorage.setItem('cwfm-login-cfi', JSON.stringify({ book: b[1], cfi: cfi }));
  } catch (e) { /* 暫存失敗就只是登入後不會自動跳到定位 */ }
})();
</script>
"""


def main(argv):
    if len(argv) != 1:
        sys.exit(__doc__)
    cps = pathlib.Path(argv[0])

    main_py = cps / "main.py"
    text = main_py.read_text(encoding="utf-8")
    if MARK in text:
        sys.exit("[patch_calibre_web] 錯誤：main.py 已經修改過")
    if text.count(REG_ANCHOR) != 1:
        sys.exit(f"[patch_calibre_web] 錯誤：main.py 的插入點應該剛好 1 處，實際 {text.count(REG_ANCHOR)} 處")
    main_py.write_text(text.replace(REG_ANCHOR, REG_ANCHOR + REG_ADD), encoding="utf-8")
    shutil.copyfile(HERE / "cwfm_api.py", cps / "cwfm_api.py")

    login = cps / "templates" / "login.html"
    text = login.read_text(encoding="utf-8")
    if LOGIN_MARK in text:
        sys.exit("[patch_calibre_web] 錯誤：login.html 已經修改過")
    # 最後一個 {% endblock %} 是 body 區塊的結尾，腳本放在它前面
    idx = text.rfind(LOGIN_ANCHOR)
    if idx < 0 or "{% block body %}" not in text:
        sys.exit("[patch_calibre_web] 錯誤：login.html 找不到 body 區塊")
    login.write_text(text[:idx] + LOGIN_ADD + text[idx:], encoding="utf-8")
    print("[patch_calibre_web] OK（註冊 cwfm_api、login.html 暫存定位）")


if __name__ == "__main__":
    main(sys.argv[1:])
