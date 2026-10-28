# 08. Indeks file, class, dan fungsi

Gunakan bab ini ketika sudah tahu pertanyaannya tetapi belum tahu file yang perlu dibuka. Nomor bab mengarah ke penjelasan bertahap. Tautan fungsi memakai `#L` untuk baris definisi pada source final; jika kode diubah kemudian, cari nama fungsinya karena nomor baris dapat bergeser.

`Masukan` berarti argumen atau record yang dibaca. `Hasil/efek` membedakan nilai yang dikembalikan dari perubahan database, file, atau tampilan. Fungsi compute biasanya mengisi field dan tidak mengembalikan dokumen baru. Fungsi pemeriksaan umumnya melanjutkan operasi bila sah atau menaikkan exception bila tidak sah.

## Peta semua berkas teks proyek

Path pada tabel relatif terhadap root repo. Berkas teks di bawah mencakup konfigurasi, source, pengujian, lisensi, dan dokumentasi. Secret lokal, arsip, dependensi, serta hasil tes memang tidak termasuk source yang dipublikasikan.

Inventaris fungsi ERP mengikuti source implementasi yang dijelaskan pada tutorial. Tool dokumentasi tambahan [scripts/build_tutorial_pdf.py](../../scripts/build_tutorial_pdf.py) membaca Markdown dan menghasilkan buku PDF dengan ReportLab; ia bukan bagian dari server ERP. Daftar operasi file, validasi, dan alur fungsi di bawah merujuk aplikasi serta alat operasinya.

### Akar dan CI

| Berkas | Untuk apa | Bab |
| --- | --- | --- |
| [.gitattributes](../../.gitattributes) | Aturan akhir baris LF untuk source tertentu dan penanda berkas biner. | [01](01-persiapan-dan-docker.md) |
| [.github/workflows/verify.yml](../../.github/workflows/verify.yml) | GitHub Actions menjalankan tes arsip, ORM, startup latihan, dan browser; menyimpan diagnostik jika gagal. | [06](06-pengujian-dan-debugging.md) |
| [.gitignore](../../.gitignore) | Mengecualikan secret, konfigurasi lokal, cadangan, dependensi, dan hasil tes dari Git. | [01](01-persiapan-dan-docker.md) / [07](07-operasi-dan-latihan.md) |
| [LICENSE](../../LICENSE) | Teks lisensi proyek dan ketentuan LGPL/GPL yang disertakan; bukan kode aplikasi. | [02](02-kerangka-addon-dan-akses.md) |
| [README.md](../../README.md) | Ringkasan fitur, screenshot, startup, batas kebijakan, dan tautan dokumentasi. | [01](01-persiapan-dan-docker.md) |
| [compose.test.yaml](../../compose.test.yaml) | Overlay yang mematikan healthcheck Odoo saat proses tes sekali jalan. | [06](06-pengujian-dan-debugging.md) |
| [compose.yaml](../../compose.yaml) | Dua layanan, image, secret, bind mount, volume, healthcheck, port localhost, dan batas memori Odoo. | [01](01-persiapan-dan-docker.md) |
| [package-lock.json](../../package-lock.json) | Versi dependensi npm terkunci untuk pemasangan ulang dengan npm ci. | [06](06-pengujian-dan-debugging.md) |
| [package.json](../../package.json) | Dependensi Playwright serta perintah browser test dan capture; bukan frontend ERP terpisah. | [06](06-pengujian-dan-debugging.md) |
| [playwright.config.js](../../playwright.config.js) | Browser, URL, satu worker, batas waktu, trace CI, dan direktori hasil pengujian. | [06](06-pengujian-dan-debugging.md) |



### Addon Python, keamanan, dan antarmuka

