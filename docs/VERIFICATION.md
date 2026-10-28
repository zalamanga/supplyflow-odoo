# Hasil verifikasi SupplyFlow Office

Tanggal: 28 Oktober 2026. Dokumen ini mencatat pemeriksaan yang sudah menghasilkan bukti dan pekerjaan yang masih menunggu hasil. Full run gabungan sepuluh tes browser lulus, dan delapan screenshot sudah diambil serta diperiksa. Publikasi GitHub dan CI remote masih menunggu hasil akhir pada catatan ini.

Status `PASS` berlaku pada skenario yang disebutkan. Status `PARSIAL` berarti sebagian kebutuhan sudah diperiksa. `PENDING` berarti hasil akhir belum tersedia; keberadaan kode tes tidak dihitung sebagai tes lulus.

## Ringkasan status

| Pemeriksaan | Status | Bukti aktual |
| --- | --- | --- |
| Instalasi baru tanpa data latihan | PASS | Inisialisasi selesai dengan 67 modul; jumlah permintaan, kasus, purchase order, dan sales order masing-masing nol sebelum pemuatan latihan |
| Role database aplikasi | PASS | Role `supplyflow` bukan superuser, tidak memiliki createdb/createrole; hasil ringkas pemeriksaan `supplyflow\|f\|f\|f` |
| Data latihan opt-in | PASS | Seed selesai melalui alur native pembelian, receipt, transfer internal, dan penjualan |
| Tes ORM addon | PASS | 42 post-tests, 0 gagal, 0 error |
| Validator arsip backup | PASS | 25 unittest lulus tanpa menjalankan restore database |
| Workspace browser | PASS | Empat metrik/filter, All requests, nomor permintaan terbaru, fokus Tab/Enter/Escape, loading/empty/error/retry, dan viewport 390 px telah lulus |
| PDF QWeb | PASS | Endpoint PDF menghasilkan PDF nyata; pypdf membaca satu halaman dan 765 karakter, termasuk judul permintaan serta pemasok latihan |
| Konkurensi HTTP | PASS | Sesi HTTP terpisah menghasilkan satu RFQ; dua kasus yang bersaing atas jumlah retur hanya menghasilkan satu keberhasilan |
| Suite gabungan browser | PASS | Sepuluh tes lulus dalam 5,3 menit: sembilan workflow dan satu tes capture yang menghasilkan delapan gambar |
| Backup dingin dan restore terisolasi | PASS | Arsip dipulihkan ke stack/volume baru; fingerprint 16 tabel dan berkas penanda cocok |
| Restart instance asli | PASS pada data yang diperiksa | Aplikasi kembali sehat dan lampiran penanda tetap cocok |
| Screenshot README | PASS | Delapan PNG nyata diambil, diperiksa secara visual, dan sudah dirujuk README |
| Publikasi GitHub/CI remote | PENDING | Belum ada hasil publikasi atau run CI remote yang dicatat sebagai selesai |

## Instalasi dan batas konfigurasi

Runtime menggunakan Odoo Community 19, image `19.0-20261015` dengan digest pada [Compose](../compose.yaml), PostgreSQL 17, dan addon dari bind mount read-only. Aplikasi lokal memakai port 8070. Pemeriksaan ini tidak menyatakan konfigurasi siap untuk deployment publik.

Instalasi pertama dilakukan sebelum data latihan dipilih. Pemeriksaan SQL menghasilkan nol record untuk empat kelompok dokumen bisnis: `supplyflow.request`, `supplyflow.issue`, `purchase.order`, dan `sale.order`. Karena itu, transaksi latihan tidak berasal dari startup kosong secara diam-diam.

Sesudahnya, pemuatan data latihan berhasil membuat alur distribusi sintetis melalui metode bisnis Odoo. Keberhasilan seed tidak dipakai sebagai pengganti tes isolasi perusahaan, seluruh skenario penolakan, atau uji browser.

## Tes ORM dan validator arsip

Log lokal `.local/orm-final-stderr.log` mencatat hasil akhir pada `2026-10-28 07:03:53 UTC`:

```text
42 post-tests in 32.35s
0 failed, 0 error(s) of 42 tests
```

Angka 42 mengikuti ringkasan hasil tes Odoo, bukan penjumlahan statistik internal lain pada log. Log lengkap berada pada folder lokal yang diabaikan Git.

