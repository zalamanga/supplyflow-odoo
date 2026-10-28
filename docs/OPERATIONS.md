# Menyalakan, mencadangkan, dan memulihkan SupplyFlow

Perintah berikut ditujukan untuk instalasi lokal SupplyFlow Office. Jalankan dari PowerShell pada folder repo. Semua perintah Compose memakai proyek `supplyflow-office`; script tidak menghentikan stack Docker proyek lain dan tidak menjalankan pembersihan volume global.

## Menyalakan aplikasi

```powershell
cd "D:\kerjaan\done push repo\supplyflow-odoo"
.\scripts\Start.ps1
```

Setup menarik image resmi Odoo/PostgreSQL, menyiapkan database `supplyflow`, memasang addon jika belum terpasang, lalu menjalankan aplikasi. Kode addon dan script memakai bind mount read-only dari repo; tidak ada langkah build image custom. Buka `http://localhost:8070`. Kredensial lokal ada di `.secrets/LOCAL-CREDENTIALS.txt`; berkas itu tidak boleh masuk Git.

Jika image yang dipatok sudah tersedia lokal, gunakan `.\scripts\Start.ps1 -SkipPull` untuk melewati pull. Opsi itu tidak mengunduh image yang belum ada. Unduhan dan ekstraksi pertama tetap membutuhkan waktu serta ruang disk.

Untuk memilih data latihan sintetis:

```powershell
.\scripts\Start.ps1 -WithTrainingData
```

Instalasi biasa tidak memilih data latihan. Data latihan dipakai untuk memeriksa alur kerja dan mengambil screenshot, bukan sebagai data pelanggan nyata. Pada instance yang sudah dipakai, baca perilaku script pemuatan data sebelum menggunakannya; opsi itu bukan perintah untuk mengosongkan database.

Untuk berhenti tanpa menghapus data:

```powershell
.\scripts\Stop.ps1
```

Database dan filestore tetap berada pada volume Docker. Lokasi volume mengikuti pengaturan disk Docker Desktop; lokasi kode di D: tidak dengan sendirinya mengubah lokasi disk Docker.

## Memperbarui kode addon

Sesudah mengubah model atau XML, hentikan Odoo, perbarui modul dari kode bind mount, lalu nyalakan kembali:

```powershell
docker compose stop odoo
docker compose run --rm -T odoo python3 /opt/supplyflow/manage.py update
docker compose up -d --wait odoo
```

Tidak diperlukan `docker compose build`. Perubahan schema/view masih memerlukan update addon; bind mount saja tidak menjalankan migrasi database. Simpan backup sebelum perubahan yang memengaruhi data.

## Membuat backup

Pastikan PostgreSQL proyek ini sedang berjalan dan tidak ada proses pemeliharaan SupplyFlow lain yang mengakses database.

```powershell
.\scripts\Backup.ps1
```

Hasil disimpan sebagai ZIP bertanggal pada `.backups/`. Folder tersebut diabaikan Git. Nama arsip juga memiliki suffix acak agar dua backup pada detik yang sama tidak saling menimpa. Script tidak menimpa arsip yang sudah ada.

Untuk memakai folder lain:

```powershell
.\scripts\Backup.ps1 -OutputDirectory "D:\Cadangan-SupplyFlow"
```

Script membaca status Odoo, menghentikan hanya layanan Odoo milik proyek ini, lalu membuat backup pada `/tmp` container satu kali dengan nama unik. Setelah proses selesai, `docker cp` menyalin arsip ke host memakai pengguna host. Tidak ada bind mount host yang harus dapat ditulis oleh UID aplikasi di container. Script memeriksa nama, ID, serta label project/service/one-off sebelum menghapus container backup miliknya sendiri.

PostgreSQL tetap berjalan. Jika Odoo sebelumnya berjalan, script menyalakannya kembali setelah backup, termasuk ketika proses backup gagal. Jika Odoo sebelumnya berhenti, script mempertahankannya tetap berhenti. Container sementara menyimpan dump dan arsip sebelum penyalinan; sediakan ruang disk Docker dan ruang folder tujuan untuk proses tersebut.

Jeda penulisan diperlukan agar dump database dan filestore saling cocok. Script Python juga menolak operasi jika masih terdeteksi koneksi aplikasi dengan role `supplyflow`; pemeriksaan itu bukan pengganti penghentian seluruh proses penulis yang dikelola pengguna.

