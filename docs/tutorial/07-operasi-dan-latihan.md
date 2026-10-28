# 07. Mengisi data latihan, menjaga data, dan mencoba satu alur lengkap

Bab ini memakai addon lengkap setelah bab 05. Tujuannya memahami mengapa data contoh, backup, dan restore mempunyai jalur sendiri, kemudian mencoba satu transaksi dari permintaan sampai stok benar-benar berpindah. Proses startup dasar sudah dibahas pada [bab 01](01-persiapan-dan-docker.md).

Untuk menulis ulang, gunakan terminal latihan yang sama dengan bab sebelumnya:

```powershell
cd 'D:\Latihan-Odoo\supplyflow-office' -ErrorAction Stop
$env:COMPOSE_PROJECT_NAME = 'supplyflow-belajar'
```

Nama proyek Compose memisahkan container dan volume latihan dari `supplyflow-office` utama, meskipun nama database di dalamnya sama-sama `supplyflow`. Port latihan masih 8070; proyek utama harus berhenti agar tidak berebut port. Pada terminal baru, set `COMPOSE_PROJECT_NAME` lagi sebelum menjalankan script. Semua contoh operasi di bab ini ditujukan ke folder latihan tersebut.

## 1. Mengapa seed dijalankan melalui shell Odoo?

Buka [manage.py](../../scripts/container/manage.py). Fungsi `run_shell(filename)` membaca script dari `/opt/supplyflow`, lalu mengirim isinya ke proses `odoo shell`. **Fungsi lengkap dari sumber**:

```python
def run_shell(filename):
    code = pathlib.Path("/opt/supplyflow", filename).read_text()
    subprocess.run(["odoo", "shell", "--config", CONFIG, "--no-http"], input=code, text=True, check=True)
```

Shell Odoo menyediakan `env`: environment berisi cursor database, pengguna, context, dan registry model yang sudah dimuat. Karena itu `env["supplyflow.request"]` mengenali model custom. Menjalankan `training_data.py` dengan Python Windows biasa tidak menyediakan environment tersebut.

`main()` pada `manage.py` memilih tiga mode. `initialize` memeriksa apakah addon sudah terpasang, memasangnya bila perlu, lalu menjalankan konfigurasi instance. `update` memperbarui addon dari source. `seed` memanggil `run_shell("training_data.py")`. Ketiganya tidak saling menggantikan: seed memerlukan model final yang sudah terpasang.

Pada [Load-TrainingData.ps1](../../scripts/Load-TrainingData.ps1), script menyiapkan konfigurasi, menyalakan PostgreSQL, membaca apakah Odoo sedang berjalan, lalu menghentikannya sebelum seed. Blok `finally` menyalakan Odoo lagi hanya jika sebelumnya berjalan. Jika sebelumnya berhenti, script seed tidak mengubahnya menjadi layanan yang terus berjalan.

Setelah pemasangan lengkap bab 05, pilih salah satu:

```powershell
cd 'D:\Latihan-Odoo\supplyflow-office' -ErrorAction Stop
$env:COMPOSE_PROJECT_NAME = 'supplyflow-belajar'
# Memuat latihan sambil menyalakan aplikasi yang lengkap.
.\scripts\Start.ps1 -WithTrainingData -SkipPull
```

Atau, jika instance lengkap sudah ada dan hanya ingin memuat dataset opsional:

```powershell
cd 'D:\Latihan-Odoo\supplyflow-office' -ErrorAction Stop
$env:COMPOSE_PROJECT_NAME = 'supplyflow-belajar'
.\scripts\Load-TrainingData.ps1
```

`-SkipPull` hanya dipakai jika image yang dipatok sudah tersedia lokal. Seed tidak dipilih oleh instalasi biasa. Jangan memanggilnya pada checkpoint addon minimal bab 02.

## 2. Ikuti isi `training_data.py`

Buka [file lengkap](../../scripts/container/training_data.py). `seed_training(environment)` menerima environment Odoo dan tidak mengembalikan dataset ke browser. Hasilnya berupa record database, external ID, parameter penanda, dan pesan status terminal.

Langkah pertama memeriksa `supplyflow.training_completed`. Jika nilainya `1`, fungsi selesai tanpa memuat ulang. Selanjutnya fungsi mensyaratkan `supplyflow.initialized`, mengunci perusahaan, dan memeriksa mata uang IDR. Tiga password latihan dibaca dari secret lokal, harus berbeda dan masing-masing sedikitnya 16 karakter. Password tidak ditulis tetap pada source.

