# 1. Persiapan dan Docker

Hasil bab ini: kamu dapat menunjukkan tempat browser, server Odoo, database, addon, dan lampiran berjalan. Kamu juga mengetahui fungsi file yang menyalakan proyek.

## 1.1 Yang perlu dipasang

Gunakan Docker Desktop dengan Linux containers dan PowerShell. Git diperlukan untuk mengambil source dari GitHub jika proyek belum ada. Node.js hanya diperlukan untuk tes Playwright; aplikasi ERP tidak memakai server Node terpisah. Python dan PostgreSQL untuk server ERP sudah tersedia di image container, sehingga tidak perlu memasangnya lagi di Windows untuk menjalankan aplikasi.

Periksa dari PowerShell:

```powershell
docker version
docker compose version
```

`docker version` harus dapat menampilkan bagian Client dan Server. Jika Server tidak tersedia, jalankan Docker Desktop terlebih dahulu.

Untuk membaca proyek yang sudah jadi, gunakan:

```powershell
cd 'D:\kerjaan\done push repo\supplyflow-odoo'
Remove-Item Env:COMPOSE_PROJECT_NAME -ErrorAction SilentlyContinue
.\scripts\Start.ps1 -WithTrainingData -SkipPull
```

`-SkipPull` sesuai untuk komputer ini karena image proyek sudah pernah ditarik. Pada komputer baru, hilangkan opsi tersebut. Buka `http://localhost:8070`; kredensial ada di `.secrets/LOCAL-CREDENTIALS.txt`. Hentikan dengan `Stop.ps1` setelah selesai supaya layanan tidak terus memakai RAM.

## 1.2 Arti image, container, dan volume

| Istilah | Pada proyek ini |
| --- | --- |
| Image | Paket Odoo 19 atau PostgreSQL 17 yang digunakan untuk membuat container |
| Container | Proses terisolasi yang menjalankan Odoo atau PostgreSQL dari image |
| Addon | Folder Python/XML/JavaScript `supplyflow_office` yang dibaca Odoo |
| Bind mount | Folder source di Windows terlihat di container; `:ro` berarti hanya dibaca dari container |
| Named volume | Penyimpanan Docker untuk database dan filestore, terpisah dari umur container |
| Secret | Berkas password yang dipasang ke `/run/secrets/...` |
| Filestore | Berkas lampiran Odoo; tabel database menyimpan metadata dan hubungannya |

Mengganti container tidak sama dengan menghapus volume. Menyalin source repo juga tidak menyalin isi database dan filestore. Karena itu, proyek mempunyai backup yang mengambil keduanya.

## 1.3 Membaca `compose.yaml`

Buka [file lengkap](../../compose.yaml). Dua service bernama `postgres` dan `odoo` terhubung melalui jaringan internal Compose.

Cuplikan asli service database:

```yaml
  postgres:
    image: postgres:17-alpine
    environment:
      POSTGRES_DB: supplyflow
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
    secrets:
      - postgres_password
      - db_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/container/init-database.sh:/docker-entrypoint-initdb.d/10-supplyflow.sh:ro
```

`POSTGRES_DB` menentukan database awal. Password administrator PostgreSQL dibaca dari berkas, bukan ditulis di YAML. `init-database.sh` dimuat pada inisialisasi volume PostgreSQL baru. Ia tidak dijalankan ulang setiap restart.

Cuplikan asli service Odoo, bukan isi seluruh file:

```yaml
    environment:
      HOST: postgres
      USER: supplyflow
      PASSWORD_FILE: /run/secrets/db_password
      ODOO_RC: /run/odoo/odoo.conf
```

`HOST: postgres` berarti nama service di jaringan Docker. Jika Odoo memakai `localhost` sebagai host database di dalam containernya sendiri, ia akan mencari PostgreSQL di container Odoo, padahal database berada di container lain.

Bagian penyimpanan dan port:

```yaml
    volumes:
      - odoo_data:/var/lib/odoo
      - ./.runtime/odoo.conf:/run/odoo/odoo.conf:ro
      - ./addons:/mnt/extra-addons:ro
      - ./scripts/container:/opt/supplyflow:ro
    ports:
      - "127.0.0.1:8070:8069"
```

