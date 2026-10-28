# SupplyFlow Office: kebutuhan produk

SupplyFlow Office adalah proyek ERP untuk distributor perlengkapan kantor. Proyek ini memakai Odoo Community untuk penjualan, pembelian, dan perpindahan stok. Addon Python `supplyflow_office` menambahkan permintaan pembelian internal serta penanganan masalah penerimaan barang.

Dokumen ini menetapkan target implementasi. Hasil pengujian, perintah yang sudah dijalankan, dan screenshot harus dicatat terpisah setelah aplikasi berjalan. Daftar kebutuhan di bawah tidak menyatakan bahwa seluruh target sudah lulus.

## Masalah yang ditangani

Staf perlu meminta pembelian kertas, alat tulis, atau perlengkapan printer sebelum petugas pembelian mengirim permintaan penawaran kepada pemasok. Catatan permintaan harus menunjukkan siapa yang mengajukan, siapa yang menyetujui, dan RFQ mana yang dibuat dari permintaan itu.

Petugas gudang juga perlu mencatat barang rusak, barang yang tidak sesuai, atau kekurangan barang pada penerimaan. Persetujuan kasus dan perpindahan fisik barang mempunyai waktu serta pelaksana yang berbeda. Menyetujui retur harus membuat dokumen retur Odoo yang masih perlu diperiksa dan divalidasi gudang.

## Pengguna dan pembagian tugas

| Peran | Tugas | Batas akses addon |
| --- | --- | --- |
| Pengaju | Menulis permintaan pembelian dan melaporkan masalah penerimaan | Mengelola dokumennya sendiri pada perusahaan yang diizinkan; tidak menyetujui pengajuannya sendiri |
| Penyetuju | Meninjau kebutuhan dan memutuskan penanganan masalah | Membaca dan memutuskan dokumen dalam perusahaan yang diizinkan; wajib orang lain dari pengaju/pembuat |
| Petugas pembelian | Mengolah RFQ dan purchase order | Menggunakan izin Purchase bawaan Odoo; izin penyetuju addon saja tidak otomatis memberi seluruh izin Purchase |
| Petugas gudang | Menerima, mengirim, dan meretur barang | Menggunakan izin Inventory bawaan Odoo; persetujuan addon tidak memvalidasi picking secara otomatis |
| Administrator | Menyiapkan perusahaan, gudang, pengguna, dan izin | Menjaga konfigurasi; aturan persetujuan mandiri tetap berlaku pada aksi bisnis addon |

Kelompok addon menggunakan XML ID `supplyflow_office.group_user` dan `supplyflow_office.group_approver`. Izin Purchase dan Inventory diberikan terpisah melalui kelompok Odoo masing-masing.

Satu akun dapat memiliki beberapa peran. Kombinasi peran tidak menghapus larangan menyetujui dokumen sendiri. Akun superuser dan akses langsung ke database berada di luar batas perlindungan aplikasi biasa.

## Lingkup standar dan tambahan

| Kebutuhan | Pelaksana |
| --- | --- |
| Produk, pemasok, pelanggan, satuan produk | Model dan tampilan Odoo |
| Sales quotation, sales order, delivery | Odoo Sales dan Inventory |
| RFQ, purchase order, receipt, backorder | Odoo Purchase dan Inventory |
| Gudang, lokasi, stok, perpindahan internal | Odoo Inventory |
| Dokumen retur pemasok dan validasi pergerakannya | Mekanisme retur Odoo |
| Permintaan pembelian internal dan persetujuan independen | Addon `supplyflow_office` |
| Hubungan permintaan dengan RFQ yang dihasilkan | Addon `supplyflow_office` |
| Kasus masalah receipt dan keputusan penyelesaiannya | Addon `supplyflow_office` |
| Hubungan kasus dengan retur pemasok | Addon `supplyflow_office` |

Addon mengatur dokumen yang melewati alurnya. Pengguna yang memang memiliki hak native Odoo tetap dapat membuat RFQ atau retur di luar addon. Proyek tidak mengklaim seluruh transaksi native wajib melalui persetujuan SupplyFlow.

## Permintaan pembelian

### Data

Model `supplyflow.request` memuat nomor permintaan, perusahaan, mata uang perusahaan, pengaju, pemasok, gudang tujuan, tanggal kebutuhan, alasan kebutuhan, baris produk, estimasi sebelum pajak, catatan keputusan, pelaksana/waktu pengajuan dan keputusan, serta hubungan ke purchase order.

