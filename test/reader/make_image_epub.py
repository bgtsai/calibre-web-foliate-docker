# 測試用純圖片 EPUB 產生器（v1.87.0）：不用真書（有版權，不能放公開 repo），測試時現場產生。
# 結構比照真的漫畫 EPUB（Sigil／calibre 轉出來的）：cover.xhtml＋每頁一個 xhtml、每頁一張 1650×2390 JPEG，
# 封面＝第一頁同一張圖（彩色滿版），內頁白底＋圖案＋頁碼；有書名／作者／出版社。
# 用法：python3 make_image_epub.py <輸出.epub> [--pages 30] [--no-publisher] [--dir rtl|ltr]
# 給其他測試 import：from make_image_epub import image_epub_bytes
import io, sys, zipfile, argparse
from PIL import Image, ImageDraw, ImageFont

W, H = 1650, 2390  # 一般漫畫單頁（長寬比約 0.69）


def _font(size):
    for path in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf'):
        try: return ImageFont.truetype(path, size)
        except OSError: pass
    return ImageFont.load_default()


def _page(n):
    if n == 1:  # 彩色滿版（封面也用這張）
        im = Image.new('RGB', (W, H), (40, 90, 160)); d = ImageDraw.Draw(im)
        for i in range(0, H, 120): d.rectangle([0, i, W, i + 60], fill=(60 + i % 160, 120, 200 - i % 120))
        d.ellipse([300, 600, 1350, 1650], fill=(240, 180, 40))
    else:  # 白底＋圖案＋頁碼
        im = Image.new('RGB', (W, H), (255, 255, 255)); d = ImageDraw.Draw(im)
        m = 120
        d.rectangle([m, m, W - m, H // 2 - 30], outline=(0, 0, 0), width=8)
        d.rectangle([m, H // 2 + 30, W // 2 - 20, H - m - 200], outline=(0, 0, 0), width=8)
        d.rectangle([W // 2 + 20, H // 2 + 30, W - m, H - m - 200], outline=(0, 0, 0), width=8)
        k = n % 3
        if k == 0: d.ellipse([500, 300, 1150, 950], outline=(0, 0, 0), width=10)
        elif k == 1: d.polygon([(825, 260), (1250, 1000), (400, 1000)], outline=(0, 0, 0), width=10)
        else: d.line([(m, m), (W - m, H // 2 - 30)], fill=(0, 0, 0), width=10)
    d.text((W // 2, H - 110), str(n), fill=(0, 0, 0) if n > 1 else (255, 255, 255), font=_font(90), anchor='mm')
    buf = io.BytesIO(); im.save(buf, 'JPEG', quality=70); return buf.getvalue()


XHTML = '''<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml"><head><style>img, div{ width:100%; max-width: 100%; display: block; }</style><title>{title}</title></head>
<body><div style="text-align: center; padding: 0pt; margin: 0pt;"><img src="../Images/{img}" alt="Images to epub"/></div></body></html>'''


def image_epub_bytes(pages=30, publisher=True, direction=None, title='測試漫畫', author='測試作者', pub_name='測試出版社'):
    buf = io.BytesIO(); z = zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED)
    z.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
    z.writestr('META-INF/container.xml', '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
               '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
    man, spine = [], []
    z.writestr('OEBPS/Text/cover.xhtml', XHTML.replace('{title}', 'Cover').replace('{img}', 'p0001.jpg'))
    man.append('<item id="cover.xhtml" media-type="application/xhtml+xml" href="Text/cover.xhtml"/>'); spine.append('<itemref idref="cover.xhtml"/>')
    for n in range(1, pages + 1):
        img = 'p%04d.jpg' % n
        z.writestr('OEBPS/Images/' + img, _page(n), compress_type=zipfile.ZIP_STORED)
        z.writestr('OEBPS/Text/p%04d.xhtml' % n, XHTML.replace('{title}', 'page_%d' % n).replace('{img}', img))
        man.append('<item id="x%04d" media-type="image/jpeg" href="Images/%s"/>' % (n, img))
        man.append('<item id="p%04d.xhtml" media-type="application/xhtml+xml" href="Text/p%04d.xhtml"/>' % (n, n))
        spine.append('<itemref idref="p%04d.xhtml"/>' % n)
    man.append('<item id="ncx" media-type="application/x-dtbncx+xml" href="toc.ncx"/>')
    pub = '<dc:publisher>%s</dc:publisher>' % pub_name if publisher else ''
    ppd = ' page-progression-direction="%s"' % direction if direction else ''
    z.writestr('OEBPS/content.opf', f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="uid">
 <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
  <meta name="cover" content="x0001"/><dc:title>{title}</dc:title><dc:language>zh</dc:language>{pub}
  <dc:creator opf:role="aut">{author}</dc:creator><dc:identifier id="uid">urn:uuid:cwfm-test-image-book</dc:identifier>
 </metadata>
 <manifest>{''.join(man)}</manifest>
 <spine toc="ncx"{ppd}>{''.join(spine)}</spine>
</package>''')
    z.writestr('OEBPS/toc.ncx', '<?xml version="1.0" encoding="UTF-8"?><ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
               '<head><meta name="dtb:uid" content="urn:uuid:cwfm-test-image-book"/></head><docTitle><text>%s</text></docTitle>'
               '<navMap><navPoint id="n1" playOrder="1"><navLabel><text>%s</text></navLabel><content src="Text/p0001.xhtml"/></navPoint></navMap></ncx>' % (title, title))
    z.close(); return buf.getvalue()


_CACHE = {}


def default_image_epub():
    """測試預設用的圖片書：CWFM_EPUB 有指定就讀那本真書，否則產生一本（同一次執行只產生一次）。"""
    import os
    path = os.environ.get('CWFM_EPUB')
    if path: return open(path, 'rb').read()
    if 'b' not in _CACHE: _CACHE['b'] = image_epub_bytes()
    return _CACHE['b']


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('out'); ap.add_argument('--pages', type=int, default=30)
    ap.add_argument('--no-publisher', action='store_true'); ap.add_argument('--dir', choices=['rtl', 'ltr'])
    a = ap.parse_args()
    data = image_epub_bytes(a.pages, not a.no_publisher, a.dir)
    open(a.out, 'wb').write(data); print('OK', a.out, len(data), 'bytes')
