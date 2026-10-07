// 【診斷用，找到 iOS 15 當機原因並修好後移除】
// 在轉譯後的 cwfm-reader.js 每個頂層敘述之後插入檢查點，執行到就把「剛跑完的
// 那個敘述的起始行號」寫進 localStorage（cwfm-chk）。瀏覽器引擎直接當掉時
// 不會有任何錯誤訊息，但最後寫進去的行號會留下來，安全模式的錯誤面板會顯示它。
//
// 行號指的是「插入檢查點之前」那份檔案（esbuild 輸出），建置是固定版本、可重現的，
// 本機用同樣步驟重建就能對回是哪一個敘述；當掉的位置就在那一行的「下一個」頂層敘述裡。
//
// 用法：node add_checkpoints.mjs <輸入> <輸出>
import fs from 'node:fs';
import * as acorn from 'acorn';

const [, , inPath, outPath] = process.argv;
const src = fs.readFileSync(inPath, 'utf8');
const ast = acorn.parse(src, { ecmaVersion: 2022, sourceType: 'module', locations: true });

const CALL = (line) => `\n;window.__cwfmChk && window.__cwfmChk(${line});\n`;
let out = '';
let pos = 0;
let n = 0;
for (const node of ast.body) {
    // import/export 宣告之後插入一般敘述在語法上沒問題，但 import 會被提前處理，檢查點沒有意義
    if (node.type === 'ImportDeclaration') continue;
    out += src.slice(pos, node.end) + CALL(node.loc.start.line);
    pos = node.end;
    n++;
}
out += src.slice(pos);
fs.writeFileSync(outPath, out);
acorn.parse(out, { ecmaVersion: 2022, sourceType: 'module' });
console.log(`[add_checkpoints] OK：插入 ${n} 個檢查點 → ${outPath}`);
