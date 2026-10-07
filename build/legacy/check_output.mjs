// 檢查轉譯後的 cwfm-reader.js 裡，還有沒有 Safari 15 看不懂的語法。
// 用法：node check_output.mjs <檔案>
//
// 只檢查「整支程式會因此拒絕執行」的那一類（解析期錯誤）：
//   - class 裡的 static { } 區塊（Safari 16.4）
//   - 正規表示式字面值裡的往回比對 (?<= / (?<!（Safari 16.4）
// 用語法樹找，不用文字搜尋：文字搜尋會把字串、註解裡碰巧出現的同樣字樣也算進去。
import fs from 'node:fs';
import * as acorn from 'acorn';
import * as walk from 'acorn-walk';

const file = process.argv[2];
const src = fs.readFileSync(file, 'utf8');
const ast = acorn.parse(src, { ecmaVersion: 2022, sourceType: 'module', locations: true });
const problems = [];
walk.full(ast, (node) => {
    if (node.type === 'StaticBlock') problems.push(`第 ${node.loc.start.line} 行：class static 區塊`);
    if (node.type === 'Literal' && node.regex && /\(\?<[=!]/.test(node.regex.pattern)) {
        problems.push(`第 ${node.loc.start.line} 行：正規表示式往回比對 /${node.regex.pattern}/`);
    }
    // esbuild 遇到目標瀏覽器不支援的正規表示式，會改寫成 new RegExp("...") 讓解析過關，
    // 但執行到那行時一樣會拋錯，所以字串形式也要抓。
    if ((node.type === 'NewExpression' || node.type === 'CallExpression') &&
        node.callee.type === 'Identifier' && node.callee.name === 'RegExp' &&
        node.arguments[0] && node.arguments[0].type === 'Literal' &&
        typeof node.arguments[0].value === 'string' && /\(\?<[=!]/.test(node.arguments[0].value)) {
        problems.push(`第 ${node.loc.start.line} 行：RegExp 字串裡的往回比對 ${JSON.stringify(node.arguments[0].value)}`);
    }
});
if (problems.length) {
    console.error('[check_output] 錯誤：仍有 Safari 15 不支援的語法：\n  ' + problems.join('\n  '));
    process.exit(1);
}
console.log('[check_output] OK：沒有 static 區塊、沒有往回比對');
