const fs=require('fs');
const acorn=require('acorn');
const src=fs.readFileSync('static/js/monitor.js','utf8');
try{ acorn.parse(src,{ecmaVersion:'latest'}); console.log('OK'); }
catch(e){ console.log('Acorn error at', e.loc, e.message); const lines=src.split(/\r?\n/); const i=e.loc.line-3; for(let k=i;k<i+7;k++){ console.log((k+1)+': '+(lines[k]||'')); } }