Environment lalu memakai akun admin untuk persiapan dataset dengan context tanpa undangan/reset password melalui email. Record sintetis memakai penanda `[Training]` dan partner tidak diberi alamat email. Saat membuat dokumen custom, script berganti ke akun buyer atau warehouse; saat menyetujui, ia berganti ke approver. Jadi contoh tetap melalui metode bisnis pengguna yang berbeda.

### External ID dan tiga helper kecil

External ID adalah nama stabil yang menunjuk ID database, misalnya `supplyflow_training.product`. Angka ID database dapat berbeda antarinstalasi. Namespace `supplyflow_training` di sini dibuat lewat `ir.model.data`; ia bukan addon kedua yang harus dipasang.

| Helper di dalam `seed_training()` | Masukan | Hasil dan alasan |
| --- | --- | --- |
| `existing(name, model)` | Nama latihan dan model yang diharapkan | Mengambil record dari external ID; menolak jika ID menunjuk model lain |
| `bind(name, record)` | Nama stabil dan satu record | Menyimpan/memeriksa `ir.model.data`, mencatat ID pada dictionary `identifiers`, lalu mengembalikan record |
| `ensure(name, model, create)` | Identitas, model, fungsi pembuat | Menggunakan record yang ada atau memanggil fungsi pembuat, kemudian mengikat identitasnya |

**Fungsi lengkap kecil dari sumber**:

```python
    def ensure(name, model, create):
        record = existing(name, model)
        return bind(name, record or create())
```

`create` pada parameter adalah fungsi yang belum dijalankan. Contoh `lambda: make_product(...)` baru dipanggil jika record belum ditemukan. Helper pembuat produk, gudang, dan akun juga memeriksa tabrakan kode/login dengan data di luar dataset; ia berhenti daripada mengambil alih akun yang kebetulan bernama `buyer`.

Pada loop pembuat akun, `def create_user(role=role)` menangkap nilai peran untuk iterasi tersebut. Grup buyer mencakup Purchase dan Inventory; approver menambah kelompok Approver; warehouse mempunyai Inventory dan peran Sales untuk latihan penjualan. Hak native tersebut berbeda dari hak addon.

Idempotensi berarti menjalankan loader lagi tidak menggandakan dataset yang sudah selesai atau mereset password akun latihan. Loader ini bukan tombol reset: setelah penanda selesai ada, ia juga tidak mengembalikan transaksi yang telah kamu ubah atau memperbaiki record latihan yang dihapus. Jangan menghapus parameter penanda untuk memaksa reset instance yang sedang dipakai.

### Data dibuat lewat transaksi bisnis

Helper `make_warehouse()` membuat dua gudang satu langkah. `make_product()` membuat produk storable dengan kode latihan. `create_request()`, `submit()`, dan `approve()` membuat permintaan, mengajukan sebagai buyer, lalu menyetujui sebagai akun lain. Script mengonfirmasi PO native dan menyelesaikan receipt dengan jumlah aktual. Ia tidak mengisi saldo stok memakai angka langsung pada `stock.quant`.

**Potongan kode asli** saat menyelesaikan receipt:

```python
    if receipt.state != "done":
        for move in receipt.move_ids.filtered(lambda move: move.state not in ("done", "cancel")):
            move.write({"quantity": move.product_uom_qty, "picked": True})
        receipt.with_user(admin).button_validate()
```

Pada dataset baru, receipt awal berisi kertas 120, folder 80, dan pena 200. Transfer internal memindahkan 10 folder ke gudang cabang. Sales order kertas 10 dan pena 30 dikonfirmasi, tetapi delivery belum divalidasi. Pemesanan/reservasi tidak sama dengan pengurangan on-hand. Ada juga permintaan submitted/approved serta kasus masalah penerimaan submitted/approved untuk bahan penjelasan.

`create_issue()` menghubungkan kasus ke move kertas pada receipt selesai. `create_branch_transfer()` memakai transfer native antargudang. Pada akhir proses, indeks ID disimpan di `supplyflow.training_json`, penanda selesai ditulis, lalu `environment.cr.commit()` menyimpan transaksi. Blok paling bawah memanggil `env.cr.rollback()` jika seed melempar exception. Nama nomor dokumen tidak perlu berurutan tanpa celah setelah percobaan yang gagal.