Model `supplyflow.request.line` memuat produk, deskripsi, satuan dasar produk, jumlah, estimasi harga satuan, dan subtotal. Estimasi membantu peninjauan kebutuhan; nilainya bukan saldo anggaran, harga kontrak, atau jaminan harga RFQ akhir.

### Status dan aturan

| Status teknis | Makna | Transisi yang diizinkan |
| --- | --- | --- |
| `draft` | Pengaju masih mengisi dokumen | Ajukan atau batalkan |
| `submitted` | Dokumen menunggu peninjauan | Setujui, tolak dengan alasan, atau batalkan oleh pengaju |
| `approved` | Penyetuju menerima permintaan | Buat RFQ; pembatalan oleh penyetuju independen harus beralasan |
| `rejected` | Penyetuju menolak dan mencatat alasan | Pengaju mengembalikan ke draft atau membatalkan |
| `rfq_created` | RFQ telah ditautkan | Buka RFQ yang sama; tidak membuat RFQ kedua |
| `cancelled` | Siklus permintaan dihentikan | Tidak diproses lebih lanjut |

Pengaju harus melengkapi pemasok, gudang, alasan, dan sekurangnya satu baris produk yang valid. Jumlah harus lebih dari nol; estimasi harga tidak boleh negatif. Produk dan gudang harus sesuai perusahaan atau boleh dipakai bersama menurut aturan Odoo.

Setelah pengajuan, isi komersial dan baris produk dibekukan. Pengguna tidak boleh mengganti perusahaan, pengaju, pemasok, gudang, produk, jumlah, atau harga melalui form maupun RPC. Catatan keputusan hanya dibuka pada tindakan yang memerlukannya. Tombol tersembunyi bukan mekanisme pengamanan utama; metode server harus memeriksa akses, peran, pemilik, dan status.

Pengembalian dokumen yang ditolak ke draft memulai siklus peninjauan berikutnya. Metadata keputusan aktif dibersihkan, sedangkan riwayat percakapan sebelumnya tetap dapat dibaca. Perubahan pada draft yang diajukan ulang harus ditinjau lagi.

Pembuatan RFQ memakai operasi incoming gudang yang dipilih. Aksi ini membutuhkan persetujuan addon dan hak membuat purchase order native. Klik berulang atau panggilan bersamaan harus mengembalikan RFQ tertaut yang sama. RFQ yang dihasilkan masih berstatus draft dan dapat diolah petugas pembelian menurut aturan Odoo; persetujuan permintaan tidak mengonfirmasi purchase order.

## Masalah penerimaan dan retur

### Data dan batas kasus

Model `supplyflow.issue` mencatat receipt sumber, perusahaan, pelapor, jenis masalah, uraian, baris barang, keputusan penyetuju, catatan penyelesaian, dan tautan picking retur bila ada. Baris kasus menunjuk produk/pergerakan dari receipt sumber, bukan produk bebas yang tidak pernah diterima.

Kasus hanya memakai receipt masuk yang sudah selesai. Jenis masalah meliputi barang rusak (`damage`), barang tidak sesuai (`wrong_item`), dan kekurangan barang (`shortage`). Kekurangan berarti barang tidak tersedia untuk dikirim balik; kasus tersebut harus ditangani melalui catatan penyelesaian, bukan retur fisik atas barang yang tidak diterima.

### Alur keputusan

1. Pelapor membuat kasus, memilih receipt, lalu menjelaskan barang dan jumlah yang bermasalah.
2. Pelapor mengajukan kasus. Isi pokok kasus dibekukan untuk peninjauan.
3. Penyetuju lain menyetujui atau menolak dengan alasan. Penolakan dapat dikembalikan ke draft oleh pelapor untuk diperbaiki.
4. Untuk barang yang benar-benar ada dan dapat diretur, penyetuju membuat picking retur melalui mekanisme Odoo. Kasus menautkan satu picking; panggilan berulang tidak membuat retur baru.
5. Petugas gudang memeriksa lokasi, jumlah, lot/serial bila digunakan, lalu memvalidasi retur dari Inventory. Pembuatan picking belum mengurangi stok.
6. Untuk penyelesaian tanpa perpindahan barang, penyetuju memasukkan catatan keputusan. Catatan itu tidak membuat kredit pemasok atau jurnal akuntansi.

