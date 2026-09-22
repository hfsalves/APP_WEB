// Run with Node and Playwright available in NODE_PATH.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8').replace(/^\uFEFF/, '');
const template = read('templates/document_ai_extract.html');
const start = template.indexOf('<section id="docAiExtractLinesSection"');
const section = template.slice(start, template.indexOf('</section>', start) + 10);
const script = read('static/js/document_ai_extract.js');
const render = script.slice(script.indexOf('  function renderLines('), script.indexOf('  function applyReadOnlyState('));
const origins = script.slice(script.indexOf('  function lineOriginLinks('), script.indexOf('  function formatDate('));
const output = process.env.LAYOUT_OUTPUT_DIR;
if (output) fs.mkdirSync(output, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || undefined });
  try {
    const page = await browser.newPage({ locale: 'pt-PT' });
    const html = `<!doctype html><html lang="pt" data-sz-theme="dark"><head>
      <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
      <style>*, ::before, ::after { box-sizing: border-box; }</style>
      <style>${read('static/css/sz_styles.css')}\n${read('static/css/document_ai.css')}
      body { margin: 0; padding: 16px; background: var(--sz-color-bg-main); font-family: var(--sz-font-family); }
      </style></head><body><div class="docai-extract-result-panel">${section}</div></body></html>`;
    await page.setContent(html);
    // Use production row rendering with a minimal, offline document state.
    await page.addScriptTag({ content: `
      const state = { selectedOrigins: [], selectedDeliveryNoteGroups: new Set(), selectedSplitLines: new Set(),
        validationVisible: false, validationMissing: new Set(), deliveryNoteDistributionMode: false };
      const els = { linesBody: document.getElementById('docAiExtractLinesBody'),
        lineCount: document.getElementById('docAiExtractLineCount'), splitLineBtn: document.getElementById('docAiExtractSplitLineBtn') };
      const ensureLineIdentities = lines => lines;
      const selectedPrimaryOriginFamilies = () => new Set(['bc']);
      const selectedPrimaryOriginFamily = () => 'bc';
      const groupMembers = line => [line];
      const countLabel = (n, single, plural) => n + ' ' + (n === 1 ? single : plural);
      const escapeHtml = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('"', '&quot;');
      const formatEditableAmount = value => Number(value).toLocaleString('pt-PT', { minimumFractionDigits: 2 });
      const refreshValidationHighlights = () => {};
      const canonicalValidationTooltips = { vehicleAssociated: 'Viatura', vehicleToAssociate: 'Associar viatura' };
      ${origins}
      ${render}
      const lines = ['NEODUR HE 3, 25 kg', 'Europaletten', 'Treibstoffzuschlag'].map((description, i) => ({
        line_id: String(i), description, qty: i === 1 ? 18 : 21600, unit_price: i === 0 ? 0.25 : 0,
        net_amount: i === 0 ? 5292 : 0, tax_rate: 0, ccusto: 'DE1702', date: i === 0 ? '' : '2026-08-31',
        origin_delivery_note_number: '1234', registration: i === 1 ? 'AA-00-AA' : '',
        detailed_costs: i === 2 ? [{ cost_type: 'included' }] : []
      }));
      window.renderFixture = distribution => { state.deliveryNoteDistributionMode = distribution; renderLines(lines, 'EUR'); };
      renderFixture(false);
    ` });
    for (const width of [1440, 1250, 1024, 768, 390]) {
      await page.setViewportSize({ width, height: 640 });
      for (const distribution of [false, true]) {
        await page.evaluate((mode) => window.renderFixture(mode), distribution);
        const issues = await page.evaluate(() => {
          const errors = [];
          for (const row of document.querySelectorAll('#docAiExtractLinesBody tr')) {
            for (const control of row.querySelectorAll('input, button')) {
              const box = control.getBoundingClientRect();
              const cell = control.closest('td').getBoundingClientRect();
              if (box.left < cell.left - 1 || box.right > cell.right + 1) {
                errors.push({ control: control.className, left: box.left, right: box.right, cellLeft: cell.left, cellRight: cell.right });
              }
            }
          }
          if (document.documentElement.scrollWidth > window.innerWidth + 1) errors.push('Page overflows viewport');
          return errors;
        });
        assert.deepEqual(issues, [], `Controls overflow at ${width}px, distribution=${distribution}`);
        const scroller = page.locator('#docAiExtractLinesSection .sz_table_wrap');
        await scroller.evaluate(el => { el.scrollLeft = el.scrollWidth; });
        await page.locator('[data-line-date="1"]').fill('2026-09-22');
        assert.equal(await page.locator('[data-line-date="1"]').inputValue(), '2026-09-22');
        if (distribution) {
          await page.locator('[data-line-select="0"]').check();
          assert.equal(await page.locator('[data-line-select="0"]').isChecked(), true);
        } else {
          await page.locator('[data-line-bc="0"]').first().click();
        }
        if (output && !distribution) {
          await page.screenshot({ path: path.join(output, `details-${width}.png`), fullPage: true });
        }
        await scroller.evaluate(el => { el.scrollLeft = 0; });
      }
      console.log(`PASS ${width}px: normal and distribution layouts, date editing, origin/selection controls`);
    }
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
