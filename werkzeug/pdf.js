// Rendert eine Druck-HTML-Datei als PDF. Aufruf: node pdf.js <eingabe.html> <ausgabe.pdf>
const path = require('path');
const { chromium } = require('playwright');
(async () => {
  const [src, out] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + path.resolve(src));
  await page.waitForSelector('body[data-ready="1"]', { timeout: 30000 });
  const over = await page.evaluate(() => [...document.querySelectorAll('.fit')]
    .filter(e => e.dataset.overflow === '1').map(e => e.closest('.card').dataset.nr));
  if (over.length) console.log('  WARNUNG: Text passt nicht ganz auf Karte ' + [...new Set(over)].join(', '));
  await page.pdf({ path: out, format: 'A4', printBackground: true, preferCSSPageSize: true });
  await browser.close();
})().catch(e => { console.error(e.message); process.exit(1); });