Retur harus mengikuti produk, satuan, perusahaan, lokasi, dan jumlah yang masih dapat diretur dari receipt sumber. Picking yang dibatalkan atau belum selesai tidak boleh menjadi sumber. Kasus yang telah menghasilkan retur tidak boleh menghasilkan retur kedua melalui addon. Retur manual di luar addon tetap diperhitungkan dalam batas jumlah yang masih tersedia.

## Penjualan, pembelian, dan beberapa gudang

Penjualan memakai alur quotation, sales order, delivery, dan validasi pengiriman Odoo. Pembelian memakai RFQ, purchase order, receipt, dan validasi penerimaan Odoo. Penerimaan/pengiriman sebagian dapat menghasilkan backorder sesuai pilihan pengguna dan perilaku Odoo.

Beberapa gudang memakai konfigurasi Odoo. Permintaan pembelian memilih gudang penerima agar dokumen pembelian tidak selalu menggunakan gudang default. Proyek tidak menambahkan mesin stok terpisah dan tidak mengubah kuantitas langsung untuk menyelesaikan kasus.

## Workspace pekerjaan

Halaman workspace menggunakan komponen Owl di dalam web client Odoo. Ringkasannya berasal dari data yang boleh dibaca pengguna: permintaan yang menunggu persetujuan, kasus yang menunggu keputusan, kasus terbuka yang melewati tenggat, dan picking retur kasus yang belum selesai atau dibatalkan. Daftar permintaan terbaru serta tautan ke incoming, outgoing, dan purchase order membantu pengguna membuka pekerjaan yang mendasarinya.

Workspace tidak menampilkan nilai stok, omzet, saldo anggaran, atau metrik kinerja yang belum mempunyai perhitungan. Angka ringkasan dan daftar harus tunduk pada pembatasan perusahaan serta record rule yang sama dengan tampilan dokumen.

## Keamanan dan jejak keputusan

ACL mengatur akses model; record rule membatasi perusahaan serta kepemilikan dokumen pengaju. Metode aksi memeriksa ulang izin, status, pemilik, dan larangan persetujuan mandiri. Penulisan langsung terhadap status, metadata persetujuan, dan tautan hasil harus ditolak bagi pengguna aplikasi biasa.

Perubahan status dan keputusan dicatat pada chatter. Riwayat ini membantu penelusuran internal, tetapi bukan log yang kebal perubahan oleh administrator database. Data receipt dan purchase order tertaut tetap mengikuti izin model native masing-masing.

Skenario dua perusahaan harus diuji dengan akun yang hanya diizinkan pada satu perusahaan. Mengetahui ID dokumen perusahaan lain tidak boleh memberi akses lewat form atau RPC. Akun multi-perusahaan hanya melihat perusahaan yang diizinkan dan aktif pada sesi Odoo.

## Instalasi dan data latihan

Target instalasi lokal memakai Docker Compose, Odoo Community `19.0-20261015`, dan PostgreSQL 17. Aplikasi hanya dipublikasikan ke `127.0.0.1:8070`. Port database tidak dibuka ke host. Versi 19 dipilih secara sengaja untuk implementasi ini; dokumen tidak menyebutnya sebagai versi Odoo terbaru.

Setup harus membuat kredensial lokal yang tidak masuk Git. Password master Odoo, password role database, dan password pengguna aplikasi adalah tiga hal berbeda. Instalasi normal tidak boleh menyisakan login aktif `admin/admin`.

Kontrak script menggunakan `scripts/Start.ps1` untuk build, inisialisasi, dan menyalakan stack. Opsi `-WithTrainingData` memilih data latihan. Kredensial login hasil setup disimpan lokal pada `.secrets/LOCAL-CREDENTIALS.txt`, yang wajib diabaikan Git. Script tambahan mencakup `Stop.ps1`, `Test.ps1`, `Backup.ps1`, `Restore.ps1`, dan `Load-TrainingData.ps1`. Detail argumen serta hasil eksekusi perlu diselaraskan dengan kode script sebelum rilis.

Data latihan bersifat opt-in dan diberi nama yang jelas. Data itu dapat menyediakan produk perlengkapan kantor, pemasok/pelanggan sintetis, gudang, dan transaksi untuk memeriksa alur. Instalasi tanpa pilihan data latihan tidak boleh diam-diam membuat transaksi contoh atau memakai data pribadi pengguna.