### Isi arsip

| Anggota | Isi |
| --- | --- |
| `database.dump` | Dump custom PostgreSQL dari database `supplyflow` |
| `filestore/...` | Berkas lampiran Odoo pada filestore database yang sama |
| `manifest.json` | Format/versi backup, database, seri Odoo, versi addon, versi server PostgreSQL, waktu, ukuran dan SHA-256 setiap payload |

Password koneksi database, password master Odoo, file `.secrets`, serta konfigurasi host tidak ditambahkan ke arsip. Dump tetap memuat data bisnis dan hash password pengguna Odoo. Simpan arsip privat dan gunakan penyimpanan terenkripsi bila diperlukan. ZIP ini sendiri tidak dienkripsi atau ditandatangani.

SHA-256 mendeteksi ketidakcocokan payload dengan manifest. Pemeriksaan itu tidak membuktikan siapa pembuat arsip, karena seseorang dapat mengganti payload sekaligus manifest. Restore hanya arsip milik sendiri yang dipercaya. Dump PostgreSQL dapat menjalankan SQL saat dipulihkan.

Backup ini tidak menyimpan kode addon, image Docker, sesi login lokal, atau secret. Simpan versi kode yang sesuai dan cadangan konfigurasi privat secara terpisah. Pengguna perlu login kembali setelah restore.

## Restore ke instalasi lokal

Restore mengganti isi database dan filestore `supplyflow` pada proyek ini. Buat backup data saat ini terlebih dahulu. Jangan gunakan restore untuk mencoba membuka ZIP dari sumber yang tidak dipercaya.

```powershell
.\scripts\Backup.ps1
.\scripts\Restore.ps1 -Archive ".\.backups\supplyflow-YYYYMMDDTHHMMSSZ-SUFFIX.zip" -ReplaceDatabase
```

Ganti nama arsip dengan berkas yang benar-benar ada. Opsi `-ReplaceDatabase` wajib ditulis; tanpa opsi tersebut, script berhenti sebelum melakukan restore. Tidak ada pilihan nama database bebas yang dapat diarahkan ke database proyek lain.

Jika pindah komputer, siapkan repo dengan versi kode yang sesuai dan jalankan setup lokal terlebih dahulu. Secret koneksi baru boleh berbeda dari komputer asal karena restore memakai role/config lokal saat ini. Sesudah setup berhasil, jalankan restore dari arsip privat yang dipilih.

### Validasi sebelum penggantian

Restore pertama-tama memeriksa arsip pada container satu kali tanpa menghentikan layanan Odoo. Pemeriksa menolak path absolut, `..`, backslash, symlink, berkas khusus, anggota ZIP terenkripsi, nama duplikat, benturan path berkas/direktori, dan berkas di luar daftar yang diizinkan.

Manifest harus sesuai dengan format versi 1, database `supplyflow`, Odoo 19, versi addon lokal yang sama, dan PostgreSQL 17. Batas validasi adalah 100.000 anggota ZIP dan total 32 GiB sebelum kompresi. Setiap payload harus mempunyai ukuran dan SHA-256 yang sesuai. Dump harus mempunyai header format custom PostgreSQL.

Validasi yang berhasil belum mengubah database dan belum membuktikan dump bisa dipulihkan. Pemeriksaan sintaks dump dilakukan lagi oleh `pg_restore` sebelum operasi SQL. Perbedaan versi addon sengaja ditolak; gunakan checkout yang sesuai atau rencanakan migrasi secara terpisah.

### Urutan restore

1. Setelah validasi awal berhasil, script menghentikan hanya layanan Odoo proyek ini jika sedang berjalan.
2. Arsip divalidasi ulang. Berkas diekstrak ke staging filestore pada volume yang sama dan diperiksa hash-nya saat disalin.
3. Target koneksi diverifikasi sebagai database lokal `supplyflow` pada PostgreSQL 17 dengan role aplikasi `supplyflow`.
4. `pg_restore --clean --if-exists --no-owner --no-privileges --exit-on-error --single-transaction` memulihkan dump ke database yang sudah ada. Script tidak menghapus volume, membuat database bernama bebas, atau memakai akun superuser PostgreSQL.
5. Filestore lama dipindah sementara, filestore staging menggantikannya, lalu salinan filestore lama dibersihkan dari lokasi kerja yang sudah diperiksa.
6. Jika seluruh proses berhasil dan Odoo sebelumnya berjalan, script menyalakannya kembali. Bila sebelumnya berhenti, Odoo tetap berhenti.

