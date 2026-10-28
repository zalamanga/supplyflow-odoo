# Membuat ERP Odoo dari nol: SupplyFlow Office

Panduan ini mengikuti kode SupplyFlow Office untuk distributor perlengkapan kantor. Kamu akan menyiapkan Odoo, membuat addon Python, menghubungkannya ke tampilan, kemudian mengikuti permintaan pembelian sampai RFQ dan kasus receipt sampai retur pemasok.

Odoo sudah menyediakan login, pengguna, perusahaan, Purchase, Inventory, Sales, ORM, dan web client. Pekerjaan kita adalah membuat addon yang memperluas bagian tersebut. Karena itu, tutorial tidak meminta kamu membuat mesin stok atau login baru.

## Mulai dari sini

| Urutan | Bab | Hasil belajar |
| --- | --- | --- |
| 1 | [Persiapan dan Docker](01-persiapan-dan-docker.md) | Memahami server, database, container, volume, secret, dan proses startup |
| 2 | [Kerangka addon dan hak akses](02-kerangka-addon-dan-akses.md) | Membuat addon minimal yang dapat dipasang, model pertama, menu, ACL, dan record rule |
| 3 | [Model permintaan dan RFQ](03-model-permintaan-dan-rfq.md) | Menulis field, perhitungan, validasi, persetujuan, dan pembuatan RFQ native |
| 4 | [Receipt, masalah, dan retur](04-receipt-masalah-dan-retur.md) | Menghubungkan kasus dengan barang yang diterima dan membuat retur yang jumlahnya dibatasi |
| 5 | [Tampilan, workspace, dan PDF](05-tampilan-workspace-dan-pdf.md) | Menghubungkan XML, tombol Python, Owl, dan QWeb serta melengkapi addon akhir |
| 6 | [Pengujian dan debugging](06-pengujian-dan-debugging.md) | Membaca tes nyata, menjalankan database uji terpisah, dan mencari sumber kesalahan |
| 7 | [Operasi dan latihan](07-operasi-dan-latihan.md) | Memahami seed, backup/restore, menjalankan satu kasus lengkap, dan mengembangkan perubahan kecil |
| 8 | [Indeks file dan fungsi](08-indeks-file-dan-fungsi.md) | Mencari file, class, fungsi, serta lokasi pembahasannya |

Istilah baru dijelaskan saat pertama dipakai. Tidak perlu memahami semua isi `purchase_request.py` sebelum mencoba bab pertama.

## Pilih cara mengikuti

**Membaca sambil membuka proyek yang sudah jadi.** Gunakan folder `D:\kerjaan\done push repo\supplyflow-odoo`. Buka file yang ditautkan, cocokkan fungsi dengan penjelasannya, dan gunakan akun latihan untuk checkpoint UI. Jangan mengganti source proyek utama dengan contoh kerangka minimal bab 2.

**Membangun ulang sebagai latihan.** Bab 1 menyiapkan folder baru `D:\Latihan-Odoo\supplyflow-office` dan proyek Compose bernama `supplyflow-belajar`. Bab 2 merupakan checkpoint addon minimal. Bab 3 dan 4 menjelaskan penggantian model dengan implementasi lengkap. Bab 5 menyatukan seluruh file final sebelum instalasi/update berikutnya. Tidak perlu menyalin `node_modules`, database, arsip, atau secret proyek utama.

Folder latihan bersifat pilihan. Jika tujuanmu memahami kode, cukup gunakan proyek utama agar tidak menambah salinan yang membingungkan.

## Versi PDF

[Unduh buku tutorial PDF](supplyflow-office-tutorial.pdf). PDF memiliki daftar isi bernomor halaman dan bookmark bab. Jika baris kode panjang terbungkus pada PDF, gunakan berkas Markdown atau source yang ditautkan untuk menyalin kode dengan susunan baris asli.

PDF dibuat dari sembilan berkas Markdown pada folder ini menggunakan [build_tutorial_pdf.py](../../scripts/build_tutorial_pdf.py). Untuk membuat ulang, pasang paket Python `reportlab` pada environment tooling yang kamu gunakan, lalu jalankan `python scripts/build_tutorial_pdf.py --publish-copy` dari root repo. Odoo tidak memerlukan generator PDF tutorial ini untuk berjalan.

## Cara membaca contoh kode

- **Isi lengkap file:** boleh ditulis sebagai isi file yang disebutkan. Jika file sudah berisi versi contoh sebelumnya, ganti isinya; jangan menambahkan class kedua dengan nama yang sama.
- **Cuplikan class/fungsi:** menunjukkan bagian dari file final. Pertahankan import, decorator, field, dan fungsi lain dari source lengkap. Jangan menimpa satu file dengan satu cuplikan.
- **Perintah PowerShell:** dijalankan di terminal Windows pada folder yang disebutkan.
- **Kode ORM:** dijalankan pada shell/test Odoo yang menyediakan `env`, bukan pada Python biasa di Windows.
- **Hasil yang diharapkan:** checkpoint untuk praktikmu. Ini tidak berarti contoh perantara telah diuji sebagai paket aplikasi final.

File final yang ditautkan adalah rujukan utuh. Proyek final telah lulus 42 tes ORM, 25 tes arsip, dan sembilan workflow browser pada [CI yang dicatat](../VERIFICATION.md). Kerangka bab 2 tidak memiliki seluruh fitur atau pengamanan aplikasi akhir.

## Pemeriksaan panduan

Pada 28 Oktober 2026, sembilan file starter diekstrak dari blok kode bab 2 dan dipasang memakai image proyek ke database uji kosong yang terpisah. Instalasi berhasil; konfigurasi pertama, model minimal, daftar kosong, grup admin, action, menu, dan view diperiksa. Database itu kemudian di-update dengan addon final sesuai tahap bab 5: modul berstatus installed, keempat model bisnis tersedia, permintaan/kasus tetap kosong, dan menu root tidak menjadi duplikat.

Pemeriksaan tersebut mencakup instalasi/konfigurasi model serta metadata view melalui Odoo, bukan click-through browser baru untuk kerangka minimal. Hasil browser aplikasi lengkap mengacu ke verifikasi proyek yang sudah dicatat. Database dan filestore uji dibersihkan sesudahnya; source dan database proyek utama tidak digunakan sebagai tempat menulis transaksi percobaan.

## Peta hubungan paling awal

```text
Browser di localhost:8070
  -> web client Odoo: menampilkan form dan mengirim aksi
  -> method model Python: memeriksa izin dan aturan bisnis
  -> ORM: membaca/menulis record PostgreSQL
  -> respons: form, status, atau dokumen native yang dibuka

Docker Compose
  -> container Odoo: menjalankan server dan addon
  -> container PostgreSQL: menyimpan data relasional
  -> volume Odoo: menyimpan filestore/lampiran
```

Saat menekan **Create RFQ**, browser memanggil method Python. Method itulah yang membuat `purchase.order`. XML hanya menghubungkan tombol dengan method dan mengatur tampilan.

## Versi dan rujukan

Panduan memakai Odoo Community 19 dan source implementasi commit `ad7be04`, dengan pembaruan dokumentasi setelahnya. Nama API mengikuti versi itu, misalnya `stock.move.quantity`, `models.Constraint`, dan `<list>`. Jangan menggantinya dengan contoh versi lain tanpa memeriksa perbedaan API.

Rujukan utama tetap source proyek. Dokumentasi resmi untuk penjelasan platform: [arsitektur Odoo](https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/01_architecture.html), [ORM](https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html), [hak akses](https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html), dan [pengujian](https://www.odoo.com/documentation/19.0/developer/reference/backend/testing.html).
