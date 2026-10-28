# Pemeriksaan antarmuka sebelum publikasi

28 Oktober 2026. Cakupan pemeriksaan: workspace Owl dan dua form addon SupplyFlow, dengan navigasi ke dokumen Odoo terkait. Ini bukan sertifikasi aksesibilitas seluruh aplikasi Odoo atau seluruh kombinasi perangkat.

Bukti utama: [hasil verifikasi](VERIFICATION.md), [tes browser](../tests/browser/workflows.spec.js), [pengambilan screenshot](../tests/browser/screenshots.spec.js), [arah desain](DESIGN.md), serta delapan gambar pada [README](../README.md). Full run lokal menghasilkan sembilan workflow dan satu sesi capture lulus. Setelah penyempurnaan visual terakhir, addon diperbarui dan form terkait diperiksa ulang.

## Hard Gate

| Pemeriksaan | Hasil dan bukti |
| --- | --- |
| R-02, tanda em dash | PASS: pemindaian teks sumber dan dokumen proyek tidak menemukan tanda tersebut. |
| R-03, reflow | PASS: workspace dan kedua form diperiksa pada 390 px; lebar dokumen tidak melampaui viewport. Tabel produk tetap dapat digulir di dalam area tabel. |
| R-17, angka nyata | PASS: empat angka workspace berasal dari ORM; tes membandingkannya dengan respons server dan filter tujuan. |
| R-18, testimoni | PASS: tidak ada testimoni, pelanggan, atau kutipan promosi yang dibuat. |
| R-23, aset dan identitas | PASS: memakai komponen Odoo, nama produk sebagai teks, dan screenshot aplikasi. Data sintetis diberi penanda Training/Browser test. |
| R-24, tujuan navigasi | PASS: empat metrik, All requests, nomor permintaan, RFQ, dan retur membuka tujuan yang diperiksa pada browser. |
| R-25, kontras | PASS: 59 elemen teks workspace diperiksa, rasio terendah 5,28:1. Label readonly kedua form memakai warna #495057 tanpa pengurangan opacity, diverifikasi melalui computed style pada mobile. |
| R-26, kontrol aktif | PASS: 18 kelompok tindakan addon dipetakan ke hasil click-through; transisi dan relasi hasil diperiksa kembali melalui RPC. |
| R-27, keadaan UI | PASS: loading, empty state terkontrol, error RPC, dan retry diperiksa pada browser. |
| R-28, FAQ | PASS: tidak ada FAQ pengisi halaman. |
| R-32, keyboard | PASS: Tab memindahkan fokus ke metrik dengan outline nyata, Enter membuka daftar, dan Escape menutup menu pencarian serta mengembalikan fokus. |
| R-33, perubahan sumber | PASS: fitur dan perbaikan ditulis pada sumber Python, XML, JavaScript, dan SCSS; tidak mengubah tampilan melalui script injeksi browser. |
| R-34, tema | PASS: satu tema native Odoo yang didukung; tidak ada toggle tema yang belum berfungsi. |
| R-35, aplikasi berjalan | PASS: instalasi nyata, 42 tes ORM, sembilan workflow browser, capture delapan layar, serta pemeriksaan visual form setelah perubahan terakhir. |
| R-36, klaim | PASS: README membatasi cakupan lokal/pembelajaran dan tidak mengklaim sertifikasi, keamanan mutlak, atau kesiapan produksi. |
| R-37, arah desain | PASS: dokumen desain dengan ENERGY 2, RHYTHM 2, MOTION 1 disiapkan sebelum implementasi pada commit 4c4e5fe. |
| R-38, konten sintetis | PASS: nama, transaksi, dan pengguna latihan ditandai; tidak disajikan sebagai aktivitas perusahaan nyata. |

## Purpose Gate

