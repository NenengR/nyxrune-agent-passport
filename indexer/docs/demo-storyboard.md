# Demo NyxRune Agent Passport — naskah dan storyboard

**Status: DRAF NASKAH. Belum direkam. Belum live.** Durasi rencana **110 detik (1 menit 50 detik)**, termasuk jeda transisi. Jangan merekam atau merakit video final sebelum frontend Garing, kontrak final, serta persetujuan HAMID tersedia. Alamat Passport tetap `0xd3a3e3a726881d2eed7e6e49331af16a7de52392`. Tidak ada tx hash, link transaksi, tampilan BscScan, atau bukti deploy buatan di dokumen ini.

Narasi di bawah disiapkan untuk rekaman setelah setiap tindakan benar-benar dapat dibuktikan. Jika bahan belum ada, pertahankan dokumen sebagai storyboard; jangan menyajikan animasi/mockup sebagai transaksi sungguhan. Angka fixture tidak boleh dipakai sebagai angka adopsi nyata.

| Waktu | Shot yang direncanakan | Teks layar | Narasi |
|---|---|---|---|
| 00–12 (12 dtk) | Judul NyxRune dan ilustrasi teks masalah, tanpa logo penyelenggara | NyxRune Agent Passport · Paspor aktivitas agen | “Aktivitas agen sering terpisah-pisah. NyxRune Agent Passport merangkum check-in, badge, dan suara dalam satu paspor aktivitas on-chain.” |
| 12–25 (13 dtk) | Frontend Garing: tombol connect; wallet extension dibuka pengguna. Tunggu status holder nyata | Connect wallet · Khusus pemegang Agent ID | “Hubungkan wallet milik sendiri lewat ekstensi. Akses memerlukan Agent ID, dengan pemeriksaan balanceOf. Tidak perlu QR login, seed phrase, atau pairing code.” |
| 25–43 (18 dtk) | Klik check-in; tampilkan detail transaksi di wallet, konfirmasi manual, tunggu receipt nyata | Check-in · Maksimal sekali per hari UTC · Gratis plus gas | “Check-in tersedia sekali per hari UTC. Periksa detail transaksi dan gas, lalu konfirmasi sendiri di wallet. Status berhasil muncul setelah transaksi dikonfirmasi.” |
| 43–59 (16 dtk) | Klik mint badge; konfirmasi pengguna; detail NFT dari frontend setelah receipt | Badge soulbound · Satu per wallet | “Mint badge tanpa biaya protokol, tetap membayar gas jaringan. Badge ini satu per wallet dan soulbound, sehingga tidak bisa dipindahtangankan.” |
| 59–77 (18 dtk) | Polling mingguan yang dibuat owner: opsi → pilih → detail wallet → konfirmasi manual → hasil | Pilih opsi · Konfirmasi vote di wallet | “Pilih opsi polling yang tersedia dan konfirmasi vote sendiri. Aturan satu suara harus mengikuti kontrak final yang sudah diperiksa. Owner hanya dapat membuat polling.” |
| 77–90 (13 dtk) | Halaman statistik dengan snapshot RPC nyata, rentang blok dan waktu terlihat | Agregat event · UTC · Snapshot baca saja | “Statistik menghitung event check-in, badge, dan vote per hari UTC, serta alamat aktif unik. Ini jumlah alamat yang beraktivitas, bukan seluruh pemegang Agent ID.” |
| 90–105 (15 dtk) | BscScan yang benar: source terverifikasi dari alamat HAMID, receipt transaksi milik demo, event Logs | Source terverifikasi dan receipt asli · Menunggu bukti HAMID | “Periksa source kontrak dan izin owner pada explorer, lalu cocokkan receipt dan event aktivitas. Bukti yang ditampilkan harus berasal dari alamat dan transaksi demo yang sebenarnya.” |
| 105–110 (5 dtk) | Judul penutup dan disclaimer | Gratis plus gas · Tidak ada return atau janji hadiah | “NyxRune Agent Passport. Gratis plus gas, tanpa return atau janji hadiah.” |

## Daftar bahan yang masih menunggu

1. **Frontend Garing** yang dapat connect lewat wallet extension, menampilkan network, hasil gate Agent ID, detail transaksi, loading/error, dan receipt. Halaman statistik fase ini tidak menjalankan transaksi.
2. **Alamat Passport dari HAMID** beserta deployment block, ABI final, source dan verifikasi explorer asli. Semua config masih `0xd3a3e3a726881d2eed7e6e49331af16a7de52392`.
3. **Keputusan aturan vote:** “satu Agent ID” pada brief versus “satu wallet per polling” pada spesifikasi. Jangan menyebut jaminan satu token satu suara di rekaman sebelum aturan dan testnya jelas.
4. Bukti nyata dari tindakan yang diizinkan: receipt check-in, mint badge, vote, dan `PollCreated`; statistik RPC yang sudah direkonsiliasi terhadap event. Tidak ada bukti tersebut dibuat sekarang.
5. Polling yang disiapkan owner dan wallet holder milik pengguna sendiri. Pengguna mengonfirmasi setiap transaksi; agen ini tidak memegang key, mengirim transaksi, menyediakan dana, melakukan approval, atau memindahkan aset.
6. Validasi HAMID atas akun/domain/nama repo, naskah final, source/izin owner, serta bukti demo. Tidak ada publikasi, deploy, submit, atau rekaman final dalam fase ini.

## Catatan pengambilan gambar nantinya

- Batasi voice-over sekitar 185 kata; rencana 110 detik menyisakan jeda untuk wallet dan loading. Jika konfirmasi terlalu lama, potong waktu tunggu dengan label “waktu tunggu dipersingkat”; jangan potong langkah persetujuan sehingga tampak otomatis.
- Jangan tampilkan notifikasi pribadi, credential, QR, pairing code, seed phrase atau private key. Tidak ada halaman pencarian wallet berdasarkan nama.
- Satu tindakan nyata per fungsi cukup untuk demo, setelah diizinkan pengguna. Jangan mengulang transaksi untuk membuat volume terlihat besar atau membuat banyak akun.
- Bila bahan belum siap, catat shot tertunda. Jangan membuat tautan explorer palsu, mengisi placeholder dengan tebakan, atau mengklaim fixture sebagai hasil on-chain.
