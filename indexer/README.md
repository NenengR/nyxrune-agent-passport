# NyxRune Agent Passport

**Status: LIVE.** Kontrak Passport sudah deploy di BSC di **`0xd3a3e3a726881d2eed7e6e49331af16a7de52392`**, source terverifikasi (Sourcify exact match), dan indexer sudah jalan live dengan data nyata. File contoh di repo ini tetap memakai data fixture untuk pengujian, lihat baris data contoh di bawah.

Paspor aktivitas untuk pemegang Agent ID: check-in harian UTC, badge ERC721 soulbound satu per wallet, dan vote per polling. Rancangan akses memakai `balanceOf(wallet) > 0` pada Agent ID `0x60b9262456de011f7d15a54cdd8c48baaa8b022f`. Alamat tersebut adalah kontrak **Agent ID**, bukan alamat Passport. Rancangan fungsi gratis plus gas; tidak ada fee protokol, return, janji hadiah, token fungibel baru, atau mekanisme pendanaan dalam kerangka ini. Badge adalah NFT soulbound sesuai spesifikasi kontrak yang masih menunggu implementasi.

Repo ini berisi indexer baca saja, halaman statistik publik yang bisa di-host sebagai file statis, dan naskah demo. Tidak ada wallet connect/transaksi dalam halaman statistik. Frontend transaksi dan `AgentPassport.sol` adalah pekerjaan Garing; source kontrak belum disalin atau dinyatakan terverifikasi di sini. `spec.md` adalah masukan spesifikasi lokal yang sudah ada; klaim verifikasi di dalamnya bukan hasil pengujian kerangka ini.

## Jalankan lokal

Kebutuhan: Python **3.10+**, tanpa dependency eksternal. Node.js hanya diperlukan untuk uji JavaScript opsional. Tidak perlu `pip install`, `npm install`, private key, seed phrase, API secret, atau wallet.

```bash
cd /workspace/sawunk/binance
python3 -m passport.indexer --fixture
python3 -m http.server 8000 --bind 127.0.0.1 --directory public
```

Buka `http://127.0.0.1:8000`. Jalankan perintah dari terminal yang mengizinkan socket lokal. Hanya direktori `public/` yang disajikan, bukan root repo atau config. Server pengembangan ini untuk lokal; deployment publik nantinya cukup menyajikan `public/` melalui static host dengan HTTPS, setelah persetujuan HAMID. Tidak ada publikasi dilakukan sekarang.

Data contoh memakai tanggal sintetis 18–19 November 2026 UTC, dua alamat aktor uji, enam event unik plus satu duplikat disengaja. Hasil yang diharapkan: **2 alamat aktif unik, 2 check-in, 1 badge, 2 vote, 1 polling**. Semua angka berlabel **DATA CONTOH LOKAL — BELUM LIVE**. Tidak ada tx hash atau tautan bukti explorer contoh. Snapshot dihasilkan ulang secara lokal, bukan di-track sebagai data produksi.

Jalankan ulang indexer untuk memperbarui snapshot. Halaman mengambil JSON setiap 60 detik, tetapi tidak menjalankan indexer. Jika memakai fixture setelah RPC, file output default akan terganti dengan data contoh berlabel fixture; gunakan `--output /tmp/nyxrune-fixture-stats.json` jika tidak ingin menimpa snapshot lain. Jangan jalankan dua penulis pada file output sama secara bersamaan.

## Pengujian

```bash
cd /workspace/sawunk/binance
python3 -m unittest discover -s tests -v
python3 -m passport.indexer --fixture
node --check public/app.js
node tests/test_ui.cjs
```

Pengujian mencakup agregasi UTC, deduplikasi, alamat case-insensitive, validasi config, empat jenis event, address word pada topics/data, filter alamat dan blok, konfirmasi blok, chain ID, bytecode kosong, reorg, penulisan atomik, serialisasi JSON-RPC dengan transport mock, serta tampilan DOM offline dan kondisi error halaman. Nilai alamat dan hash sintetis di unit test hanya data internal pengujian, bukan config deploy, alamat Passport, tx hash, atau bukti chain.

Lingkungan pengerjaan 18 November 2026 UTC melarang pembuatan socket: uji HTTP loopback dilewati dengan `Local socket unavailable: [Errno 1] Operation not permitted`. Hasil saat itu: **16 test Python, 15 lolos, 1 skip**, ditambah uji Node lolos. Uji mock bukan bukti koneksi HTTP nyata. Tidak ada browser terpasang untuk inspeksi visual; tampilan responsif belum diverifikasi melalui browser. Tidak ada testnet/mainnet yang dihubungi. Tidak ada dependency yang perlu diunduh; jalur instalasi/DNS tidak dicoba karena tidak diperlukan.