## 3. Buat satu transaksi baru dari awal sampai selesai

Gunakan label unik, misalnya `[Latihan] Pembelian kertas sesi 1`, agar tidak bergantung pada keadaan fixture lama. Pada proyek utama, sebagian data latihan mungkin sudah berubah saat pengujian atau demonstrasi. Jalankan transaksi baru ini hanya pada instance latihan.

1. Login `warehouse`. Catat on-hand kertas di Main warehouse sebagai nilai **B**. Periksa juga gudang tujuan yang dipakai, supaya stok cabang tidak tercampur dalam perbandingan.
2. Login `buyer`. Buka **SupplyFlow Office > Purchase requests > New**. Pilih `[Training] Paper supplier`, Main warehouse, tanggal kebutuhan, dan purpose unik tadi. Tambahkan A4 paper sebanyak 5 dengan estimasi 45.000. Simpan dan pilih **Submit for Approval**.
3. Login `approver`. Buka permintaan itu, tinjau datanya, lalu **Approve**. Buyer tidak menyetujui permintaannya sendiri. Pilih **Create RFQ**, catat nomor RFQ, lalu buka ulang untuk membuktikan tautannya menuju dokumen yang sama.
4. Sebagai petugas Purchase yang berwenang, periksa vendor, gudang incoming, harga, dan pajak RFQ. Konfirmasi PO. Jika aturan native meminta approval PO tambahan, gunakan pengguna berwenang; persetujuan SupplyFlow tidak melewati aturan Purchase.
5. Login `warehouse`, buka receipt dari PO, masukkan jumlah aktual 5 dan validasi. Untuk skenario penerimaan penuh ini, tidak ada sisa yang perlu dijadikan backorder. On-hand Main warehouse menjadi **B + 5** jika tidak ada transaksi lain.
6. Masih sebagai `warehouse`, buat **Supplier issues** untuk receipt tersebut: alasan damaged goods, uraian, resolver approver, tanggal, move kertas, jumlah terdampak 1. Simpan lalu **Submit for review**.
7. Login `approver`, **Approve supplier return**, kemudian **Create return transfer**. Pastikan jumlah rencana 1 dan receipt sumber benar. On-hand masih **B + 5** sebelum validasi retur.
8. Login `warehouse`, buka retur tertaut, periksa jumlah aktual 1 lalu validasi. On-hand menjadi **B + 4**. Kasus menyimpan `state=return_created`; status transfer terkait menjadi `done`.
9. Dengan akun Sales yang berwenang, buat quotation pelanggan `[Training] Office customer`, gudang Main, kertas 2, dan harga yang ditinjau. Konfirmasi order. Pada akun latihan warehouse, hak Sales tersedia untuk latihan ini.
10. Buka delivery dari sales order, periksa ketersediaan serta jumlah 2, lalu validasi. On-hand menjadi **B + 2**: penerimaan 5, retur 1, delivery 2. Nomor permintaan, PO, receipt, kasus, retur, SO, dan delivery memberi jejak dokumen untuk menjelaskan perubahan itu.

Catat hasil aktual, bukan hanya menyalin rumus. Bila stok berbeda, periksa lokasi, status `done`, transaksi lain, dan satuan. Screenshot hasil latihan adalah gambar aplikasi nyata; jangan menampilkan password atau informasi pribadi pada gambar.

## 4. Mengapa backup berisi database dan filestore?

PostgreSQL menyimpan record seperti permintaan, baris, picking, pengguna, dan metadata lampiran. Filestore menyimpan isi berkas lampiran. Database yang dipulihkan tanpa filestore yang cocok dapat menampilkan metadata lampiran sementara isi berkasnya hilang.

[Backup.ps1](../../scripts/Backup.ps1) menerima `-OutputDirectory` opsional; default hasilnya folder `.backups` pada root repo. Nama ZIP memakai waktu UTC dan suffix acak. PostgreSQL harus sudah berjalan. Script membaca apakah Odoo sedang berjalan, menghentikan penulisan aplikasi, lalu membuat container satu kali untuk menjalankan [backup.py](../../scripts/container/backup.py).

```powershell
cd 'D:\Latihan-Odoo\supplyflow-office' -ErrorAction Stop
$env:COMPOSE_PROJECT_NAME = 'supplyflow-belajar'
.\scripts\Backup.ps1
```