Tes tersebut berada di [purchase request](../addons/supplyflow_office/tests/test_purchase_request.py), [supplier issue](../addons/supplyflow_office/tests/test_supplier_issue.py), [distribution flow](../addons/supplyflow_office/tests/test_distribution_flow.py), dan [workspace](../addons/supplyflow_office/tests/test_workspace.py). Cakupannya meliputi transisi, larangan persetujuan mandiri, field audit/context terlindungi, pembekuan parent/baris, izin native, perusahaan, validasi angka, RFQ idempoten, retur tertaut, jumlah retur tersisa, receipt sebagian/backorder, perpindahan gudang, serta penjualan/pengiriman native.

Perintah validator arsip yang sudah menghasilkan 25 tes lulus:

```powershell
python -m unittest discover -s tests -p test_backup_archive.py
```

[Tes arsip](../tests/test_backup_archive.py) memeriksa path traversal, path absolut, symlink, nama duplikat, benturan berkas/direktori, ukuran/hash, format/versi, nama database, dan header dump. Pemeriksaan ini terpisah dari latihan restore PostgreSQL yang dijelaskan di bawah.

## Browser, PDF, dan transaksi bersamaan

Full run gabungan menghasilkan sepuluh tes lulus dalam 5,3 menit. Sembilan tes memeriksa workflow; satu tes capture menghasilkan delapan screenshot. Hasil ini berasal dari satu putaran penuh setelah cakupan workspace dan varian pembatalan kasus diperluas.

[Helper clickWorkflow](../tests/browser/helpers.js) menunggu POST `call_button` berdasarkan model/metode, memeriksa respons bisnis, lalu menunggu field penanda pada form dokumen native bila aksi membuka RFQ atau picking. Assertion field relasi membaca nilai input yang sesuai. Sinkronisasi ini mencegah pemeriksaan status dilakukan sebelum transaksi tombol selesai.

Seluruh skenario selesai: workspace metrik/filter/navigasi/keyboard, controlled loading/empty/error/retry dan layar 390 px, PDF, pembuatan form/penarikan permintaan, RFQ independen, retur pemasok, penolakan/revisi/pembatalan persetujuan, shortage serta pembatalan kasus, dan konkurensi HTTP.

Pada putaran penuh ini, RFQ independen lulus dalam 30,3 detik; retur pemasok 36,3 detik; penolakan/revisi 48,1 detik; shortage beserta pembatalan oleh pelapor dan Approver 28,7 detik; konkurensi HTTP 20,8 detik. Waktu ini merupakan hasil satu eksekusi lokal, bukan tolok ukur performa aplikasi.

Kesembilan skenario workflow meliputi workspace/filter/keyboard, pemulihan error/layar sempit, PDF, pembuatan form dan penarikan permintaan, persetujuan/RFQ independen, retur pemasok, penolakan/revisi/pembatalan persetujuan, penyelesaian shortage/pembatalan kasus, serta konkurensi HTTP.

Endpoint laporan menghasilkan PDF nyata. Berkas lokal `.local/request-summary.pdf` dibaca dengan pypdf: satu halaman, 765 karakter, judul permintaan dan nama pemasok latihan ditemukan. Menu **Actions → Purchase request summary** juga diklik; log server mencatat pembuatan PDF dan POST `/report/download` HTTP 200 pada `08:06:40 UTC`. Browser menampilkan respons perantara service worker 204, sehingga respons tersebut tidak dipakai sebagai pemeriksaan MIME PDF. Tes endpoint memeriksa MIME dan signature PDF secara terpisah. Ini bukan audit tata letak seluruh kemungkinan dokumen.

Uji konkurensi memakai context HTTP terpisah, bukan dua pemanggilan berurutan dalam satu transaksi. Pembuatan RFQ bersamaan menyisakan satu purchase order tertaut. Dua kasus retur yang masing-masing meminta lebih dari separuh sisa jumlah sumber menghasilkan satu retur yang berhasil, sehingga jumlah yang sama tidak dialokasikan dua kali lewat alur addon pada skenario itu.