## Kriteria penerimaan

Semua baris berikut merupakan target yang perlu dibuktikan sebelum rilis. Hasil akhir harus mencantumkan jenis pemeriksaan dan keterbatasannya, bukan sekadar mengulang daftar kebutuhan.

| ID | Skenario | Bukti yang diminta |
| --- | --- | --- |
| A01 | Setup baru menginisialisasi database, memasang addon, dan membuka login lokal | Log setup dan pemeriksaan HTTP/UI pada database kosong |
| A02 | Instalasi tanpa data latihan tidak mengandung transaksi latihan | Pemeriksaan database atau ORM setelah setup |
| A03 | Pengaju membuat permintaan valid, mengajukan, dan membuka dokumennya kembali | Tes ORM dan alur browser |
| A04 | Pengajuan kosong, jumlah nol/negatif, dan harga negatif ditolak | Tes validasi dengan pesan yang dapat ditindaklanjuti |
| A05 | Pengaju yang juga penyetuju gagal menyetujui dokumennya sendiri | Tes metode server, termasuk pembuat yang mengganti data lewat RPC |
| A06 | Isi dan baris permintaan tidak dapat diubah setelah pengajuan | Tes `write`, create/unlink baris, dan field audit/status tertutup |
| A07 | Penolakan memerlukan alasan; reset ke draft memerlukan pengajuan ulang | Tes transisi dan riwayat chatter |
| A08 | Permintaan disetujui menghasilkan satu RFQ pada gudang yang dipilih | Tes hubungan, operasi incoming, dan pengulangan aksi |
| A09 | Pengguna tanpa izin native Purchase tidak memperoleh hak lewat aksi RFQ | Tes ACL/record rule pada akun terbatas |
| A10 | Pemrosesan bersamaan tidak membuat RFQ ganda | Tes dengan transaksi/koneksi terpisah, bukan dua klik berurutan saja |
| A11 | Kasus tidak dapat memakai picking belum selesai, outgoing, atau perusahaan terlarang | Tes validasi dan isolasi perusahaan |
| A12 | Penyetuju independen membuat satu retur dari kasus barang yang dapat dikembalikan | Tes hubungan, kuantitas, dan pengulangan aksi |
| A13 | Kekurangan barang diselesaikan dengan catatan; tidak dibuat retur barang yang tidak diterima | Tes kasus shortage dan tampilan keputusan |
| A14 | Retur kasus menghormati retur sebelumnya dan stok hanya berubah setelah validasi gudang | Tes receipt/return native dan pemeriksaan kuantitas |
| A15 | Penjualan sampai delivery dan pembelian sampai receipt bekerja dengan addon terpasang | Tes integrasi native, termasuk penerimaan/pengiriman sebagian yang dipilih |
| A16 | Pengguna perusahaan A tidak membaca atau mengubah dokumen perusahaan B | Tes pencarian, pembacaan ID langsung, dan aksi bisnis |
| A17 | Form, daftar, pencarian, status, kesalahan, dan navigasi keyboard dapat dipakai | Pemeriksaan browser pada tampilan desktop serta layar sempit yang dicatat |
| A18 | Restart tidak menghapus data, lampiran, dan relasi dokumen | Pemeriksaan database dan filestore setelah restart |
| A19 | Cadangan database dan filestore dapat dipulihkan bersama | Pemulihan pada lingkungan terpisah dan pemeriksaan data/lampiran |
| A20 | README menjelaskan batas standar/custom dan menunjukkan UI aplikasi yang benar-benar dijalankan | Pemeriksaan dokumentasi, tautan lokal, dan screenshot nyata |

## Di luar lingkup

Proyek tidak mengimplementasikan akuntansi anggaran, pembayaran, penggajian, perpajakan Indonesia, integrasi bank, marketplace, atau kepatuhan bisnis tertentu. Proyek juga tidak memerlukan addon Enterprise, tidak mengganti seluruh antarmuka Odoo, dan tidak menyediakan server publik produksi.

Katalog, pemasok, dan transaksi latihan tidak mewakili pelanggan nyata. Screenshot dan angka hasil pengujian baru boleh ditambahkan setelah diperoleh dari aplikasi yang berjalan.