PostgreSQL dan filesystem tidak berbagi satu transaksi atomik. SQL memakai satu transaksi untuk menghindari dump setengah masuk saat terjadi kesalahan SQL, tetapi kegagalan pergantian filestore setelah SQL selesai tetap memerlukan penanganan. Karena itu, restore yang gagal membiarkan Odoo berhenti.

Gunakan instalasi proyek dengan struktur database yang sesuai. `--clean` membersihkan objek yang tercantum pada dump; opsi itu bukan penghapus universal untuk objek tambahan yang tidak ada di arsip. Memulihkan ke instalasi yang telah dimodifikasi di luar kode proyek memerlukan pemeriksaan tersendiri.

## Password setelah restore

Password pengguna Odoo kembali mengikuti hash pada database ketika backup dibuat. Password tersebut dapat berbeda dari tulisan pada `.secrets/LOCAL-CREDENTIALS.txt` di komputer tujuan, terutama jika backup berasal dari komputer lain atau pengguna telah mengganti password di aplikasi.

Password role PostgreSQL dan password master Odoo tetap mengikuti secret/config lokal saat ini. Keduanya tidak diganti oleh restore. Jangan menimpa secret koneksi dengan password login Odoo. Setup yang menemukan instance sudah diinisialisasi tidak dimaksudkan untuk mereset password pengguna hasil restore.

## Jika restore gagal

Biarkan aplikasi berhenti dan simpan pesan kesalahannya. Jangan langsung menjalankan `Start.ps1` sampai keadaan database dan filestore dipahami.

| Titik kegagalan | Keadaan yang perlu diperiksa |
| --- | --- |
| Validasi awal | Data belum disentuh dan aplikasi belum dihentikan oleh script |
| Koneksi, staging, atau pemeriksaan dump | Belum ada operasi restore SQL; staging sementara dibersihkan bila proses dapat menyelesaikan penanganan kesalahan |
| Operasi SQL | PostgreSQL membatalkan transaksi restore yang gagal; periksa log sebelum melanjutkan |
| Setelah SQL selesai, saat mengganti filestore | Database dapat sudah berisi hasil restore, sedangkan filestore belum cocok; aplikasi tetap berhenti |
| Proses dimatikan paksa | Transaksi database dapat dibatalkan, tetapi direktori kerja sementara dapat tertinggal |

Direktori kerja memakai prefix `.supplyflow-restore-` dan `.supplyflow-previous-` langsung di `/var/lib/odoo/filestore`. Jangan menghapusnya sebelum menentukan salinan yang dibutuhkan. Pada kegagalan rename, script mencoba mengembalikan filestore lama bila target belum terpasang; itu tidak membatalkan database yang sudah berhasil dipulihkan.

Cara pemulihan yang dapat ditinjau adalah memperbaiki penyebabnya, lalu menjalankan kembali restore dari arsip backup terpercaya yang diketahui lengkap. Sebelum memulai ulang, cocokkan database dan lampirannya. Jangan menghapus volume PostgreSQL atau filestore untuk menghilangkan pesan error.

## Pemeriksaan hasil

Keberhasilan backup berarti arsip berhasil ditulis, bukan bahwa pemulihan sudah diuji. Lakukan latihan restore pada lingkungan proyek yang terpisah sebelum mengandalkan suatu cadangan. Jalankan instance terpisah dengan nama proyek, volume, dan port yang berbeda agar tidak menimpa instance kerja.

Sesudah restore, periksa login pengguna yang diketahui, perusahaan/gudang, satu permintaan beserta RFQ, satu kasus beserta retur, serta satu lampiran yang dapat dibuka. Cocokkan jumlah/relasi data yang penting. Hasil pemeriksaan proyek yang benar-benar sudah dijalankan harus dicatat pada dokumen verifikasi akhir.

## Batas penggunaan

Script ini ditujukan untuk pengembangan lokal dengan satu layanan Odoo. Pemakaian produksi memerlukan kebijakan retensi, penyimpanan di lokasi terpisah, enkripsi, pembatasan akses, pemantauan kegagalan, jadwal backup, uji pemulihan rutin, serta prosedur perubahan versi. Konfigurasi localhost bukan rancangan deployment publik.