Pemeriksaan viewport 390 px dan fokus Tab/Enter/Escape yang sudah lulus berlaku pada workspace. Setelah penyempurnaan visual terakhir, dua form addon juga diperiksa pada 390 px tanpa overflow dokumen. Tabel produk memakai scroll internal. Label readonly kedua form diverifikasi melalui computed style: `rgb(73, 80, 87)` dengan opacity `1`. Pemeriksaan 59 elemen teks workspace menghasilkan rasio kontras minimum 5,28:1. Screenshot form terkait diambil ulang dan diperiksa visual. Ini tidak menyatakan seluruh layar native, dialog, breakpoint, atau kombinasi teknologi bantu telah diaudit.

Tes capture menghasilkan delapan berkas pada `docs/screenshots`: workspace, daftar permintaan, permintaan disetujui, pembelian native, kasus pemasok, receipt native, penjualan native, dan workspace mobile. Seluruh gambar telah diperiksa secara visual, termasuk keterisian data tabel serta keterbacaan deskripsi kasus. [README](../README.md) memakai kedelapan gambar tersebut. Gambar berasal dari aplikasi berjalan dengan data latihan sintetis.

### Pemetaan tindakan antarmuka

Tabel ini memetakan 18 kelompok tindakan: empat handler workspace, delapan label tombol permintaan, dan enam label tombol kasus. Varian tombol/filter yang berbagi handler tetap disebutkan supaya hasil satu klik tidak dianggap membuktikan seluruh varian. Bukti kode ada pada [workflow browser](../tests/browser/workflows.spec.js) dan [helper](../tests/browser/helpers.js); sumber tes saja tidak mengubah status pending menjadi pass.

| Kelompok tindakan | Hasil aktual atau celah |
| --- | --- |
| Workspace `load`: Refresh dan Try again | PASS: refresh lewat keyboard, loading/empty, error RPC, dan retry telah lulus |
| Workspace `openRequests`: metrik submitted dan All requests | PASS: kedua kontrol serta filter/daftar hasil telah diperiksa |
| Workspace `openIssues`: open, overdue, awaiting warehouse | PASS: ketiga metrik membuka filter yang sesuai |
| Workspace `openRequest`: nomor permintaan terbaru | PASS: kontrol pada baris workspace membuka permintaan tertaut |
| Permintaan Submit for Approval | PASS pada pembuatan form/pengajuan dan alur review |
| Permintaan Approve | PASS pada alur review independen |
| Permintaan Reject | PASS pada alur penolakan beralasan |
| Permintaan Create RFQ | PASS pada full run alur RFQ independen |
| Permintaan Open RFQ | PASS: tes capture mengklik tombol dan membuka pembelian native dengan data pemasok yang sesuai |
| Permintaan Revise Draft | PASS pada alur revisi setelah penolakan |
| Permintaan Withdraw | PASS pada pembuatan form/penarikan |
| Permintaan Cancel Approval | PASS pada alur pembatalan persetujuan |
| Kasus Submit for review | PASS pada alur retur dan penyelesaian shortage |
| Kasus Approve supplier return | PASS pada full run alur retur |
| Kasus Resolve without return | PASS pada alur shortage; status accepted tanpa picking retur diperiksa |
| Kasus Create return transfer | PASS pada full run; picking terbentuk dan belum done |
| Kasus Cancel issue | PASS pada varian pelapor gudang dan Approver, dalam skenario shortage/pembatalan 28,7 detik |
| Kasus Supplier return | PASS pada full run pembukaan picking retur tertaut |

## Backup, restore, dan restart

[Backup.ps1](../scripts/Backup.ps1) berhasil membuat arsip privat `.backups/supplyflow-20261028T072318Z-f033d5c4.zip`. Manifest memuat 458 payload: satu `database.dump` dan 457 berkas filestore. Arsip dan log/snapshot lokal tidak dipublikasikan bersama kode.

[Restore.ps1](../scripts/Restore.ps1) dengan `-ReplaceDatabase` berhasil memulihkan arsip tersebut ke proyek Compose terpisah, `supplyflow-restore-check-20261028`, dengan volume PostgreSQL dan Odoo baru. Instance kerja tidak dijadikan target percobaan restore itu.

Fingerprint sebelum backup dan setelah restore cocok pada 16 tabel. Fingerprint memakai jumlah record serta MD5 atas `row_to_json` yang diurutkan. Cakupan tabel mencakup permintaan, kasus, pembelian, penjualan, stok, partner, produk, pengguna, dan lampiran. Bukti lokal disimpan pada `.local/snapshot-before.txt` serta `.local/snapshot-restored.txt`.

