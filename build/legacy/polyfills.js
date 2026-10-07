/* cwfm: 舊版 Safari（iOS 15.x）缺少的內建函式代用品。
 * 只在瀏覽器本身沒有時才補上，新瀏覽器完全不受影響。
 * 這個檔案會被接在 cwfm-reader.js 最前面，所以本身只能用最舊的語法（ES5）。
 *
 * 清單來源：掃描 foliate-js 引擎實際用到、而 Safari 15.3 沒有的函式。
 * 只收 EPUB 會走到的，以及順手就能補、零風險的；PDF 專用的
 * （AbortSignal.any、ArrayBuffer.transferToFixedLength、迭代器輔助函式）不補，
 * 舊 iOS 上開 PDF 可能仍會出錯——這是刻意的範圍取捨。
 */
(function () {
    function def(obj, name, fn) {
        if (obj && typeof obj[name] !== 'function') {
            Object.defineProperty(obj, name, { value: fn, writable: true, configurable: true, enumerable: false });
        }
    }
    function at(i) {
        var n = this.length >>> 0;
        var k = Math.trunc(Number(i)) || 0;
        if (k < 0) k += n;
        return k < 0 || k >= n ? undefined : this[k];
    }
    // Safari 15.4 才有 .at()
    def(Array.prototype, 'at', at);
    def(String.prototype, 'at', function (i) { var r = at.call(String(this), i); return r; });
    if (typeof Int8Array !== 'undefined') def(Object.getPrototypeOf(Int8Array.prototype), 'at', at);

    // Safari 15.4
    def(Array.prototype, 'findLast', function (fn, thisArg) {
        for (var i = this.length - 1; i >= 0; i--) if (fn.call(thisArg, this[i], i, this)) return this[i];
        return undefined;
    });
    def(Array.prototype, 'findLastIndex', function (fn, thisArg) {
        for (var i = this.length - 1; i >= 0; i--) if (fn.call(thisArg, this[i], i, this)) return i;
        return -1;
    });
    def(Object, 'hasOwn', function (o, k) { return Object.prototype.hasOwnProperty.call(Object(o), k); });

    // Safari 17.4（EPUB 中繼資料解析會用到）
    def(Object, 'groupBy', function (items, fn) {
        var out = Object.create(null), i = 0;
        Array.from(items, function (v) {
            var key = fn(v, i++);
            (out[key] || (out[key] = [])).push(v);
        });
        return out;
    });
    def(Map, 'groupBy', function (items, fn) {
        var out = new Map(), i = 0;
        Array.from(items, function (v) {
            var key = fn(v, i++);
            if (!out.has(key)) out.set(key, []);
            out.get(key).push(v);
        });
        return out;
    });
    def(Promise, 'withResolvers', function () {
        var res, rej;
        var p = new this(function (a, b) { res = a; rej = b; });
        return { promise: p, resolve: res, reject: rej };
    });
    def(Promise, 'try', function (fn) {
        var args = Array.prototype.slice.call(arguments, 1), C = this;
        return new C(function (a) { a(fn.apply(undefined, args)); });
    });
    def(URL, 'parse', function (u, base) {
        try { return base === undefined ? new URL(u) : new URL(u, base); } catch (e) { return null; }
    });
    def(Map.prototype, 'getOrInsertComputed', function (k, fn) {
        if (!this.has(k)) this.set(k, fn(k));
        return this.get(k);
    });
    if (typeof WeakMap !== 'undefined') def(WeakMap.prototype, 'getOrInsertComputed', function (k, fn) {
        if (!this.has(k)) this.set(k, fn(k));
        return this.get(k);
    });
})();