`backup.py` melakukan pemeriksaan koneksi/database/versi, memeriksa tidak ada koneksi aplikasi lain dengan role yang sama, menginventarisasi filestore, menjalankan `pg_dump`, lalu menulis arsip. `add_file()` membaca berkas per chunk, menulisnya ke ZIP, dan menghitung ukuran serta SHA-256. Output baru dibuka memakai mode `xb`, sehingga berkas yang sudah ada tidak ditimpa.

| Isi ZIP | Kegunaan |
| --- | --- |
| `database.dump` | Dump custom PostgreSQL 17, termasuk data bisnis dan hash password pengguna |
| `filestore/...` | Isi lampiran dari database yang sama |
| `manifest.json` | Format/version, nama database, seri Odoo, versi addon, versi PostgreSQL, waktu, serta path/ukuran/SHA-256 payload |

Arsip dibuat di `/tmp` container lalu disalin ke Windows dengan `docker cp`. Script PowerShell menunggu exit code pekerjaan dan memeriksa kepemilikan sebelum membersihkan container sementara: ID lengkap, nama acak, label proyek Compose, service `odoo`, dan `oneoff=True` harus cocok. Pembersihan ini tidak mencari lalu menghapus sembarang container Odoo.

Blok `finally` mencoba menyalakan Odoo kembali jika sebelumnya berjalan, termasuk ketika backup gagal. Jika sebelumnya berhenti, tetap berhenti. Menulis backup yang berhasil belum membuktikan restore berhasil; uji pemulihan merupakan pemeriksaan lain.

Backup tidak memasukkan source, image, `.secrets`, atau konfigurasi host. Simpan versi source yang sesuai dan secret secara privat terpisah. ZIP berisi data sensitif, tidak dienkripsi, dan harus tetap di luar Git. Jeda penulisan diperlukan untuk konsistensi database/filestore; pemeriksaan koneksi bukan pengganti menghentikan seluruh proses penulis tambahan yang kamu jalankan sendiri.

## 5. Baca restore sebelum menjalankannya

**Restore mengganti database dan filestore. Bagian ini menjelaskan prosedur; jangan mencobanya pada proyek utama atau menjalankannya otomatis untuk melanjutkan tutorial.** Buat backup keadaan saat ini dan siapkan instance latihan terpisah yang siap diganti. Pastikan versi addon sama dengan arsip.

[Restore.ps1](../../scripts/Restore.ps1) mewajibkan `-Archive` dan switch `-ReplaceDatabase`. Tanpa switch penggantian, script berhenti sebelum restore. Berikut **contoh sintaks**. `supplyflow-WAKTU-SUFFIX.zip` adalah placeholder yang tidak dibuat tutorial; ganti dengan arsip yang benar-benar ada, dibuat dari instance latihan milikmu sendiri, dan dipercaya. Ini bukan perintah yang perlu dijalankan untuk menyelesaikan latihan UI:

```powershell
cd 'D:\Latihan-Odoo\supplyflow-office' -ErrorAction Stop
$env:COMPOSE_PROJECT_NAME = 'supplyflow-belajar'
$labRoot = (Resolve-Path -LiteralPath 'D:\Latihan-Odoo\supplyflow-office' -ErrorAction Stop).ProviderPath
if ((Get-Location).ProviderPath -ne $labRoot -or $env:COMPOSE_PROJECT_NAME -ne 'supplyflow-belajar') {
    throw 'Folder aktif dan nama proyek harus menunjuk instance latihan.'
}
$archivePath = '.\.backups\supplyflow-WAKTU-SUFFIX.zip'
if (-not (Test-Path -LiteralPath $archivePath -PathType Leaf)) {
    throw 'Ganti placeholder dengan berkas backup latihan milik sendiri yang dipercaya.'
}
.\scripts\Restore.ps1 -Archive $archivePath -ReplaceDatabase
```

Urutan [restore.py](../../scripts/container/restore.py) membantu memahami titik kegagalannya:

1. `validate_archive(path, expected_addon_version)` memeriksa arsip lebih dahulu melalui mode `--validate-only`, sebelum aplikasi dihentikan. Path traversal, symlink, berkas khusus, ZIP terenkripsi, nama duplikat, benturan path, format/versi salah, dan payload yang tidak cocok ditolak. Batasnya 100.000 anggota, 32 GiB total sebelum kompresi, serta manifest 16 MiB.
2. Sesudah validasi awal, PowerShell menghentikan Odoo bila sedang berjalan. Proses restore memvalidasi arsip kembali, lalu memeriksa target tetap database `supplyflow`, role/host lokal yang sesuai, PostgreSQL 17, dan tidak ada koneksi aplikasi aktif.
3. `restore_archive()` mengekstrak dump ke lokasi sementara dan filestore ke direktori staging pada volume yang sama. Ukuran dan hash diperiksa saat ekstraksi, sebelum SQL restore. `pg_restore --list` memeriksa struktur dump.
4. `pg_restore` memakai `--clean --if-exists --no-owner --no-privileges --exit-on-error --single-transaction`. Kesalahan SQL membatalkan transaksi restore; flag `--clean` hanya membersihkan objek yang tercantum pada dump, bukan semua objek tambahan sembarang instalasi.
5. Setelah SQL berhasil, filestore lama di-rename ke direktori sementara, staging menggantikannya, lalu salinan lama dibersihkan. `remove_working_directory()` hanya menerima direktori kerja dengan prefix yang diizinkan langsung di parent filestore, tanpa symlink.
6. Odoo dinyalakan kembali hanya jika restore seluruhnya berhasil dan Odoo sebelumnya berjalan. Jika sebelumnya berhenti, tetap berhenti. Jika restore gagal setelah dihentikan, aplikasi dibiarkan berhenti untuk pemeriksaan.

SHA-256 membuktikan payload sesuai dengan manifest yang dibaca, bukan membuktikan identitas pembuat. Seseorang dapat mengganti payload dan manifest bersamaan. Gunakan hanya arsip sendiri yang dipercaya; dump database dapat menjalankan SQL saat dipulihkan.