| Pemeriksaan | Hasil dan alasan |
| --- | --- |
| R-01, gradient/glow | PASS: tidak ditambahkan; dokumen kerja memakai permukaan native. |
| R-04, ikon | PASS: ikon native mengacu ke RFQ, transfer, dan navigasi; tidak menambahkan pustaka ikon dekoratif. |
| R-06, tipografi | PASS: font Odoo dipertahankan agar form addon konsisten dengan Purchase dan Inventory. |
| R-07, pola latar | PASS: tidak menambahkan grid atau pola latar dekoratif. |
| R-08, panah | PASS: penanda alur status native menjelaskan posisi dokumen, bukan dekorasi tombol. |
| R-09, badge | PASS: badge daftar menyatakan status record yang sebenarnya. |
| R-10, glassmorphism | PASS: tidak digunakan. |
| R-12, bayangan | PASS: tidak menambahkan bayangan pada seluruh komponen. |
| R-13, glow berulang | PASS: tidak digunakan. |
| R-14, ukuran komponen | PASS: empat metrik setara untuk membandingkan antrean; tabel permintaan mendapat area utama yang lebih besar. |
| R-19, gerakan | PASS: tidak menambahkan animasi otomatis; indikator loading mengikuti permintaan data. |
| R-22, ilustrasi | PASS: tidak ada ilustrasi generik atau gambar pengganti aplikasi. |

## Liveliness

| Pemeriksaan | Hasil dan bukti |
| --- | --- |
| Dial eksplisit | PASS: ENERGY 2, RHYTHM 2, MOTION 1 pada DESIGN. |
| Konsistensi dial | PASS: aksen native pada tindakan kerja, komposisi daftar/form/workspace, tanpa animasi tambahan. |
| Titik fokus | PASS: antrean kerja pada workspace, nomor/status/tindakan pada form. |
| Whitespace struktural | PASS: jarak memisahkan metrik, daftar, identitas dokumen, produk, dan keputusan. |
| Aksen disengaja | PASS: aksen ungu Odoo menghubungkan navigasi dan aksi utama; warna status memiliki arti operasional. |
| Motif identitas | PASS: nomor permintaan, gudang, pemasok, status, dan dokumen hasil berulang pada alur distributor perlengkapan kantor. |
| Design Read | PASS: arah desain menjadi bagian commit dokumentasi sebelum kode addon. |

## Craftsmanship dan Quality Locks

| Pemeriksaan | Hasil dan bukti |
| --- | --- |
| C-1, keputusan bertujuan | PASS: tujuan komponen, warna, teks, dan label readonly dijelaskan pada DESIGN. |
| C-2, fungsi lengkap | PASS: aksi menunggu respons server; tes memeriksa status dan hubungan hasil, bukan sekadar klik selesai. |
| C-3, komposisi dari kebutuhan | PASS: ruang diisi antrean, dokumen, produk, dan keputusan; tidak ada bagian promosi. |
| C-4, ketahanan UI | PASS: workspace loading/empty/error/retry, keyboard, desktop, dan mobile diperiksa; kedua form juga diperiksa pada layar sempit. |
| C-5, bukti | PASS: angka server, screenshot nyata, dan hasil tes dipisahkan dari batas penggunaan yang belum dinyatakan. |
| R-05, pola halaman | PASS: workspace operasional, tabel dan form sesuai tugas; tidak memakai pola landing page. |
| R-11, radius | PASS: kontrol dan tabel mengikuti bentuk native; tidak menyeragamkan semua komponen menjadi pill. |
| R-15, label tindakan | PASS: Submit for Approval, Create RFQ, Resolve without return, dan Create return transfer menyebut tindakan sebenarnya. |
| R-16, bahasa | PASS: teks menjelaskan pekerjaan dan batas fitur, tanpa slogan teknologi. |
| R-20, identitas tugas | PASS: field gudang, estimasi, receipt sumber, jumlah retur, dan keputusan membentuk alur distributor; tidak bergantung pada logo untuk menyatakan fungsi. |
| R-21, tema terang | PASS: memakai tema native untuk konsistensi dengan aplikasi ERP yang menjadi dependensi. |
| R-29, palet | PASS: palet native ditambah warna teks label yang lebih terbaca; status mengikuti arti native Odoo. |
| R-30, konsistensi produk | PASS: addon sengaja menjadi bagian Odoo; tidak meniru tampilan produk lain sebagai identitas baru. |
| R-31, alasan visual | PASS: setiap pilihan utama memiliki alasan singkat pada DESIGN dan tabel komponen. |