| Berkas | Untuk apa | Bab |
| --- | --- | --- |
| [addons/supplyflow_office/__init__.py](../../addons/supplyflow_office/__init__.py) | Memuat paket models ketika addon dibaca Odoo. | [02](02-kerangka-addon-dan-akses.md) |
| [addons/supplyflow_office/__manifest__.py](../../addons/supplyflow_office/__manifest__.py) | Identitas addon, dependensi, urutan data XML/CSV, dan daftar aset web. | [02](02-kerangka-addon-dan-akses.md) / [05](05-tampilan-workspace-dan-pdf.md) |
| [addons/supplyflow_office/data/sequences.xml](../../addons/supplyflow_office/data/sequences.xml) | Sequence nomor permintaan dan kasus pemasok. | [02](02-kerangka-addon-dan-akses.md) / [03](03-model-permintaan-dan-rfq.md) / [04](04-receipt-masalah-dan-retur.md) |
| [addons/supplyflow_office/models/__init__.py](../../addons/supplyflow_office/models/__init__.py) | Memuat purchase_request, supplier_issue, dan workspace agar model terdaftar. | [02](02-kerangka-addon-dan-akses.md) / [03](03-model-permintaan-dan-rfq.md) / [04](04-receipt-masalah-dan-retur.md) / [05](05-tampilan-workspace-dan-pdf.md) |
| [addons/supplyflow_office/models/purchase_request.py](../../addons/supplyflow_office/models/purchase_request.py) | Dua model permintaan dan baris: estimasi, CRUD terjaga, keputusan, revisi, konversi RFQ. | [03](03-model-permintaan-dan-rfq.md) |
| [addons/supplyflow_office/models/supplier_issue.py](../../addons/supplyflow_office/models/supplier_issue.py) | Kasus receipt, baris sumber, kuantitas retur, wizard native, dan revisi stock.move. | [04](04-receipt-masalah-dan-retur.md) |
| [addons/supplyflow_office/models/workspace.py](../../addons/supplyflow_office/models/workspace.py) | Model RPC tanpa tabel bisnis baru untuk hitungan dan daftar permintaan terakhir. | [05](05-tampilan-workspace-dan-pdf.md) |
| [addons/supplyflow_office/reports/purchase_request_report.xml](../../addons/supplyflow_office/reports/purchase_request_report.xml) | Action laporan dan template QWeb PDF ringkasan permintaan. | [05](05-tampilan-workspace-dan-pdf.md) |
| [addons/supplyflow_office/security/company_rules.xml](../../addons/supplyflow_office/security/company_rules.xml) | Empat record rule yang membatasi dokumen dan baris pada perusahaan aktif. | [02](02-kerangka-addon-dan-akses.md) |
| [addons/supplyflow_office/security/groups.xml](../../addons/supplyflow_office/security/groups.xml) | Peran SupplyFlow User dan Approver serta hubungan grupnya. | [02](02-kerangka-addon-dan-akses.md) |
| [addons/supplyflow_office/security/ir.model.access.csv](../../addons/supplyflow_office/security/ir.model.access.csv) | Hak CRUD model untuk grup; pemeriksaan pemilik dan status dilanjutkan di Python. | [02](02-kerangka-addon-dan-akses.md) / [03](03-model-permintaan-dan-rfq.md) / [04](04-receipt-masalah-dan-retur.md) |
| [addons/supplyflow_office/static/src/workspace.js](../../addons/supplyflow_office/static/src/workspace.js) | Komponen Owl memuat RPC, keadaan tampilan, dan navigasi ke dokumen native. | [05](05-tampilan-workspace-dan-pdf.md) |
| [addons/supplyflow_office/static/src/workspace.scss](../../addons/supplyflow_office/static/src/workspace.scss) | Gaya workspace dan penyesuaian form pada layar kecil. | [05](05-tampilan-workspace-dan-pdf.md) |
| [addons/supplyflow_office/static/src/workspace.xml](../../addons/supplyflow_office/static/src/workspace.xml) | Template Owl untuk loading, error, kosong, metrik, dan daftar terbaru. | [05](05-tampilan-workspace-dan-pdf.md) |
| [addons/supplyflow_office/views/menus.xml](../../addons/supplyflow_office/views/menus.xml) | Menu SupplyFlow dan client action workspace. | [05](05-tampilan-workspace-dan-pdf.md) |
| [addons/supplyflow_office/views/purchase_request_views.xml](../../addons/supplyflow_office/views/purchase_request_views.xml) | List, form, search, tombol workflow, dan window action permintaan. | [03](03-model-permintaan-dan-rfq.md) / [05](05-tampilan-workspace-dan-pdf.md) |
| [addons/supplyflow_office/views/supplier_issue_views.xml](../../addons/supplyflow_office/views/supplier_issue_views.xml) | List, form, search, tombol kasus, dan smart button pembuka retur. | [04](04-receipt-masalah-dan-retur.md) / [05](05-tampilan-workspace-dan-pdf.md) |



### Script operasional

| Berkas | Untuk apa | Bab |
| --- | --- | --- |
| [scripts/Backup.ps1](../../scripts/Backup.ps1) | Menghentikan penulis Odoo, menjalankan job backup, menyalin ZIP, dan membersihkan job terverifikasi. | [07](07-operasi-dan-latihan.md) |
| [scripts/Common.ps1](../../scripts/Common.ps1) | Fungsi Compose bersama, password acak, secret, konfigurasi, dan petunjuk login lokal. | [01](01-persiapan-dan-docker.md) / [07](07-operasi-dan-latihan.md) |
| [scripts/Load-TrainingData.ps1](../../scripts/Load-TrainingData.ps1) | Memuat data latihan sambil menghentikan aplikasi dan mempertahankan keadaan start/stop sebelumnya. | [07](07-operasi-dan-latihan.md) |
| [scripts/Restore.ps1](../../scripts/Restore.ps1) | Opsi penggantian wajib, validasi awal, penghentian Odoo, restore, dan kebijakan restart jika berhasil. | [07](07-operasi-dan-latihan.md) |
| [scripts/Start.ps1](../../scripts/Start.ps1) | Inisialisasi konfigurasi, pull opsional, start database, install addon, seed opsional, lalu start Odoo. | [01](01-persiapan-dan-docker.md) |
| [scripts/Stop.ps1](../../scripts/Stop.ps1) | Menghentikan layanan proyek tanpa menghapus volume data. | [01](01-persiapan-dan-docker.md) / [07](07-operasi-dan-latihan.md) |
| [scripts/Test.ps1](../../scripts/Test.ps1) | Database uji bernama unik, instalasi dan tes addon, lalu pembersihan kecuali KeepDatabase. | [06](06-pengujian-dan-debugging.md) |
| [scripts/container/backup.py](../../scripts/container/backup.py) | Membuat ZIP privat berisi dump custom PostgreSQL, filestore, manifest, ukuran, dan SHA-256. | [07](07-operasi-dan-latihan.md) |
| [scripts/container/clean_test_filestore.py](../../scripts/container/clean_test_filestore.py) | Script tanpa fungsi: menghapus hanya filestore dengan pola nama database tes dan path yang diperiksa. | [06](06-pengujian-dan-debugging.md) |
| [scripts/container/configure_instance.py](../../scripts/container/configure_instance.py) | Script shell Odoo satu kali: admin, grup, perusahaan IDR, URL, dan penanda initialized; tidak mendefinisikan fungsi. | [01](01-persiapan-dan-docker.md) / [07](07-operasi-dan-latihan.md) |
| [scripts/container/init-database.sh](../../scripts/container/init-database.sh) | Membuat role supplyflow yang tidak superuser dan mengatur pemilik database saat volume PostgreSQL baru diinisialisasi. | [01](01-persiapan-dan-docker.md) |
| [scripts/container/manage.py](../../scripts/container/manage.py) | Dispatcher initialize/update/seed dan pemanggilan shell Odoo. | [01](01-persiapan-dan-docker.md) / [07](07-operasi-dan-latihan.md) |
| [scripts/container/restore.py](../../scripts/container/restore.py) | Memvalidasi arsip dan memulihkan database tetap supplyflow serta filestore staging. | [07](07-operasi-dan-latihan.md) |
| [scripts/container/training_data.py](../../scripts/container/training_data.py) | Seed sintetis opsional melalui workflow nyata dengan XML ID untuk penggunaan ulang record. | [07](07-operasi-dan-latihan.md) |