Browser Windows mengakses port `8070`; server Odoo di container mendengarkan `8069`. Binding `127.0.0.1` membatasi akses ke komputer ini. PostgreSQL tidak mempunyai mapping port host pada Compose proyek.

Healthcheck PostgreSQL memakai TCP `127.0.0.1`, sehingga tidak menganggap server socket sementara saat bootstrap sebagai server final yang sudah siap. `depends_on` menunggu status sehat sebelum memulai service yang bergantung padanya. Healthcheck Odoo memanggil `/web/health`; keberhasilan endpoint ini bukan pengganti tes alur bisnis.

Image Odoo di source dipatok dengan tag tanggal serta digest. Proyek memakai image resmi secara langsung; tidak ada Dockerfile custom. Batas memori Odoo pada Compose adalah 1536 MiB, sedangkan PostgreSQL dan aplikasi Windows tetap membutuhkan memori sendiri.

## 1.4 Siapa membuat password dan konfigurasi?

Buka [Common.ps1](../../scripts/Common.ps1). Tiga fungsi utamanya:

| Fungsi | Masukan dan hasil |
| --- | --- |
| `Invoke-Compose` | Menerima argumen CLI, menjalankan Compose pada root proyek, dan menghentikan script bila exit code gagal |
| `New-LocalPassword` | Membuat 30 byte acak kriptografis, lalu mengembalikannya sebagai teks Base64 |
| `Initialize-LocalConfiguration` | Memeriksa volume lama, mempertahankan secret yang ada, membuat secret baru jika diperlukan, lalu menulis config dan petunjuk login lokal |

Cuplikan fungsi lengkap asli di `Common.ps1`:

```powershell
function Invoke-Compose {
    # Keep native flags such as -d and -v out of PowerShell common-parameter binding.
    & docker compose --project-directory $script:ProjectRoot @args
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose failed (exit $LASTEXITCODE)." }
}
```

`$PSScriptRoot` menunjuk folder script. Root proyek dihitung dari situ agar perintah tidak bergantung pada folder terminal yang kebetulan sedang aktif. `@args` meneruskan argumen, misalnya `up -d --wait postgres`. Fungsi ini sengaja bukan advanced function agar flag native seperti `-d` tidak tertangkap sebagai common parameter PowerShell.

Folder yang dihasilkan:

```text
.secrets/
  postgres_password          administrator PostgreSQL
  db_password                role koneksi aplikasi supplyflow
  admin_password             login admin Odoo saat setup pertama
  master_password            password pengelolaan database Odoo
  training_credentials.json  password tiap akun latihan
  LOCAL-CREDENTIALS.txt       petunjuk login lokal
.runtime/
  odoo.conf                  konfigurasi Odoo untuk instance ini
```

Password database, password admin aplikasi, dan master password memiliki pekerjaan berbeda. Mengubah isi berkas secret tidak otomatis mengubah password yang sudah tersimpan pada database atau akun Odoo.

Jika volume data sudah ada tetapi secret aslinya hilang, script berhenti. Membuat password baru diam-diam justru dapat memutus hubungan dengan database lama. `.gitignore` mengecualikan folder-foder tersebut dari Git.

## 1.5 Role database dan startup

[init-database.sh](../../scripts/container/init-database.sh) membuat role aplikasi:

```sql
CREATE ROLE supplyflow LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD :'app_password';
ALTER DATABASE supplyflow OWNER TO supplyflow;
GRANT ALL ON SCHEMA public TO supplyflow;
```

Ini cuplikan SQL dari script shell. `:'app_password'` adalah substitusi variabel `psql` dengan quoting literal, bukan password yang ditulis manual di source. Role aplikasi mempunyai database lokal tetapi tidak diberi hak superuser, membuat role, atau membuat database lain.

[Start.ps1](../../scripts/Start.ps1) menjalankan urutan berikut:

1. Memanggil `Initialize-LocalConfiguration`.
2. Menarik image kecuali `-SkipPull` dipilih.
3. Menyalakan PostgreSQL dan menunggu healthcheck.
4. Menghentikan Odoo proyek ini sebelum proses instalasi satu kali.
5. Memanggil `manage.py initialize` untuk memasang addon bila belum terpasang.
6. Memanggil seed hanya bila `-WithTrainingData` diberikan.
7. Menyalakan service Odoo dan menunggu sehat.

