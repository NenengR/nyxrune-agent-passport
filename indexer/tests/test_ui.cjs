// Offline DOM behavior checks; not a substitute for a rendered browser test.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const base = path.join(__dirname, '..');
const stats = JSON.parse(fs.readFileSync(path.join(base, 'public/data/stats.json'), 'utf8'));
const code = fs.readFileSync(path.join(base, 'public/app.js'), 'utf8');
class Element {
  constructor() { this.textContent = ''; this.hidden = false; this.children = []; }
  append(child) { this.children.push(child); }
  replaceChildren(...children) { this.children = children; }
  removeAttribute(name) { delete this[name]; }
}
(async () => {
  const nodes = new Map();
  let fail = false;
  const context = vm.createContext({
    document: {getElementById: id => {if (!nodes.has(id)) nodes.set(id, new Element()); return nodes.get(id);},
               createElement: () => new Element()},
    fetch: async () => ({ok: !fail, status: 503, json: async () => stats}),
    Intl, Date, Number, Error, setInterval: () => 1
  });
  vm.runInContext(code, context);
  await new Promise(resolve => setImmediate(resolve));
  assert.match(nodes.get('status').textContent, /DATA CONTOH LOKAL/);
  assert.equal(nodes.get('unique').textContent, '2');
  assert.equal(nodes.get('checkins').textContent, '2');
  assert.equal(nodes.get('badges').textContent, '1');
  assert.equal(nodes.get('votes').textContent, '2');
  assert.equal(nodes.get('daily').children.length, 2);
  assert.equal(nodes.get('contract').textContent, '0xd3a3e3a726881d2eed7e6e49331af16a7de52392');
  assert.equal(nodes.get('error').hidden, true);
  fail = true;
  await vm.runInContext('refresh()', context);
  assert.match(nodes.get('error').textContent, /HTTP 503/);
  assert.equal(nodes.get('daily').children.length, 0);
  assert.equal(nodes.get('unique').textContent, '—');
  assert.equal(nodes.get('updated').textContent, '—');
  fail = false;
  await vm.runInContext('refresh()', context);
  assert.equal(nodes.get('error').hidden, true);
  assert.equal(nodes.get('daily').children.length, 2);
  stats.schema_version = 99;
  await vm.runInContext('refresh()', context);
  assert.match(nodes.get('error').textContent, /Format snapshot tidak valid/);
  console.log('PASS: UI fixture rendering, totals, daily rows, source label, HTTP failure, recovery, invalid schema (offline DOM; no visual browser test).');
})().catch(error => { console.error(error); process.exitCode = 1; });