### Pengujian

| Berkas | Untuk apa | Bab |
| --- | --- | --- |
| [addons/supplyflow_office/tests/__init__.py](../../addons/supplyflow_office/tests/__init__.py) | Memuat empat file pengujian ORM saat tes addon dijalankan. | [06](06-pengujian-dan-debugging.md) |
| [addons/supplyflow_office/tests/test_distribution_flow.py](../../addons/supplyflow_office/tests/test_distribution_flow.py) | Dua tes end-to-end ORM: receipt sebagian/backorder/retur/delivery dan transfer dua gudang. | [04](04-receipt-masalah-dan-retur.md) / [06](06-pengujian-dan-debugging.md) |
| [addons/supplyflow_office/tests/test_purchase_request.py](../../addons/supplyflow_office/tests/test_purchase_request.py) | 17 tes permintaan: RFQ, harga nol, revisi, izin, perusahaan, angka, context, dan mutasi baris. | [03](03-model-permintaan-dan-rfq.md) / [06](06-pengujian-dan-debugging.md) |
| [addons/supplyflow_office/tests/test_supplier_issue.py](../../addons/supplyflow_office/tests/test_supplier_issue.py) | 20 tes kasus: retur, reservasi pending, shortage, konteks wizard, sumber, peran, dan angka. | [04](04-receipt-masalah-dan-retur.md) / [06](06-pengujian-dan-debugging.md) |
| [addons/supplyflow_office/tests/test_workspace.py](../../addons/supplyflow_office/tests/test_workspace.py) | Tiga tes hitungan berdasarkan record dan penolakan pengguna tanpa peran. | [05](05-tampilan-workspace-dan-pdf.md) / [06](06-pengujian-dan-debugging.md) |
| [tests/browser/helpers.js](../../tests/browser/helpers.js) | Delapan helper login, RPC, klik workflow tersinkron, indeks latihan, dan navigasi. | [06](06-pengujian-dan-debugging.md) |
| [tests/browser/screenshots.spec.js](../../tests/browser/screenshots.spec.js) | Satu skenario capture menghasilkan delapan screenshot dari aplikasi yang berjalan. | [05](05-tampilan-workspace-dan-pdf.md) / [06](06-pengujian-dan-debugging.md) |
| [tests/browser/workflows.spec.js](../../tests/browser/workflows.spec.js) | Sembilan skenario browser: workspace, gagal/retry, PDF, form, reviewer, retur, revisi, shortage, dan konkurensi HTTP. | [06](06-pengujian-dan-debugging.md) |
| [tests/test_backup_archive.py](../../tests/test_backup_archive.py) | 25 unit test validator ZIP dengan arsip sintetis; tidak memerlukan Docker. | [06](06-pengujian-dan-debugging.md) / [07](07-operasi-dan-latihan.md) |



### Dokumentasi pendamping

| Berkas | Untuk apa | Bab |
| --- | --- | --- |
| [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) | Pemisahan proses Odoo standar, addon, database, server, dan batas kebijakan. | [01](01-persiapan-dan-docker.md) / [02](02-kerangka-addon-dan-akses.md) |
| [docs/CODE-GUIDE.md](../../docs/CODE-GUIDE.md) | Panduan source singkat sebagai pendamping tutorial bertahap ini. | [03](03-model-permintaan-dan-rfq.md) / [04](04-receipt-masalah-dan-retur.md) / [05](05-tampilan-workspace-dan-pdf.md) |
| [docs/DELIVERY-GATE.md](../../docs/DELIVERY-GATE.md) | Pemeriksaan tampilan, keyboard, kontras, error, dan layar kecil. | [05](05-tampilan-workspace-dan-pdf.md) / [06](06-pengujian-dan-debugging.md) |
| [docs/DESIGN.md](../../docs/DESIGN.md) | Keputusan tampilan operasi yang mengikuti antarmuka native Odoo. | [05](05-tampilan-workspace-dan-pdf.md) |
| [docs/FLOWS.md](../../docs/FLOWS.md) | Diagram alur pembelian, penerimaan, penjualan, transfer, dan penyelesaian pemasok. | [03](03-model-permintaan-dan-rfq.md) / [04](04-receipt-masalah-dan-retur.md) |
| [docs/OPERATIONS.md](../../docs/OPERATIONS.md) | Perintah operasional, secret, backup, restore, diagnosis, dan batas pemulihan. | [07](07-operasi-dan-latihan.md) |
| [docs/PRD.md](../../docs/PRD.md) | Kebutuhan distributor, pelaku, ruang lingkup, dan kriteria penerimaan. | [01](01-persiapan-dan-docker.md) |
| [docs/VERIFICATION.md](../../docs/VERIFICATION.md) | Bukti tes, PDF, konkurensi, backup/restore, dan batas hasil verifikasi. | [06](06-pengujian-dan-debugging.md) / [07](07-operasi-dan-latihan.md) |



Folder [screenshots](../screenshots) berisi delapan PNG biner: `01-operations.png`, `02-purchase-requests.png`, `03-approved-request.png`, `04-native-purchase.png`, `05-supplier-resolution.png`, `06-native-receipt.png`, `07-native-sale.png`, dan `08-mobile-workspace.png`. Screenshot memperlihatkan data latihan/pemeriksaan lokal; kode pengambilannya ada pada `screenshots.spec.js`.

Tutorial ini sendiri terdiri dari [README](README.md) serta bab berikut. Ini juga berkas dokumentasi, bukan file yang perlu dimuat manifest addon.