## Isi alamat kontrak setelah HAMID memberikan hasil deploy terverifikasi

1. Tunggu HAMID memberikan alamat Passport asli, network/chain ID, deployment block, source terverifikasi, ABI final, dan izin melanjutkan integrasi. Jangan mengambil alamat Agent ID sebagai alamat Passport.
2. Salin config lokal:

   ```bash
   cp config/indexer.example.json config/indexer.local.json
   ```

3. Edit `config/indexer.local.json`: ganti `contract_address` dari `0xd3a3e3a726881d2eed7e6e49331af16a7de52392` hanya dengan alamat asli dari HAMID; isi `deployment_block` dari bukti nyata. Default `chain_id: 56` berasal dari spesifikasi lokal; konfirmasi kembali dengan HAMID. Ubah chain ID jika pengujian yang diizinkan memakai jaringan lain.
4. Untuk **setiap** event `CheckIn`, `BadgeMinted`, `Voted`, `PollCreated`, isi `topic0` dengan hash Keccak-256 dari signature event canonical pada ABI final, atau minta Garing memasok nilai dari build final. **Jangan gunakan SHA3-256**, jangan menebak tipe parameter, urutan parameter, atau penanda `indexed`. `EVENT_TOPIC_TBD` sengaja belum bisa dipakai. Event harus non-anonymous.
5. Untuk `CheckIn`, `BadgeMinted`, `Voted`, isi `wallet` dengan objek `source` dan `index` sesuai posisi address `user` pada ABI final: `source` bernilai `topics` untuk field indexed (indeks 1 adalah indexed pertama; indeks 0 adalah signature), atau `data` untuk field non-indexed (word pertama indeks 0). Objeknya berbentuk `{"source":"topics","index":1}` **hanya bila ABI final memang menempatkan user sebagai indexed pertama**. Word ABI adalah 32 byte; posisi `Voted` khususnya tidak boleh diasumsikan sama dengan event lain. Dynamic fields menggunakan offset ABI; hanya address statis top-level yang didukung decoder ini.
6. `PollCreated` hanya dihitung, tidak didecode pertanyaan/opsinya dan tidak masuk hitungan alamat aktif. Setelah layout dan hash keempat event diperiksa terhadap ABI/source final, set `event_schema_verified: true`. Flag ini pernyataan operator; tool tidak melakukan audit atau pembuktian `balanceOf` historis.
7. `confirmations` default 20 adalah buffer operasional, **bukan jaminan finalitas**. Sesuaikan dengan operator. Atur `block_chunk_size` sesuai batas RPC. Gunakan RPC baca publik tanpa API secret; jangan masukkan credential ke repo. `RPC_URL` diambil dari environment shell, tidak ditulis ke statistik.

Contoh perintah (set `RPC_URL` ke endpoint baca publik pilihan operator di shell terlebih dahulu; tidak ada endpoint atau secret dibuat oleh proyek):

```bash
python3 -m passport.indexer --rpc --config config/indexer.local.json
```

Config contoh sengaja menolak mode RPC sebelum request jaringan dengan error:

```text
ERROR: contract_address is CONTRACT_ADDRESS_TBD or invalid; wait for HAMID's verified address
```

Jangan mengaktifkan flag schema atau mengisi alamat semata-mata untuk melewati guard. Integrasi nyata menunggu ABI dan alamat dari HAMID. Indexer tidak memverifikasi source BscScan secara otomatis.

## Arti statistik dan batas teknis

- `unique_active_agent_addresses`: union alamat `user` dalam `CheckIn`, `BadgeMinted`, `Voted` selama rentang scan; keunikan harian dihitung terpisah, bukan dijumlahkan. **Bukan total seluruh pemegang Agent ID**, bukan identitas manusia unik, bukan daftar kepemilikan saat ini. Validitas gate Agent ID bergantung pada kontrak Garing; agregasi event tidak membuktikan `balanceOf`.
- `check_ins`, `badges`, `votes`, `polls`: jumlah event unik masing-masing, bukan hitungan klik UI atau supply yang direkonstruksi. Hari memakai timestamp blok UTC; hari tanpa event tidak ditampilkan, bukan data yang hilang dari tabel. Mint hari ini tidak berarti user masih holder Agent ID hari ini.
- Snapshot publik hanya memuat agregat, alamat Passport, metadata rentang blok, hash blok konfirmasi dari RPC nyata saat tersedia, dan waktu pembuatan; tidak memuat daftar wallet/identitas/nama.
- Setiap run membaca ulang **seluruh rentang dari deployment block ke head dikurangi confirmations**, per chunk. Tidak ada cursor tersimpan, sehingga rerun tidak menumpuk hitungan dan mengoreksi reorg pada run berikutnya. Biaya baca tumbuh seiring umur kontrak; cocok untuk kerangka MVP kecil. Belum ada scheduler, DB inkremental, failover, auto-retry/rate-limit backoff atau adaptive chunking. Jika provider membatasi log, kecilkan chunk dan rerun; pastikan provider tidak memangkas hasil diam-diam.
- Identitas event RPC adalah `(blockNumber, transactionIndex, logIndex)`; duplikat identik dihitung sekali, duplikat konflik ditolak. Hash log dibandingkan dengan bloknya, dan anchor head dikonfirmasi lagi sebelum publish; reorg terdeteksi menghentikan run. Provider dipercaya, tidak ada pembuktian independen multi-RPC.
- JSON ditulis atomik hanya setelah scan lengkap. Kegagalan menyisakan snapshot lama; waktu snapshot tetap terlihat. Halaman tidak dapat mengetahui run gagal jika snapshot lama masih terbaca: operator harus memonitor exit code dan umur `generated_at`. Kegagalan fetch/JSON UI menampilkan error dan menyembunyikan angka.

