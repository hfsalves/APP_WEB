const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'static', 'js', 'dashboard.js'), 'utf8');
let active = 0;
let maximumActive = 0;

const context = {
  console,
  setTimeout,
  clearTimeout,
  document: {
    querySelector: () => null,
    addEventListener: () => {},
  },
  fetch: async () => {
    active += 1;
    maximumActive = Math.max(maximumActive, active);
    await new Promise((resolve) => setTimeout(resolve, 15));
    active -= 1;
    return {
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ columns: [], rows: [] }),
    };
  },
};
vm.createContext(context);
vm.runInContext(source, context);

(async () => {
  await Promise.all([
    context.runWidget('MAPA_GESTAO_GR_RESUMO', { ano: 2026 }),
    context.runWidget('MAPA_GESTAO_GR_TOP_LUCRO', { ano: 2026 }),
    context.runWidget('MAPA_GESTAO_GR_TOP_PREJUIZO', { ano: 2026 }),
  ]);
  assert.equal(maximumActive, 1);
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
