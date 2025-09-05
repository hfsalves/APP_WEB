const acorn=require('acorn');
const src=$subset;
try{ acorn.parse(src,{ecmaVersion:'latest'}); console.log('OK'); } catch(e){ console.log('ERR', e.loc, e.message); }