| Berkas tutorial | Isi |
| --- | --- |
| [01-persiapan-dan-docker.md](01-persiapan-dan-docker.md) | Lingkungan lokal dan container |
| [02-kerangka-addon-dan-akses.md](02-kerangka-addon-dan-akses.md) | Checkpoint addon minimal dan akses |
| [03-model-permintaan-dan-rfq.md](03-model-permintaan-dan-rfq.md) | Permintaan, baris, persetujuan, RFQ |
| [04-receipt-masalah-dan-retur.md](04-receipt-masalah-dan-retur.md) | Receipt, kasus, dan retur |
| [05-tampilan-workspace-dan-pdf.md](05-tampilan-workspace-dan-pdf.md) | Penyatuan addon final, view, Owl, QWeb |
| [06-pengujian-dan-debugging.md](06-pengujian-dan-debugging.md) | Pengujian dan diagnosis |
| [07-operasi-dan-latihan.md](07-operasi-dan-latihan.md) | Seed, operasi, dan latihan utuh |
| [08-indeks-file-dan-fungsi.md](08-indeks-file-dan-fungsi.md) | Indeks yang sedang dibaca |



## Class Python: tempat menaruh field dan method

Nama class adalah nama pada source Python. Nama model Odoo adalah string `_name` atau model yang diperluas melalui `_inherit`. Ejaan `SupplyflowIssue` memang mengikuti source; jangan menggantinya dengan nama class lain saat mencari.

