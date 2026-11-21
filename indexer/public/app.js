'use strict';
const $ = id => document.getElementById(id);
const numeric = value => Number.isSafeInteger(value) && value >= 0;
const keys = ['unique_active_agent_addresses', 'check_ins', 'badges', 'votes', 'polls'];
const number = new Intl.NumberFormat('id-ID');
function validate(data) {
  if (data.schema_version !== 1 || !['local-fixture', 'rpc'].includes(data.source)
      || data.is_fixture !== (data.source === 'local-fixture')
      || !data.totals || !keys.every(key => numeric(data.totals[key]))
      || !Array.isArray(data.daily) || !data.daily.every(row => /^\d{4}-\d{2}-\d{2}$/.test(row.day)
        && keys.every(key => numeric(row[key])))
      || !Number.isFinite(Date.parse(data.generated_at))
      || typeof data.contract_address !== 'string' || typeof data.metric_note !== 'string'
      || (data.source === 'rpc' && (!data.scan || !numeric(data.scan.from_block)
        || !numeric(data.scan.to_block) || !numeric(data.scan.confirmations)
        || !numeric(data.scan.chain_id)))) throw new Error('Format snapshot tidak valid.');
}
async function refresh() {
  try {
    const response = await fetch('data/stats.json', {cache: 'no-store'});
    if (!response.ok) throw new Error(`HTTP ${response.status}: snapshot tidak tersedia.`);
    const data = await response.json();
    validate(data);
    $('status').textContent = data.is_fixture
      ? 'DATA CONTOH LOKAL — KERANGKA, BELUM LIVE. Angka di bawah bukan aktivitas nyata.'
      : 'SNAPSHOT RPC BACA SAJA — lihat waktu snapshot dan rentang blok di bawah.';
    for (const [id, key] of Object.entries({unique: keys[0], checkins: 'check_ins', badges: 'badges', votes: 'votes', polls: 'polls'})) {
      $(id).textContent = number.format(data.totals[key]);
    }
    const rows = data.daily.map(row => {
      const tr = document.createElement('tr');
      for (const value of [row.day, ...keys.map(key => number.format(row[key]))]) {
        const td = document.createElement('td');
        td.textContent = value;
        tr.append(td);
      }
      return tr;
    });
    $('daily').replaceChildren(...rows);
    $('empty').hidden = rows.length !== 0;
    $('note').textContent = `*${data.metric_note}`;
    $('contract').textContent = data.contract_address;
    $('updated').textContent = new Date(data.generated_at).toISOString();
    $('updated').dateTime = data.generated_at;
    $('provenance').textContent = data.is_fixture
      ? 'Sumber: fixture sintetis lokal. Tidak ada RPC, testnet, atau mainnet yang dibaca untuk angka ini.'
      : `Sumber: RPC chain ${data.scan.chain_id}, blok ${data.scan.from_block}–${data.scan.to_block}; kedalaman konfirmasi ${data.scan.confirmations} blok. Bukan data real-time.`;
    $('error').hidden = true;
  } catch (error) {
    $('status').textContent = 'DATA TIDAK TERSEDIA / GAGAL DIPERBARUI. Periksa snapshot indexer.';
    $('error').textContent = `${error.message} Angka lama disembunyikan. Jalankan indexer, lalu muat ulang.`;
    $('error').hidden = false;
    for (const id of ['unique', 'checkins', 'badges', 'votes', 'polls']) $(id).textContent = '—';
    $('daily').replaceChildren();
    $('empty').hidden = true;
    $('provenance').textContent = 'Tidak ada snapshot yang dapat ditampilkan.';
    $('updated').textContent = '—';
    $('updated').removeAttribute('datetime');
    $('contract').textContent = '0xd3a3e3a726881d2eed7e6e49331af16a7de52392';
  }
}
refresh();
setInterval(refresh, 60000);
