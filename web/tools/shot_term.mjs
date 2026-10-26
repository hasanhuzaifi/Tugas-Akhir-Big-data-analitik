// Render teks terminal -> PNG. Pakai: node shot_term.mjs <judul> <file-teks> <png>
import {chromium} from 'playwright';
import fs from 'fs';
const [,, title, txt, out] = process.argv;
const esc = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const body = esc(fs.readFileSync(txt, 'utf8').replace(/\x1b\[[0-9;]*m/g, ''));
const html = `<body style="margin:0;background:#1e1e1e"><div style="width:1100px;font:14px/1.45 Consolas,monospace;color:#d4d4d4">
<div style="background:#333;padding:8px 14px;color:#aaa;font:13px Segoe UI">${esc(title)}</div>
<pre style="margin:0;padding:14px;white-space:pre-wrap;word-break:break-all">${body}</pre></div></body>`;
const b = await chromium.launch(); const p = await b.newPage({viewport:{width:1100,height:200}});
await p.setContent(html); await p.locator('div').first().screenshot({path: out}); await b.close();