| Class dan source | Peran |
| --- | --- |
| [SupplyFlowRequest](../../addons/supplyflow_office/models/purchase_request.py#L8) | models.Model; tabel dokumen supplyflow.request, bidang kebutuhan dan jejak keputusan. |
| [SupplyFlowRequestLine](../../addons/supplyflow_office/models/purchase_request.py#L315) | models.Model; tabel supplyflow.request.line, daftar barang pada satu permintaan. |
| [SupplyflowIssue](../../addons/supplyflow_office/models/supplier_issue.py#L9) | models.Model; tabel supplyflow.issue, masalah pada receipt dan hasil review. |
| [SupplyflowIssueLine](../../addons/supplyflow_office/models/supplier_issue.py#L283) | models.Model; tabel supplyflow.issue.line, barang sumber dan jumlah terdampak. |
| [StockMove](../../addons/supplyflow_office/models/supplier_issue.py#L395) | Perluasan stock.move; menambah revisi internal, tidak membuat model bisnis pengganti. |
| [SupplyFlowWorkspace](../../addons/supplyflow_office/models/workspace.py#L5) | models.AbstractModel supplyflow.workspace; menyediakan RPC, bukan tabel transaksi baru. |



## Semua fungsi Python aplikasi dan script

Ada 86 definisi fungsi non-tes pada source ini, termasuk method class dan helper yang bersarang dalam `seed_training()`. Callback lambda tidak mempunyai nama `def` terpisah. Script `configure_instance.py` dan `clean_test_filestore.py` berjalan di tingkat file, sehingga fungsinya dijelaskan pada peta file.

Baris tabel berikut menyebut input serta hasil/efek utama; urutan pemanggilan dan cuplikan lengkap ada pada bab terkait. Pemeriksaan izin tambahan tetap dapat berlangsung di ORM atau model native yang dipanggil.

### Permintaan dan RFQ

Source: [addons/supplyflow_office/models/purchase_request.py](../../addons/supplyflow_office/models/purchase_request.py). Pembahasan: bab [03](03-model-permintaan-dan-rfq.md).

| Fungsi dan baris source | Masukan -> hasil/efek dan alasan |
| --- | --- |
| [SupplyFlowRequest._compute_amount_estimated](../../addons/supplyflow_office/models/purchase_request.py#L73) | Subtotal baris -> isi amount_estimated; tolak total di luar kemampuan mata uang. |
| [SupplyFlowRequest._onchange_company_id](../../addons/supplyflow_office/models/purchase_request.py#L85) | Perusahaan pada form -> pilih default gudang perusahaan itu untuk membantu pengisian. |
| [SupplyFlowRequest._check_request_details](../../addons/supplyflow_office/models/purchase_request.py#L91) | Record permintaan -> validasi tujuan, perusahaan pemasok, dan gudang; naikkan ValidationError bila tidak sesuai. |
| [SupplyFlowRequest._require_group](../../addons/supplyflow_office/models/purchase_request.py#L101) | ID grup (default User) -> tolak pengguna tanpa peran SupplyFlow yang diminta. |
| [SupplyFlowRequest._lock_for_change](../../addons/supplyflow_office/models/purchase_request.py#L105) | Recordset -> periksa hak tulis, flush, lock, invalidasi cache, periksa ulang akses sebelum perubahan. |
| [SupplyFlowRequest._require_requester](../../addons/supplyflow_office/models/purchase_request.py#L113) | Recordset -> tolak bila pengguna saat ini bukan pengaju salah satu dokumen. |
| [SupplyFlowRequest._require_independent_approver](../../addons/supplyflow_office/models/purchase_request.py#L117) | Recordset -> wajib Approver yang berbeda dari requester dan pembuat record. |
| [SupplyFlowRequest._require_draft](../../addons/supplyflow_office/models/purchase_request.py#L125) | Recordset -> wajib draft milik pengaju; dipakai bersama jalur edit isi. |
| [SupplyFlowRequest._transition](../../addons/supplyflow_office/models/purchase_request.py#L130) | Dictionary field tervalidasi -> super().write internal untuk status/audit setelah guard action. |
| [SupplyFlowRequest.create](../../addons/supplyflow_office/models/purchase_request.py#L135) | Daftar dictionary -> record baru bernomor otomatis, draft milik pengguna; saring audit dan default context. |
| [SupplyFlowRequest.write](../../addons/supplyflow_office/models/purchase_request.py#L168) | Dictionary perubahan -> simpan isi draft/catatan reviewer yang sah; tolak perubahan audit langsung. |
| [SupplyFlowRequest.unlink](../../addons/supplyflow_office/models/purchase_request.py#L182) | Recordset -> hapus hanya draft milik pengaju setelah lock dan pemeriksaan. |
| [SupplyFlowRequest.action_submit](../../addons/supplyflow_office/models/purchase_request.py#L187) | Draft berisi barang -> submitted, pelaku/waktu pengajuan, pesan chatter; kembalikan True. |
| [SupplyFlowRequest.action_approve](../../addons/supplyflow_office/models/purchase_request.py#L204) | Submitted dan reviewer independen -> approved, pelaku/waktu, chatter; kembalikan True. |
| [SupplyFlowRequest.action_reject](../../addons/supplyflow_office/models/purchase_request.py#L217) | Submitted dengan alasan -> rejected, pelaku/waktu, chatter; penolakan kosong ditolak. |
| [SupplyFlowRequest.action_reset_draft](../../addons/supplyflow_office/models/purchase_request.py#L232) | Rejected milik pengaju -> draft dan audit keputusan aktif kosong; riwayat chatter dipertahankan. |
| [SupplyFlowRequest.action_cancel](../../addons/supplyflow_office/models/purchase_request.py#L247) | Record dan pelaku sesuai status -> cancelled sebelum RFQ tercipta, dengan catatan pelaku. |
| [SupplyFlowRequest.action_create_rfq](../../addons/supplyflow_office/models/purchase_request.py#L261) | Satu approved dan izin Purchase -> buat/tautkan satu RFQ atau buka yang sudah ada; kembalikan window action. |
| [SupplyFlowRequest._rfq_action](../../addons/supplyflow_office/models/purchase_request.py#L307) | purchase_order_id -> dictionary pembuka form purchase.order; tidak mengubah stok. |
| [SupplyFlowRequestLine._compute_name](../../addons/supplyflow_office/models/purchase_request.py#L335) | Produk -> isi awal deskripsi dengan display_name produk. |
| [SupplyFlowRequestLine._compute_product_uom_id](../../addons/supplyflow_office/models/purchase_request.py#L340) | Produk -> isi satuan baris dari satuan produk. |
| [SupplyFlowRequestLine._compute_subtotal](../../addons/supplyflow_office/models/purchase_request.py#L345) | Jumlah dan harga estimasi -> isi subtotal hasil perkalian. |
| [SupplyFlowRequestLine._check_line_details](../../addons/supplyflow_office/models/purchase_request.py#L350) | Baris tersimpan -> validasi angka, presisi satuan, produk yang dapat dibeli/dilacak, dan perusahaan. |
| [SupplyFlowRequestLine._validate_numeric_input](../../addons/supplyflow_office/models/purchase_request.py#L366) | Jumlah, harga, satuan, mata uang -> pasangan angka float tervalidasi sebelum konversi field. |
| [SupplyFlowRequestLine.create](../../addons/supplyflow_office/models/purchase_request.py#L393) | Dictionary baris dan induk -> baris baru hanya pada draft sendiri; lindungi field turunan/default context. |
| [SupplyFlowRequestLine.write](../../addons/supplyflow_office/models/purchase_request.py#L424) | Dictionary perubahan -> edit baris draft sendiri setelah validasi kombinasi angka; larang pindah induk. |
| [SupplyFlowRequestLine.unlink](../../addons/supplyflow_office/models/purchase_request.py#L439) | Baris -> hapus hanya bila induk draft milik pengaju, setelah guard dan lock. |



### Receipt, kasus, retur, dan stock.move

Source: [addons/supplyflow_office/models/supplier_issue.py](../../addons/supplyflow_office/models/supplier_issue.py). Pembahasan: bab [04](04-receipt-masalah-dan-retur.md).

| Fungsi dan baris source | Masukan -> hasil/efek dan alasan |
| --- | --- |
| [SupplyflowIssue._check_member](../../addons/supplyflow_office/models/supplier_issue.py#L68) | Pengguna saat ini -> wajib peran SupplyFlow User sebelum menangani kasus. |
| [SupplyflowIssue._check_approver](../../addons/supplyflow_office/models/supplier_issue.py#L72) | Pengguna saat ini -> wajib User dan Approver untuk review kasus. |
| [SupplyflowIssue._check_draft_owner](../../addons/supplyflow_office/models/supplier_issue.py#L77) | Recordset -> wajib akses tulis, status draft, dan pelapor yang sama untuk edit isi. |
| [SupplyflowIssue._transition](../../addons/supplyflow_office/models/supplier_issue.py#L86) | Dictionary yang sudah diperiksa action -> tulis status/audit melalui implementasi induk. |
| [SupplyflowIssue._lock](../../addons/supplyflow_office/models/supplier_issue.py#L89) | Recordset -> periksa akses tulis, lock, invalidasi cache, dan periksa akses kembali. |
| [SupplyflowIssue._check_independent_reviewer](../../addons/supplyflow_office/models/supplier_issue.py#L95) | Kasus -> wajib Approver yang berbeda dari pelapor untuk mengambil keputusan. |
| [SupplyflowIssue.create](../../addons/supplyflow_office/models/supplier_issue.py#L101) | Daftar dictionary -> kasus draft bernomor dan pelapor saat ini; audit/link serta default berbahaya disaring. |
| [SupplyflowIssue.write](../../addons/supplyflow_office/models/supplier_issue.py#L128) | Perubahan isi/catatan -> simpan sesuai pemilik dan tahap review; field status/audit langsung ditolak. |
| [SupplyflowIssue.unlink](../../addons/supplyflow_office/models/supplier_issue.py#L146) | Kasus -> hapus hanya draft milik pelapor setelah lock. |
| [SupplyflowIssue._check_receipt](../../addons/supplyflow_office/models/supplier_issue.py#L152) | Kasus -> pastikan receipt incoming sudah Done, perusahaan cocok, resolver internal, dan deskripsi terisi. |
| [SupplyflowIssue._check_lines](../../addons/supplyflow_office/models/supplier_issue.py#L166) | Kasus dan returning flag -> periksa baris/sumber; shortage tidak boleh retur dan jumlah tidak melampaui sisa. |
| [SupplyflowIssue.action_submit](../../addons/supplyflow_office/models/supplier_issue.py#L184) | Satu draft sah -> submitted dengan pesan chatter; kembalikan True. |
| [SupplyflowIssue.action_approve](../../addons/supplyflow_office/models/supplier_issue.py#L194) | Satu submitted dan reviewer independen -> approved untuk retur, isi audit; barang belum bergerak. |
| [SupplyflowIssue.action_accept_resolution](../../addons/supplyflow_office/models/supplier_issue.py#L207) | Submitted dengan catatan reviewer -> accepted dan audit keputusan; tidak membuat retur stok. |
| [SupplyflowIssue.action_cancel](../../addons/supplyflow_office/models/supplier_issue.py#L222) | Kasus aktif dan pelaku berizin -> cancelled; kasus yang sudah selesai/bereturan tidak dibatalkan di sini. |
| [SupplyflowIssue._return_action](../../addons/supplyflow_office/models/supplier_issue.py#L238) | Tautan retur yang dapat dibaca -> dictionary pembuka form stock.picking. |
| [SupplyflowIssue.action_open_return](../../addons/supplyflow_office/models/supplier_issue.py#L246) | Satu kasus dan anggota berhak baca -> buka retur yang tertaut; tolak bila belum ada. |
| [SupplyflowIssue.action_create_return](../../addons/supplyflow_office/models/supplier_issue.py#L254) | Approved dan Approver -> lock sumber, periksa sisa, jalankan wizard, tautkan satu retur; kembalikan action. |
| [SupplyflowIssueLine._validated_quantity_input](../../addons/supplyflow_office/models/supplier_issue.py#L307) | Nilai jumlah -> float positif finite dalam kemampuan presisi; selain itu ValidationError. |
| [SupplyflowIssueLine._compute_returnable_qty](../../addons/supplyflow_office/models/supplier_issue.py#L321) | Sumber move dan retur terkait -> isi returnable_qty yang dihitung saat dibaca. |
| [SupplyflowIssueLine._remaining_returnable_quantity](../../addons/supplyflow_office/models/supplier_issue.py#L325) | Satu sumber move -> jumlah diterima dikurangi retur Done dan komitmen pending non-cancel, satuan disamakan. |
| [SupplyflowIssueLine._check_source_move](../../addons/supplyflow_office/models/supplier_issue.py#L342) | Baris -> wajib move Done dari receipt kasus, perusahaan cocok, dan jumlah positif sesuai presisi. |
| [SupplyflowIssueLine.create](../../addons/supplyflow_office/models/supplier_issue.py#L355) | Dictionary baris -> baris pada draft sendiri dengan jumlah tervalidasi dan field sumber terlindungi. |
| [SupplyflowIssueLine.write](../../addons/supplyflow_office/models/supplier_issue.py#L378) | Dictionary perubahan -> edit draft sendiri; larang pindah kasus dan pemalsuan detail sumber. |
| [SupplyflowIssueLine.unlink](../../addons/supplyflow_office/models/supplier_issue.py#L389) | Baris -> hapus hanya setelah induk dikunci dan kepemilikan draft diperiksa. |
| [StockMove.write](../../addons/supplyflow_office/models/supplier_issue.py#L400) | Dictionary perubahan move -> lanjutkan penulisan native kecuali revisi retur dikirim secara langsung. |
| [StockMove._supplyflow_advance_return_revision](../../addons/supplyflow_office/models/supplier_issue.py#L405) | Move sumber terkunci -> naikkan penghitung revisi internal agar transaksi bersaing dengan snapshot lama perlu retry. |



### RPC workspace

Source: [addons/supplyflow_office/models/workspace.py](../../addons/supplyflow_office/models/workspace.py). Pembahasan: bab [05](05-tampilan-workspace-dan-pdf.md).

| Fungsi dan baris source | Masukan -> hasil/efek dan alasan |
| --- | --- |
| [SupplyFlowWorkspace.get_overview](../../addons/supplyflow_office/models/workspace.py#L10) | Lingkungan pengguna/perusahaan -> dictionary hitungan pekerjaan dan delapan permintaan terbaru, mengikuti ACL/rule; tidak membuat data. |



### Manajemen server container

Source: [scripts/container/manage.py](../../scripts/container/manage.py). Pembahasan: bab [01](01-persiapan-dan-docker.md) / [07](07-operasi-dan-latihan.md).

| Fungsi dan baris source | Masukan -> hasil/efek dan alasan |
| --- | --- |
| [manage.run_shell](../../scripts/container/manage.py#L12) | Nama script container -> baca lalu jalankan lewat odoo shell yang menyediakan env; kegagalan subprocess diteruskan. |
| [manage.main](../../scripts/container/manage.py#L17) | Mode initialize/update/seed -> instal bila belum ada, update addon, atau jalankan seed; initialize juga konfigurasi satu kali. |



### Data latihan termasuk helper bersarang

Source: [scripts/container/training_data.py](../../scripts/container/training_data.py). Pembahasan: bab [07](07-operasi-dan-latihan.md).

| Fungsi dan baris source | Masukan -> hasil/efek dan alasan |
| --- | --- |
| [training_data.seed_training](../../scripts/container/training_data.py#L13) | Environment ORM -> data sintetis, indeks XML ID, penanda selesai, commit; bila sudah lengkap, pertahankan record dan password. |
| [training_data.seed_training.existing](../../scripts/container/training_data.py#L48) | Nama XML ID latihan dan model -> record yang masih ada; tolak bila ID menunjuk model berbeda. |
| [training_data.seed_training.bind](../../scripts/container/training_data.py#L56) | Nama ID dan satu record -> daftarkan/periksa XML ID, tambahkan ID ke indeks, kembalikan record. |
| [training_data.seed_training.ensure](../../scripts/container/training_data.py#L70) | Nama ID, model, callback pembuat -> gunakan record lama atau buat satu, lalu bind; menghindari duplikasi ID latihan. |
| [training_data.seed_training.create_user](../../scripts/container/training_data.py#L84) | Peran dari loop -> akun sintetis dengan grup/password peran; tolak login yang sudah dimiliki di luar dataset. |
| [training_data.seed_training.make_warehouse](../../scripts/container/training_data.py#L109) | Nama dan kode -> gudang latihan baru; tolak konflik kode yang sudah terpakai. |
| [training_data.seed_training.make_product](../../scripts/container/training_data.py#L122) | Nama, kode, biaya, harga -> produk stok yang bisa dibeli/dijual tanpa pajak latihan; tolak kode yang berbenturan. |
| [training_data.seed_training.create_request](../../scripts/container/training_data.py#L136) | Tujuan dan daftar produk/jumlah/biaya -> draft milik buyer pada pemasok/gudang latihan. |
| [training_data.seed_training.submit](../../scripts/container/training_data.py#L145) | Permintaan -> jalankan Submit sebagai buyer hanya jika masih draft; tidak mengembalikan record baru. |
| [training_data.seed_training.approve](../../scripts/container/training_data.py#L149) | Permintaan -> ajukan bila perlu dan setujui sebagai approver bila submitted. |
| [training_data.seed_training.create_issue](../../scripts/container/training_data.py#L195) | Deskripsi, alasan, jumlah, deadline -> draft kasus milik warehouse pada receipt latihan. |
| [training_data.seed_training.create_branch_transfer](../../scripts/container/training_data.py#L218) | Lingkungan gudang/produk latihan -> buat transfer internal sepuluh folder; validasi dilakukan kode pemanggil setelahnya. |



### Pembuatan arsip

Source: [scripts/container/backup.py](../../scripts/container/backup.py). Pembahasan: bab [07](07-operasi-dan-latihan.md).

| Fungsi dan baris source | Masukan -> hasil/efek dan alasan |
| --- | --- |
| [backup.addon_version](../../scripts/container/backup.py#L30) | Manifest lokal -> string versi addon yang cocok seri Odoo 19. |
| [backup.database_environment](../../scripts/container/backup.py#L38) | Konfigurasi tetap lokal -> environment PG termasuk password, tanpa mencetak secret; tolak target lain. |
| [backup.checked_run](../../scripts/container/backup.py#L56) | Daftar argumen, environment, capture flag -> CompletedProcess; kegagalan proses menjadi exception. |
| [backup.postgres_version](../../scripts/container/backup.py#L60) | Environment koneksi -> angka versi server, hanya menerima mayor PostgreSQL 17. |
| [backup.check_quiet_database](../../scripts/container/backup.py#L67) | Koneksi database -> tolak bila ada koneksi lain dengan user aplikasi yang sama; tidak menulis data. |
| [backup.filestore_files](../../scripts/container/backup.py#L74) | Lokasi filestore tetap -> daftar berkas biasa terurut; tolak symlink dan berkas khusus. |
| [backup.add_file](../../scripts/container/backup.py#L91) | ZIP, file sumber, nama anggota, kompresi -> tulis anggota sambil hitung path, ukuran, SHA-256; kembalikan metadata. |
| [backup.create_backup](../../scripts/container/backup.py#L104) | Path ZIP baru langsung di /tmp -> pg_dump + filestore + manifest; cetak ringkasan JSON dan bersihkan output gagal miliknya. |
| [backup.main](../../scripts/container/backup.py#L143) | Argumen --output -> jalankan backup; kembalikan kode 0 atau 1 untuk kegagalan yang ditangani. |



### Validasi dan pemulihan arsip

Source: [scripts/container/restore.py](../../scripts/container/restore.py). Pembahasan: bab [07](07-operasi-dan-latihan.md).

| Fungsi dan baris source | Masukan -> hasil/efek dan alasan |
| --- | --- |
| [restore.addon_version](../../scripts/container/restore.py#L36) | Manifest lokal -> string versi addon untuk dibandingkan dengan manifest backup. |
| [restore.database_environment](../../scripts/container/restore.py#L44) | Konfigurasi lokal -> environment PG untuk database supplyflow saja; password tetap privat. |
| [restore.validate_member](../../scripts/container/restore.py#L59) | ZipInfo -> tolak traversal, path asing, symlink, direktori, enkripsi, dan ukuran anggota di luar batas. |
| [restore.validate_archive](../../scripts/container/restore.py#L76) | Path ZIP dan versi addon -> manifest setelah pemeriksaan anggota, batas ukuran, nama, versi, hash, dan header dump; belum restore. |
| [restore.check_filestore_location](../../scripts/container/restore.py#L145) | Path filestore tetap -> tolak pengalihan symlink, target bukan direktori, atau berkas khusus. |
| [restore.remove_working_directory](../../scripts/container/restore.py#L157) | Path kerja restore -> hapus hanya staging/previous di bawah parent filestore yang diperiksa. |
| [restore.restore_archive](../../scripts/container/restore.py#L165) | ZIP dan manifest -> ekstraksi staging dengan hash ulang, pg_restore transaksi tunggal, lalu tukar filestore; cetak ringkasan. |
| [restore.main](../../scripts/container/restore.py#L219) | --archive dan satu mode wajib -> validasi saja atau restore pengganti; kembalikan kode 0/1 yang ditangani. |



## Semua fungsi PowerShell

Script startup, stop, test, seed, dan restore sebagian besar berupa langkah berurutan di tingkat file. Empat fungsi bernama berikut dipakai ulang atau memeriksa kepemilikan job backup. Pembahasan ada pada bab [01](01-persiapan-dan-docker.md) dan [07](07-operasi-dan-latihan.md).

| Fungsi dan source | Masukan -> hasil/efek dan alasan |
| --- | --- |
| [Backup.ps1::Assert-BackupContainerOwnership](../../scripts/Backup.ps1#L31) | ID container 64 heksadesimal -> cocokkan nama unik dan label project/service/oneoff; throw sebelum operasi pada container asing. |
| [Common.ps1::Invoke-Compose](../../scripts/Common.ps1#L4) | Argumen native Docker -> jalankan Compose pada root repo, teruskan output, throw bila exit code bukan nol; memakai @args agar -d/-v tidak dicuri binder. |
| [Common.ps1::New-LocalPassword](../../scripts/Common.ps1#L10) | Tanpa argumen -> string Base64 dari 30 byte acak kriptografis; tidak menulis atau mencetak password sendiri. |
| [Common.ps1::Initialize-LocalConfiguration](../../scripts/Common.ps1#L17) | Keadaan file dan volume -> buat secret baru hanya bila belum ada serta tulis konfigurasi/kredensial lokal; tolak secret hilang pada volume lama. |



## Semua method komponen Owl

Source: [static/src/workspace.js](../../addons/supplyflow_office/static/src/workspace.js). Nama class sama dengan class RPC Python, tetapi objek ini berjalan di browser. Pembahasan: bab [05](05-tampilan-workspace-dan-pdf.md).

| Method dan source | Masukan -> hasil/efek dan alasan |
| --- | --- |
| [SupplyFlowWorkspace.setup](../../addons/supplyflow_office/static/src/workspace.js#L11) | Pembuatan komponen -> ambil layanan ORM/action, siapkan state reaktif, jadwalkan load sebelum tampilan awal. |
| [SupplyFlowWorkspace.load](../../addons/supplyflow_office/static/src/workspace.js#L18) | Pemanggilan awal atau Retry/Refresh -> RPC get_overview, isi data atau pesan error, selalu akhiri loading. |
| [SupplyFlowWorkspace.openRequests](../../addons/supplyflow_office/static/src/workspace.js#L30) | pending boolean -> buka window action permintaan, opsional filter Awaiting Approval; kembalikan hasil doAction. |
| [SupplyFlowWorkspace.openIssues](../../addons/supplyflow_office/static/src/workspace.js#L36) | Nama filter atau kosong -> buka kasus dengan default filter yang sesuai metrik; kembalikan hasil doAction. |
| [SupplyFlowWorkspace.openRequest](../../addons/supplyflow_office/static/src/workspace.js#L42) | ID permintaan -> buka form satu supplyflow.request pada jendela saat ini. |



## Semua ekspor helper browser

Source: [tests/browser/helpers.js](../../tests/browser/helpers.js). Helper ini mendukung pengujian, bukan endpoint atau bagian server ERP. Pembahasan: bab [06](06-pengujian-dan-debugging.md).

| Ekspor dan source | Masukan -> hasil/efek dan alasan |
| --- | --- |
| [helpers.credentials](../../tests/browser/helpers.js#L4) | Peran (default admin) -> objek login/password dari secret lokal; jangan menampilkan hasilnya di log atau README. |
| [helpers.login](../../tests/browser/helpers.js#L10) | Page dan peran -> isi form login lalu tunggu navbar; menyiapkan sesi UI yang benar sebelum langkah tes. |
| [helpers.rpc](../../tests/browser/helpers.js#L19) | Page, model, method, args, kwargs -> panggil call_kw dengan sesi itu, kembalikan result atau throw bila RPC error. |
| [helpers.clickWorkflow](../../tests/browser/helpers.js#L28) | Page, model/method, nama tombol, opsi confirm -> klik dan tunggu respons call_button yang tepat; kembalikan action setelah form native siap bila relevan. |
| [helpers.authenticateApi](../../tests/browser/helpers.js#L56) | APIRequestContext dan peran -> autentikasi sesi HTTP untuk database supplyflow; tolak bila tidak mendapat uid. |
| [helpers.trainingIndex](../../tests/browser/helpers.js#L65) | Page admin -> ambil parameter indeks latihan melalui RPC dan kembalikan objek hasil JSON.parse. |
| [helpers.openAction](../../tests/browser/helpers.js#L69) | Page dan XML ID action -> navigasi ke /odoo/action-... dan tunggu action manager terlihat. |
| [helpers.openRecord](../../tests/browser/helpers.js#L74) | Page, XML ID action, ID record -> navigasi ke form record dan tunggu form terlihat. |



## Jika mencari tes atau fungsi bawaan Odoo

Method test dan fixture dikelompokkan per file pada peta pengujian di atas. Untuk membaca urutan `setUpClass()`, helper pembuat record, assertion, serta sembilan skenario browser, gunakan [bab 06](06-pengujian-dan-debugging.md). Angka 42 adalah jumlah method tes ORM, bukan jumlah seluruh fungsi aplikasi.

Nama seperti `purchase.order.create()`, `stock.picking.button_validate()`, dan `stock.return.picking.action_create_returns()` berasal dari modul native Odoo. Source-nya tidak disalin ke repo SupplyFlow. Indeks ini mencatat fungsi yang ditulis dalam proyek, sedangkan bab 03 dan 04 menunjukkan titik pemanggilan proses native tersebut.

Contoh pencarian di terminal dari root repo: `rg -n "def action_create_rfq|action_create_rfq" addons/supplyflow_office`. Hasilnya memperlihatkan definisi Python, tombol XML, dan tes yang memanggilnya. Dari situ, ikuti satu nama fungsi yang sama melalui tampilan, aturan bisnis, lalu pengujian.