## Aturan akses, keamanan dan izin owner

Rancangan kontrak: semua fitur pengguna digate `balanceOf > 0`; `checkIn()` sekali per hari UTC, `mintBadge()` sekali per wallet, `vote(pollId, optionIndex)` mengikuti aturan final yang harus dikonfirmasi. **Isu terbuka:** brief menyebut satu Agent ID satu vote, sementara `spec.md` menyebut satu wallet per polling. Gate balance dan kunci wallet tidak menjamin token yang berpindah wallet tidak vote dua kali. HAMID/Garing harus memutuskan aturan dan test sebelum klaim demo atau live.

Owner hanya boleh `createPoll`. Tidak boleh ada withdraw, fee, transfer aset user, unlimited approval, atau hak owner lain yang disisipkan. Source final dan bukti test hak owner menunggu Garing; MIT pada repo ini bukan klaim source kontrak sudah tersedia atau diaudit.

Halaman statistik tidak menyediakan koneksi wallet, input nama/wallet, QR login, pairing code, penyimpanan sesi, maupun tanda tangan/transaksi. Indexer membatasi RPC pada lima metode baca saja. Tiap transaksi dari frontend Garing nantinya harus dikonfirmasi sendiri oleh pengguna di walletnya. Jangan meminta seed phrase, private key, API secret, atau pairing code. Tidak ada manipulasi volume atau registrasi massal. Demo nantinya hanya menunjukkan tindakan nyata yang diperlukan dan diizinkan. Proyek memakai identitas NyxRune Agent Passport dan tidak memakai logo/merek penyelenggara sebagai identitas proyek.

## Struktur file untuk repo publik (belum dipublikasikan)

```text
LICENSE                       Lisensi MIT
README.md                     Status, penggunaan, batasan, aturan akses
.gitignore                    Abaikan config lokal, credential, cache, output runtime
spec.md                       Spesifikasi masukan yang sudah ada; belum diverifikasi ulang
config/indexer.example.json   Placeholder alamat + schema event final yang masih kosong
fixtures/events.json          Event sintetis lokal, satu duplikat disengaja
passport/__init__.py          Paket Python
passport/indexer.py           CLI, RPC baca, decode alamat, agregasi, JSON atomik
public/index.html             Halaman statistik
public/styles.css             Gaya responsif
public/app.js                 Pembacaan JSON dan rendering aman textContent
public/data/stats.json        Hasil runtime dari --fixture/--rpc; tidak di-track
public/data/.gitkeep           Pertahankan direktori output pada checkout baru
tests/test_indexer.py         Uji Python offline + HTTP loopback bila diizinkan
tests/test_ui.cjs             Uji DOM JS offline, tanpa dependency
docs/demo-storyboard.md       Naskah 110 detik dan daftar shot (lihat docs/)
```

File source lokal siap untuk dipilih HAMID saat membuat repo publik. Tidak ada repo GitHub dibuat, tidak ada remote, push, deploy, atau submit. Akun dan nama repo harus diputuskan HAMID. Review `spec.md` (termasuk alamat wallet dan klaim historis) sebelum publikasi; indeks/statistik tidak memerlukan daftar nama atau wallet tersebut. Saat source kontrak final diterima, sertakan source, lisensi yang sesuai, ABI, hasil pengujian, dan referensi explorer asli setelah review HAMID.

## Demo dan jadwal koordinasi

Lihat `docs/demo-storyboard.md`. Target dari brief: MVP 25 November 2026 dan submit awal 5 Desember 2026, menunggu validasi HAMID. Ini target koordinasi, bukan klaim siap live atau konfirmasi syarat/tenggat resmi hackathon. Naskah saja sudah dibuat; belum ada video final.

Lisensi: MIT, lihat `LICENSE`.