PostgreSQL dan filesystem tidak memiliki satu transaksi bersama. SQL dapat sudah berhasil ketika pergantian filestore gagal. Kode mencoba mengembalikan filestore lama jika rename pengganti belum terjadi, tetapi ini tidak membatalkan SQL yang sudah selesai. Pada kegagalan, simpan log dan direktori kerja yang masih diperlukan; jangan langsung menyalakan Odoo atau menghapus volume. [OPERATIONS.md](../OPERATIONS.md#jika-restore-gagal) menjelaskan keadaan per titik kegagalan.

Setelah pemulihan latihan, periksa satu permintaan/RFQ, satu kasus/retur, stok penting, dan satu lampiran yang dapat dibuka. Login memakai password pengguna pada saat backup, yang mungkin berbeda dari teks kredensial lokal sekarang. Password role PostgreSQL dan master Odoo tetap mengikuti secret host saat ini.

## 6. Mengapa sisa tes dibersihkan dengan guard?

[Test.ps1](../../scripts/Test.ps1) membuat nama database baru `supplyflow_test_` diikuti GUID 32 karakter. Script menghentikan Odoo, menjalankan tes pada database tersebut, lalu menghapus database dan filestore tes pada blok `finally`, kecuali `-KeepDatabase` dipilih. Ia tidak otomatis menyalakan aplikasi kembali; setelah tes, nyalakan lewat `Start.ps1` saat ingin memakai UI.

[clean_test_filestore.py](../../scripts/container/clean_test_filestore.py) menolak nama selain pola tersebut. **Potongan asli**, bukan isi lengkap file:

```python
if not re.fullmatch(r"supplyflow_test_[0-9a-f]{32}", name):
    raise SystemExit("Only a generated SupplyFlow test database filestore may be removed.")
```

Selanjutnya script memastikan parent tepat `/var/lib/odoo/filestore`, target bukan symlink, dan resolved target tetap langsung di parent itu sebelum `shutil.rmtree()`. Guard ini melindungi penghapusan hasil tes dari path salah. Jangan mengganti pemeriksaan tersebut dengan penghapusan seluruh volume atau parent filestore.

## 7. Latihan kecil: tambah referensi internal permintaan

Kerjakan hanya pada source latihan. Tambahan ini **belum ada pada kode final referensi**; tujuannya mempraktikkan hubungan model, guard, view, update, dan tes. Tambah satu field opsional, tanpa mengubah status atau perhitungan stok.

Di kelas `SupplyFlowRequest` pada [purchase_request.py](../../addons/supplyflow_office/models/purchase_request.py), setelah `purpose`, tambahkan baris latihan baru:

```python
    internal_reference = fields.Char(string="Internal reference", tracking=True)
```

Masukkan `"internal_reference"` ke `_DRAFT_FIELDS` pada kelas yang sama, tanpa menghapus anggota set yang sudah ada. Ini langkah server yang penting: `write()` menggunakan set itu untuk mewajibkan draft milik pengaju. Readonly pada form saja tidak membekukan field melalui RPC.

Di [purchase_request_views.xml](../../addons/supplyflow_office/views/purchase_request_views.xml), tambahkan elemen latihan berikut di dalam group form dekat `requested_date`:

```xml
<field name="internal_reference" readonly="state != 'draft' or requester_id != uid"/>
```

Di kelas `TestPurchaseRequest` pada [test_purchase_request.py](../../addons/supplyflow_office/tests/test_purchase_request.py), tambahkan metode latihan berikut. Fixture `_request()` dan `UserError` sudah tersedia pada file tersebut:

```python
    def test_internal_reference_freezes_after_submission(self):
        request = self._request(internal_reference="LATIHAN-001")
        request.write({"internal_reference": "LATIHAN-002"})
        self.assertEqual(request.internal_reference, "LATIHAN-002")
        request.action_submit()
        with self.assertRaises(UserError):
            request.write({"internal_reference": "DIUBAH-SETELAH-AJU"})
```

Ikuti prosedur update addon pada [bab 05](05-tampilan-workspace-dan-pdf.md), lalu tes seperti [bab 06](06-pengujian-dan-debugging.md). Periksa field tersimpan pada draft dan perubahan langsung ditolak setelah submitted. Field tambahan ini tidak otomatis masuk ke PDF, RFQ, atau workspace; bagian itu sengaja di luar latihan kecil ini.

Menambahkan method tes latihan ini membuat jumlah tes ORM menjadi 43 pada salinanmu. Angka 42 pada catatan verifikasi adalah baseline proyek referensi sebelum latihan tambahan.

## 8. Simpan pekerjaan dan hentikan layanan

Simpan source dan catatan hasil, lalu hentikan instance latihan:

```powershell
cd 'D:\Latihan-Odoo\supplyflow-office' -ErrorAction Stop
$env:COMPOSE_PROJECT_NAME = 'supplyflow-belajar'
.\scripts\Stop.ps1
```

Container berhenti, volume database/filestore tetap ada. Tidak perlu menghapus volume setiap selesai belajar. Jika source latihan sudah memakai Git, tinjau `git status --short` serta `git diff` sebelum commit. Pilih file model, view, dan tes yang berubah; periksa isi staged diff sebelum push.

Jangan push `.secrets`, `.runtime`, `.backups`, `.local`, database dump, screenshot yang menampilkan password, CV/dokumen pribadi, `node_modules`, atau hasil tes. [.gitignore](../../.gitignore) menangani folder generated proyek, tetapi tetap periksa file yang akan dipublikasikan. Git menyimpan source; backup menyimpan keadaan data. Mengunggah repo tidak mencadangkan transaksi ERP.

## Periksa pemahaman

| Pertanyaan | Jawaban yang perlu dapat kamu jelaskan |
| --- | --- |
| Mengapa seed memakai `odoo shell`? | Agar script mendapat `env`, registry model, context pengguna, dan cursor transaksi Odoo |
| Apa yang terjadi jika seed dipanggil lagi setelah selesai? | Penanda selesai membuatnya berhenti; data dan password latihan dipertahankan, bukan direset |
| Mengapa stock quant tidak diisi langsung oleh seed? | Receipt/transfer native harus mencatat hubungan dokumen dan perpindahan stok melalui workflow |
| Mengapa backup menyimpan filestore? | Metadata lampiran di database memerlukan berkas fisik yang sesuai |
| Mengapa hash valid belum membuat arsip terpercaya? | Hash hanya cocok dengan manifest; pembuat arsip yang tidak dipercaya dapat mengganti keduanya |
| Apa arti `--single-transaction` pada restore? | SQL restore menjadi satu transaksi, tetapi pergantian filestore sesudahnya tetap operasi filesystem terpisah |
| Mengapa field latihan harus masuk `_DRAFT_FIELDS`? | Supaya aturan server membekukan perubahan, termasuk pemanggilan langsung di luar form |
| Apakah commit source menyimpan stok latihan? | Tidak; stok berada pada database, dan cadangan data memakai arsip database plus filestore |

Gunakan [indeks file dan fungsi](08-indeks-file-dan-fungsi.md) ketika ingin mencari kembali helper yang menjalankan salah satu langkah tersebut.