[manage.py](../../scripts/container/manage.py) adalah pengatur proses, bukan server HTTP baru. `main()` membaca mode `initialize`, `update`, atau `seed`. Mode initialize memeriksa tabel modul melalui koneksi PostgreSQL, kemudian memanggil Odoo CLI jika addon belum installed. `run_shell(filename)` membaca script container dan mengirimkannya ke `odoo shell` melalui stdin.

[configure_instance.py](../../scripts/container/configure_instance.py) berjalan pada shell itu, sehingga variabel `env` sudah tersedia. Pada setup pertama, ia membaca secret admin, memberi kelompok Approver, menetapkan mata uang IDR dan URL lokal, lalu mencatat `supplyflow.initialized`. Pada startup berikutnya, penanda itu mencegah password dan data bisnis ditulis ulang.

`Stop.ps1` hanya menghentikan dua service proyek ini. Ia tidak menjalankan penghapusan volume.

## 1.6 Folder kosong untuk jalur membangun ulang

Lewati bagian ini jika hanya membaca proyek utama. Untuk praktik dari folder kosong, buka satu terminal PowerShell khusus latihan dan jalankan:

```powershell
$referensi = 'D:\kerjaan\done push repo\supplyflow-odoo'
$latihan = 'D:\Latihan-Odoo\supplyflow-office'
if (Test-Path -LiteralPath $latihan) {
    throw 'Folder latihan sudah ada. Gunakan folder kosong lain; jangan timpa pekerjaan lama.'
}
New-Item -ItemType Directory -Path $latihan | Out-Null
Copy-Item -LiteralPath "$referensi\compose.yaml" -Destination "$latihan\compose.yaml"
Copy-Item -LiteralPath "$referensi\compose.test.yaml" -Destination "$latihan\compose.test.yaml"
Copy-Item -LiteralPath "$referensi\.gitignore" -Destination "$latihan\.gitignore"
Copy-Item -LiteralPath "$referensi\.gitattributes" -Destination "$latihan\.gitattributes"
New-Item -ItemType Directory -Path "$latihan\scripts\container" -Force | Out-Null
foreach ($sourceFile in (Get-ChildItem -LiteralPath "$referensi\scripts" -Filter '*.ps1' -File)) {
    Copy-Item -LiteralPath $sourceFile.FullName -Destination "$latihan\scripts"
}
foreach ($sourceFile in (Get-ChildItem -LiteralPath "$referensi\scripts\container" -File)) {
    if ($sourceFile.Extension -in @('.py', '.sh')) {
        Copy-Item -LiteralPath $sourceFile.FullName -Destination "$latihan\scripts\container"
    }
}
Set-Location -LiteralPath $latihan
$env:COMPOSE_PROJECT_NAME = 'supplyflow-belajar'
```

Yang disalin hanya infrastruktur source agar kamu dapat berfokus membuat addon. Pemilihan file tidak menyalin `__pycache__`. Tidak ada data, secret, atau dependency terpasang yang disalin. Seluruh helper tersebut dijelaskan pada bab ini dan bab 7; kamu dapat membuka file lengkapnya jika ingin mengetik ulang.

`COMPOSE_PROJECT_NAME` wajib tetap bernilai `supplyflow-belajar` pada terminal latihan. Ini memisahkan nama container dan volume dari proyek utama. Port tetap 8070, jadi hentikan proyek utama lebih dahulu jika masih berjalan. Pada terminal baru untuk latihan, set variabel itu lagi sebelum perintah Compose atau script proyek.

Belum jalankan `Start.ps1` di folder latihan sampai kerangka addon bab 2 selesai. Jangan memuat data latihan sebelum addon lengkap pada bab 5.

## Checkpoint

Kamu dapat menjawab: browser mengakses port mana, Odoo menghubungi host database apa, source Python dipasang ke folder container mana, dan data apa yang tidak termasuk saat repo di-push. Jika salah satunya belum jelas, cocokkan kembali nilai pada `compose.yaml` dengan tabel istilah di atas.