Lampiran `[Verification] backup-marker.txt`, ID 543, berisi 54 byte statis. Isi fisiknya diperiksa pada volume hasil restore dan diperiksa lagi pada instance asli setelah restart. Instance asli kembali sehat. Pemeriksaan ini tidak menambahkan klaim bahwa sesi browser lama harus tetap login setelah restart.

Container, volume, dan network clone dibersihkan setelah label kepemilikan proyek diperiksa. Pembersihan dibatasi pada stack verifikasi tersebut. Keberhasilan latihan ini membuktikan pemulihan dataset yang diperiksa; prosedur produksi tetap membutuhkan kebijakan retensi, penyimpanan terpisah, dan latihan pemulihan berkala.

## Pemetaan kriteria penerimaan

ID mengacu ke [PRD](PRD.md). Status parsial mempertahankan bagian kebutuhan yang belum dibuktikan.

| ID | Status saat catatan dibuat | Bukti atau celah yang tersisa |
| --- | --- | --- |
| A01 | PASS | Instalasi database kosong selesai, addon terpasang, aplikasi dapat dibuka/login pada pemeriksaan browser |
| A02 | PASS | Empat hitungan dokumen bisnis nol sebelum memilih seed latihan |
| A03 | PASS | Pembuatan/pengajuan terbukti pada ORM dan skenario form browser yang sudah lulus |
| A04 | PASS | Tes ORM menolak baris kosong/tidak valid, jumlah tidak positif, dan harga/angka tidak valid |
| A05 | PASS | Tes ORM memeriksa larangan persetujuan mandiri serta manipulasi identitas/context |
| A06 | PASS | Tes ORM memeriksa perubahan parent, tambah/ubah/hapus baris, status, audit, dan relasi hasil |
| A07 | PASS | Penolakan beralasan, reset, riwayat chatter, dan persetujuan baru diperiksa pada ORM; alur revisi/pembatalan juga lulus pada browser |
| A08 | PASS | RFQ native, gudang incoming, estimasi, tautan, dan pengulangan aksi diperiksa pada ORM; full run UI RFQ lulus |
| A09 | PASS | Tes ORM membuktikan izin native Purchase tetap diperlukan |
| A10 | PASS | Uji context HTTP terpisah membuktikan satu RFQ pada skenario bersamaan |
| A11 | PASS | Tes ORM memeriksa receipt selesai/incoming, sumber baris, dan kecocokan perusahaan |
| A12 | PASS | Tes ORM memeriksa penyetuju independen, satu picking retur tertaut, dan pengulangan aksi; full run UI retur juga lulus |
| A13 | PASS | Aturan shortage/catatan lulus pada ORM dan browser; penyelesaian accepted tidak membuat picking retur |
| A14 | PASS | Retur manual/pending/cancel diperhitungkan; tes integrasi membandingkan stok sebelum dan setelah validasi retur |
| A15 | PASS pada alur yang diuji | Pembelian, receipt sebagian/backorder, retur, penjualan/delivery, gudang terpilih, dan transfer internal diperiksa melalui metode native |
| A16 | PARSIAL | Tes ORM isolasi permintaan/baris serta kecocokan perusahaan kasus lulus; catatan ini tidak mengklaim seluruh kombinasi akses HTTP lintas perusahaan diuji |
| A17 | PASS pada kontrol custom yang dipetakan | Full run mencakup seluruh kelompok tindakan di atas, termasuk empty/error/loading/keyboard/390 px pada workspace serta pembatalan kasus oleh pelapor dan Approver |
| A18 | PASS pada data yang diperiksa | Restart instance asli sehat dan lampiran penanda tetap cocok |
| A19 | PASS | Restore pada stack baru, fingerprint 16 tabel cocok, dan marker filestore 54 byte cocok |
| A20 | PASS | README menjelaskan batas standar/custom serta merujuk delapan screenshot nyata yang sudah diperiksa visual |

## Yang belum dinyatakan selesai

Publikasi GitHub dan GitHub Actions remote masih menunggu pembaruan catatan ini. Penyempurnaan visual terakhir sudah dimuat melalui update addon, screenshot terkait sudah diambil ulang, dan pemeriksaan visual/kontras/mobile sudah selesai. CI akan menjalankan kembali alur bisnis pada sumber terakhir.
