// 舊版 Safari（iOS 15.x，16.4 以前）沒有內建 DecompressionStream。
// foliate-js 用 zip.js 解開 EPUB（zip 檔），解壓縮時直接 new DecompressionStream("deflate-raw")；
// 沒有內建時拿到的是 false，開書失敗：「false is not a constructor」（iPad 實機回報）。
// 這裡用 fflate（MIT，foliate-js 開 MOBI 時本來就用它）補一個，只在瀏覽器沒有內建時才生效。
// 建置時由 make_legacy.py 用 esbuild 打包成單一 IIFE，接在 cwfm-reader.js 最前面。
import { Inflate, Unzlib, Gunzip } from 'fflate';

if (typeof globalThis.DecompressionStream === 'undefined' && typeof TransformStream !== 'undefined') {
    const MAKERS = {
        'deflate-raw': () => new Inflate(),
        deflate: () => new Unzlib(),
        gzip: () => new Gunzip(),
    };
    class DecompressionStream {
        constructor(format) {
            const make = MAKERS[format];
            if (!make) throw new TypeError('[cwfm polyfill] 不支援的壓縮格式：' + format);
            let inflater;
            const ts = new TransformStream({
                start(controller) {
                    inflater = make();
                    inflater.ondata = (chunk) => { if (chunk.length) controller.enqueue(chunk); };
                },
                transform(chunk) {
                    inflater.push(chunk instanceof Uint8Array ? chunk : new Uint8Array(chunk), false);
                },
                flush() {
                    inflater.push(new Uint8Array(0), true);
                },
            });
            this.readable = ts.readable;
            this.writable = ts.writable;
        }
    }
    globalThis.DecompressionStream = DecompressionStream;
}
