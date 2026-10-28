# 06. Menguji aturan ERP dan mencari penyebab error

Tes perlu membuktikan bahwa dokumen dan stok berubah sesuai aturan, termasuk saat seseorang memanggil metode langsung tanpa tombol UI. SupplyFlow memeriksa hal itu melalui tes ORM Odoo, validator arsip backup, dan browser Playwright.

Bab ini menjelaskan berkas tes yang sudah ada, cara membacanya, cara menjalankannya, dan lokasi pemeriksaan saat terjadi error. Hasil aktual proyek dicatat terpisah pada [VERIFICATION.md](../VERIFICATION.md). Menyalin tes atau menjalankan perintah belum berarti tes tersebut lulus.

Semua perintah praktik di bab ini memakai folder **latihan** sesudah paket final bab 05 dipasang. Pada setiap terminal baru, masuk ke `D:\Latihan-Odoo\supplyflow-office` dan set `COMPOSE_PROJECT_NAME=supplyflow-belajar` lagi. Nama itu harus cocok dengan data serta secret yang dibuat terminal latihan sebelumnya.

### Siapkan berkas verifikasi pada folder latihan

Bab 01 sudah menyalin scripts dan Compose; bab 05 menyalin addon lengkap beserta tes ORM-nya. Untuk tes arsip dan browser, salin sumber verifikasi berikut. Perintah hanya menyalin file source dan lockfile, tanpa `node_modules`, password, hasil tes, atau data instance:

```powershell
$referensi = 'D:\kerjaan\done push repo\supplyflow-odoo'
$latihan = 'D:\Latihan-Odoo\supplyflow-office'
if (-not (Test-Path -LiteralPath "$latihan\addons\supplyflow_office\__manifest__.py" -PathType Leaf)) {
    throw 'Addon latihan belum tersedia. Selesaikan paket final bab 05 lebih dahulu.'
}
Set-Location -LiteralPath $latihan
$env:COMPOSE_PROJECT_NAME = 'supplyflow-belajar'
Copy-Item -LiteralPath "$referensi\package.json" -Destination "$latihan\package.json" -Force
Copy-Item -LiteralPath "$referensi\package-lock.json" -Destination "$latihan\package-lock.json" -Force
Copy-Item -LiteralPath "$referensi\playwright.config.js" -Destination "$latihan\playwright.config.js" -Force
New-Item -ItemType Directory -Path "$latihan\tests\browser" -Force | Out-Null
Copy-Item -LiteralPath "$referensi\tests\test_backup_archive.py" -Destination "$latihan\tests\test_backup_archive.py" -Force
Copy-Item -LiteralPath "$referensi\tests\browser\helpers.js" -Destination "$latihan\tests\browser\helpers.js" -Force
Copy-Item -LiteralPath "$referensi\tests\browser\workflows.spec.js" -Destination "$latihan\tests\browser\workflows.spec.js" -Force
Copy-Item -LiteralPath "$referensi\tests\browser\screenshots.spec.js" -Destination "$latihan\tests\browser\screenshots.spec.js" -Force
```

Jika hanya membaca dan sengaja menguji proyek utama yang sudah jadi, pilih terminal terpisah dan gunakan pengganti konteks berikut sebelum Docker/script proyek utama:

```powershell
Remove-Item Env:COMPOSE_PROJECT_NAME -ErrorAction SilentlyContinue
Set-Location -LiteralPath 'D:\kerjaan\done push repo\supplyflow-odoo'
```

Pada jalur proyek utama, jangan menerapkan `COMPOSE_PROJECT_NAME=supplyflow-belajar`. Pada jalur latihan, jangan beralih ke folder utama sambil membawa variabel latihan. Setiap blok praktik berikut kembali menetapkan folder dan context latihan supaya password/config serta volume berasal dari instance yang sama. Port kedua instance tetap 8070; jalankan satu instance pada satu waktu.

## 1. Pisahkan tiga lapisan pemeriksaan

| Lapisan | Jumlah pada versi terdokumentasi | Sumber | Yang dibuktikan |
| --- | --- | --- | --- |
| ORM addon | 42 metode tes: 17 permintaan, 20 kasus, 3 workspace, 2 distribusi | [tests addon](../../addons/supplyflow_office/tests/__init__.py) | Model, izin, transisi, angka, hubungan native, perusahaan, dan perubahan stok |
| Validator arsip | 25 metode unittest | [test_backup_archive.py](../../tests/test_backup_archive.py) | Struktur/path/hash/versi arsip sebelum restore |
| Workflow browser | 9 tes | [workflows.spec.js](../../tests/browser/workflows.spec.js) | Login, tombol/form, navigasi, kondisi workspace, PDF, dan transaksi HTTP bersamaan |
| Capture | 1 tes yang menghasilkan 8 PNG | [screenshots.spec.js](../../tests/browser/screenshots.spec.js) | Mengambil gambar dari aplikasi yang berjalan dengan data latihan |

Capture dipisahkan dari sembilan workflow melalui tag `@capture`. Full run lokal yang mengikutsertakan capture berjumlah sepuluh tes. CI menjalankan sembilan workflow tanpa capture. Angka 42/25/9 tidak boleh dijumlahkan lalu disebut persentase coverage kode; proyek tidak mengukur line coverage pada catatan tersebut.

## 2. Pahami struktur tes ORM

[addons/supplyflow_office/tests/__init__.py](../../addons/supplyflow_office/tests/__init__.py) mengimpor keempat file tes. Berkas tes yang tidak diimpor dapat luput dari pemuatan test runner addon.

Pada [test_purchase_request.py](../../addons/supplyflow_office/tests/test_purchase_request.py), pembuka class adalah:

```python
@tagged("post_install", "-at_install", "supplyflow")
class TestPurchaseRequest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
```

`TransactionCase` memberikan environment Odoo beserta transaksi database. `setUpClass()` menyiapkan fixture bersama satu kali untuk class. Fixture adalah data yang sengaja dibuat agar kondisi awal tes jelas, seperti pemasok, produk, gudang, pengaju, dan reviewer.

Odoo menjalankan setiap metode `test_...` dalam savepoint, yaitu batas pemulihan di dalam transaksi. Perubahan suatu metode dikembalikan setelah selesai agar metode berikutnya tidak menerima hasil samping tes sebelumnya. Transaksi class ditutup tanpa commit. Jangan menambahkan `self.env.cr.commit()` sebagai cara membuat tes lolos. Perilaku ini berasal dari [implementasi resmi TransactionCase Odoo 19](https://github.com/odoo/odoo/blob/19.0/odoo/tests/common.py).

Tag `post_install` meminta tes dijalankan setelah pemasangan modul, sedangkan `-at_install` mengeluarkannya dari fase tes saat pemasangan masing-masing modul. Tag `supplyflow` memberi penanda tambahan pada sebagian class; script proyek memilih addon melalui `--test-tags /supplyflow_office`.

### Fixture harus mewakili pengguna sebenarnya

`setUpClass()` permintaan membuat requester, approver, peer, outsider, reviewer yang hanya punya sebagian hak native, dan akun multi-perusahaan. `new_test_user()` mengisi kelompok secara eksplisit. `with_user(...)` kemudian menjalankan metode sebagai akun yang diuji.

Helper `_values()` menyiapkan nilai permintaan, `_request()` membuatnya sebagai requester, dan `_approved_request()` menjalankan submit serta persetujuan akun lain. Helper tersebut mengurangi pengulangan persiapan. Isi assertion tetap menjelaskan aturan yang diuji.

Checkpoint: cari satu pemanggilan `with_user(self.approver)` dan bedakan dari environment awal tes. Tanpa pergantian pengguna yang benar, tes izin dapat berjalan sebagai akun yang terlalu berkuasa dan memberi rasa aman yang keliru.

## 3. Uji alur permintaan dan penolakannya

[test_purchase_request.py](../../addons/supplyflow_office/tests/test_purchase_request.py) mempunyai 17 metode tes. Baca `test_request_to_native_rfq_uses_company_warehouse_and_estimate()` terlebih dahulu. Tes ini memeriksa status RFQ draft, pemasok, perusahaan, mata uang, gudang incoming, origin, produk, satuan, kuantitas, estimasi, serta metadata persetujuan.

Tes pengulangan aksi menggunakan fungsi lengkap berikut di dalam class:

```python
    def test_rfq_conversion_is_idempotent(self):
        request = self._approved_request()
        first = request.with_user(self.approver).action_create_rfq()
        second = request.with_user(self.approver).action_create_rfq()
        self.assertEqual(first["res_id"], second["res_id"])
        orders = self.env["purchase.order"].search([("origin", "=", request.name)])
        self.assertEqual(orders, request.purchase_order_id)
```

Idempoten berarti pengulangan aksi menghasilkan dokumen hasil yang sama, bukan RFQ tambahan. Dua panggilan di atas berjalan berurutan. Kasus klik bersamaan masih membutuhkan tes HTTP terpisah pada bagian berikutnya.

Tes persetujuan independen berisi potongan berikut:

```python
    def test_approval_needs_an_independent_reviewer(self):
        own = self._request(user=self.approver)
        own.action_submit()
        with self.assertRaises(AccessError):
            own.action_approve()
        with self.assertRaises(AccessError):
            own.write({"decision_reason": "I approve my own request"})
```

`assertRaises(AccessError)` mengharapkan operasi ditolak. Jika operasi tiba-tiba berhasil, tes gagal. Bagian lanjutan pada sumber memeriksa requester/peer yang tidak boleh mengambil keputusan, lalu approver independen yang berhasil.

Odoo membungkus `assertRaises` miliknya dengan pengelolaan environment/savepoint. Pada tes addon ini gunakan satu kelas exception yang diharapkan pada setiap context. Polanya dapat dibaca pada [BaseCase Odoo 19](https://github.com/odoo/odoo/blob/19.0/odoo/tests/common.py). Validator arsip memakai `unittest.TestCase` standar sehingga perilaku helper-nya tidak harus disamakan dengan helper Odoo.

Metode lain yang perlu ditelusuri:

| Metode tes | Mengapa diperlukan |
| --- | --- |
| `test_rfq_preserves_estimate_even_when_vendor_prices_are_configured` | Harga vendor native dapat menghitung ulang baris; estimasi yang disetujui, termasuk nol, perlu tetap dipindahkan sesuai rancangan |
| `test_reject_and_revision_preserve_chatter_then_require_new_approval` | Revisi setelah penolakan harus ditinjau ulang dan riwayat lama tetap dapat ditelusuri |
| `test_direct_state_audit_and_link_changes_are_blocked` | Pengguna tidak boleh melompati workflow melalui `write()` pada state/audit/tautan |
| `test_context_defaults_cannot_forge_approval_or_link` | Context RPC tidak boleh menyisipkan persetujuan saat create |
| `test_submitted_parent_and_every_line_mutation_path_are_frozen` | Perlindungan harus menutup perubahan parent, baris, penghapusan, dan pemindahan relasi |
| `test_standard_purchase_rights_are_still_required` | Kelompok Approver addon tidak otomatis menjadi izin membuat dokumen Purchase |
| `test_company_record_rules_hide_requests_and_lines` | Isolasi perusahaan berlaku pada pencarian, pembacaan ID, perubahan, dan baris |
| `test_numeric_edits_are_validated_before_database_conversion` | Input non-finite atau terlalu besar perlu ditolak sebelum konversi field/SQL merusak alur error |
| `test_workflow_actions_have_no_state_shortcuts` | Metode harus menolak urutan tindakan yang tidak sesuai status |
| `test_approved_request_can_only_be_cancelled_by_an_independent_approver` | Pembatalan setelah persetujuan juga memiliki batas pelaku |

Sumber lengkap juga memeriksa kepemilikan draft, perusahaan vendor/produk/gudang, baris kosong/invalid/non-stok, dan akun tanpa kelompok SupplyFlow. Baca alasan kegagalan assertion sebelum mengubah implementasi atau melemahkan tes.

## 4. Uji kasus receipt dan perubahan stok sebenarnya

[test_supplier_issue.py](../../addons/supplyflow_office/tests/test_supplier_issue.py) mempunyai 20 metode. Helper `_make_receipt()` membuat incoming picking native, mengonfirmasi, mengisi jumlah aktual, dan memvalidasi. Fixture menolak melanjutkan jika receipt belum `done`.

Pada Odoo 19, fixture ini menulis `quantity` dan `picked` pada move. Jangan mengganti contoh dengan nama field dari versi Odoo lain tanpa memeriksa sumber versi yang dipakai.

Di dalam `test_independent_approval_creates_native_return_without_moving_stock()`, bagian setelah pembuatan retur memeriksa:

```python
        self.assertNotEqual(returned.state, "done")
        self.product.invalidate_recordset(["qty_available"])
        self.assertEqual(self.product.qty_available, before)
        returned.move_ids.write({"quantity": 3, "picked": True})
        returned.button_validate()
        self.assertEqual(returned.state, "done")
        self.product.invalidate_recordset(["qty_available"])
        self.assertEqual(self.product.qty_available, before - 3)
        self.assertEqual(issue.return_state, "done")
```

Tes membedakan membuat rencana transfer dari memvalidasi perpindahan barang. `invalidate_recordset` meminta pembacaan nilai stok kembali ketika assertion memerlukan hasil terbaru. Pemeriksaan tidak sekadar membandingkan teks status kasus.

Contoh batas jumlah retur yang masih menunggu:

```python
    def test_existing_pending_returns_reserve_their_quantity(self):
        first = self._issue(7)
        second = self._issue(4)
        self._approve(first)
        self._approve(second)
        first.with_user(self.approver).action_create_return()
        with self.assertRaises(UserError):
            second.with_user(self.approver).action_create_return()
        self.assertFalse(second.return_picking_id)
        self.assertEqual(second.state, "approved")
```

Fixture menerima 10 unit. Retur 7 yang sudah dibuat memakai kapasitas sumber itu walaupun belum done. Retur kedua sejumlah 4 harus ditolak, dan kasus kedua tetap approved tanpa tautan retur. Tes terpisah memeriksa retur native di luar addon dan retur yang dibatalkan.

Kelompok pemeriksaan lain pada file yang sama meliputi:

- Pembuatan retur idempoten, reviewer independen, larangan pengaju menyetujui kasusnya sendiri, dan hak pembatalan.
- Field state/audit/link, default context, detail receipt turunan, context wizard, serta revisi sumber yang tidak boleh dipalsukan.
- Parent/baris yang membeku sesudah pengajuan, pemilik draft, dan pemindahan baris ke parent lain.
- Receipt incoming selesai, kecocokan perusahaan, sumber stock move, angka positif/finite, serta batas kuantitas.
- Shortage yang harus diselesaikan dengan catatan tanpa retur fisik.

Checkpoint: ikuti satu tes negatif dari input sampai assertion. Catat kondisi awal, aktor yang memanggil metode, exception yang diharapkan, lalu status/tautan yang harus tetap utuh sesudah penolakan.

## 5. Uji integrasi seluruh distribusi dan angka workspace

[test_distribution_flow.py](../../addons/supplyflow_office/tests/test_distribution_flow.py) mempunyai dua skenario. `_purchase_for()` menjalankan permintaan custom sampai RFQ, lalu mengonfirmasi PO melalui metode Purchase. `_finish_picking()` memproses picking melalui metode Inventory. `_stock_at()` membaca jumlah `stock.quant` pada lokasi gudang untuk assertion; helper itu tidak menulis quant untuk memalsukan hasil.

`test_approved_purchase_partial_receipt_return_and_customer_delivery()` memeriksa rangkaian berikut:

```text
Permintaan 20 → persetujuan → RFQ/PO
  → receipt pertama 12 + wizard backorder 8
  → receipt backorder selesai: stok 20
  → rencana retur 2: stok masih 20
  → retur divalidasi: stok 18
  → sales order/delivery 7 divalidasi: stok 11
```

Tes memakai `Form.from_action(...).save()` untuk wizard keputusan backorder yang benar-benar dihasilkan Odoo. Artinya sisa 8 tidak dipalsukan dengan membuat baris stok secara terpisah. Purchase line, receipt move, return move, sale line, dan delivery diperiksa hubungannya.

`test_selected_receiving_warehouse_then_native_internal_transfer()` menerima 10 pada gudang B, memindahkan 4 ke A melalui internal picking, lalu memeriksa A=4, B=6, dan total produk tetap 10.

[test_workspace.py](../../addons/supplyflow_office/tests/test_workspace.py) memiliki tiga pemeriksaan:

| Metode | Hasil yang diperiksa |
| --- | --- |
| `test_empty_workspace_uses_real_counts` | Workspace kosong mengembalikan nol dan daftar kosong |
| `test_unassigned_user_cannot_call_workspace` | Akun tanpa kelompok SupplyFlow ditolak |
| `test_counts_follow_request_workflow` | Permintaan submitted menambah pending menjadi 1; pembatalan mengembalikannya menjadi 0 |

Jumlah workspace berasal dari record yang dibuat pada tes. Tidak ada angka statistik contoh yang diperlakukan sebagai hasil database.

## 6. Jalankan ORM pada database terisolasi

Dari folder latihan:

```powershell
cd 'D:\Latihan-Odoo\supplyflow-office'
$env:COMPOSE_PROJECT_NAME = 'supplyflow-belajar'
.\scripts\Test.ps1
```

[Test.ps1](../../scripts/Test.ps1) melakukan urutan berikut:

1. Membaca/menyiapkan konfigurasi lokal melalui [Common.ps1](../../scripts/Common.ps1).
2. Pull image kecuali `-SkipPull`, lalu menyalakan PostgreSQL milik proyek.
3. Menghentikan layanan Odoo SupplyFlow yang biasa agar proses maintenance tidak berjalan bersamaan.
4. Membuat database unik `supplyflow_test_` diikuti GUID, dengan pemilik role aplikasi `supplyflow`.
5. Menjalankan container satu kali untuk instalasi addon serta tes.
6. Dalam `finally`, menghapus database/filestore uji, kecuali `-KeepDatabase` dipilih.

Container tes memakai [compose.test.yaml](../../compose.test.yaml), `--no-http`, `--max-cron-threads=0`, `--stop-after-init`, `--without-demo=True`, `-i supplyflow_office`, `--test-enable`, dan `--test-tags /supplyflow_office`. Overlay mematikan healthcheck untuk job yang memang tidak melayani HTTP.

`Test.ps1` meninggalkan aplikasi Odoo biasa dalam keadaan berhenti; script tidak menyalakannya kembali otomatis. PostgreSQL tetap berjalan. Sesudah tes, gunakan `Start.ps1` bila ingin membuka UI lagi:

```powershell
cd 'D:\Latihan-Odoo\supplyflow-office'
$env:COMPOSE_PROJECT_NAME = 'supplyflow-belajar'
.\scripts\Start.ps1 -WithTrainingData -SkipPull
```

Gunakan `-SkipPull` pada Test hanya jika image yang dipatok sudah tersedia. Untuk penyelidikan lokal:

```powershell
cd 'D:\Latihan-Odoo\supplyflow-office'
$env:COMPOSE_PROJECT_NAME = 'supplyflow-belajar'
.\scripts\Test.ps1 -SkipPull -KeepDatabase
```

Nama database yang ditahan dicetak ke terminal. Pilihan tersebut menahan database hasil instalasi/tes untuk inspeksi; transaksi fixture tes tetap mengikuti rollback `TransactionCase`. Hindari menjalankannya berkali-kali tanpa membersihkan hasil yang ditahan. Script [clean_test_filestore.py](../../scripts/container/clean_test_filestore.py) memeriksa pola nama database uji sebelum membersihkan folder filestore.

## 7. Uji validator arsip tanpa PostgreSQL

[test_backup_archive.py](../../tests/test_backup_archive.py) memakai `unittest.TestCase` standar, bukan environment Odoo. File mengimpor [restore.py](../../scripts/container/restore.py) untuk memanggil `validate_archive()`. `setUp()` membuat folder sementara dan mendaftarkan pembersihannya.

`make_archive()` membangun ZIP kecil dengan dump sintetis berheader `PGDMP`, satu filestore sintetis, dan manifest. Data tersebut hanya cukup untuk menguji validator, bukan database PostgreSQL yang dapat direstore.

Contoh tes path traversal:

```python
    def test_reject_parent_path(self):
        self.assert_invalid_path("../escape")
```

Helper `assert_invalid_path()` menyisipkan nama path itu ke ZIP; `assert_invalid()` mengharapkan validator menolak. Tes lain mengganti payload/hash/ukuran/versi, membuat symlink, nama duplikat, konflik direktori/berkas, atau header dump tidak valid.

Jalankan:

```powershell
cd 'D:\Latihan-Odoo\supplyflow-office'
$env:COMPOSE_PROJECT_NAME = 'supplyflow-belajar'
python -m unittest discover -s tests -p test_backup_archive.py
```

Perintah ini tidak menyalakan server dan tidak memulihkan database. Keberhasilan 25 tes validator harus dilengkapi latihan backup/restore nyata. Latihan proyek yang sudah dilakukan membandingkan fingerprint 16 tabel serta lampiran filestore pada stack terpisah; rincian buktinya ada pada [VERIFICATION.md](../VERIFICATION.md).

## 8. Siapkan browser test

Node pada repo dipakai untuk verifikasi browser. Server ERP tetap Odoo. [package.json](../../package.json) mematok `@playwright/test` 1.64.1 dan menyediakan dua script:

```json
  "scripts": {
    "test:browser": "playwright test --grep-invert @capture",
    "screenshots": "playwright test --grep @capture"
  },
```

[playwright.config.js](../../playwright.config.js) memakai satu worker, base URL `http://127.0.0.1:8070`, viewport desktop 1440×960, dan Microsoft Edge secara default. CI memilih Chromium melalui `PLAYWRIGHT_CHANNEL`. `SUPPLYFLOW_URL` dapat mengganti base URL untuk instance latihan yang sengaja dipilih.

Siapkan instance latihan dan dependensi:

```powershell
cd 'D:\Latihan-Odoo\supplyflow-office'
$env:COMPOSE_PROJECT_NAME = 'supplyflow-belajar'
.\scripts\Start.ps1 -WithTrainingData -SkipPull
npm ci
npm run test:browser
```

Data latihan menyediakan akun buyer, approver, warehouse, serta index ID dokumen. Password dibuat lokal dan dibaca helper dari `.secrets`; isi file kredensial tidak dicetak dalam tutorial. Suite workflow membuat dokumen verifikasi tambahan. Jalankan pada instance latihan proyek, bukan database operasional berisi transaksi pengguna.

Jika memilih Chromium pada komputer yang belum memilikinya, pasang runtime yang diperlukan dan set channel sebelum tes:

```powershell
cd 'D:\Latihan-Odoo\supplyflow-office'
$env:COMPOSE_PROJECT_NAME = 'supplyflow-belajar'
npx playwright install chromium
$env:PLAYWRIGHT_CHANNEL = "chromium"
npm run test:browser
Remove-Item Env:PLAYWRIGHT_CHANNEL
```

## 9. Baca helper login, RPC, dan tombol

[helpers.js](../../tests/browser/helpers.js) menyediakan:

| Fungsi | Tugas |
| --- | --- |
| `credentials(role)` | Membaca password admin atau akun latihan dari file lokal yang diabaikan Git |
| `login(page, role)` | Mengisi form login dan menunggu navbar ERP terlihat |
| `rpc(page, model, method, args, kwargs)` | Memanggil `call_kw`, memeriksa error JSON-RPC, lalu mengembalikan result |
| `clickWorkflow(...)` | Mengklik tombol, mengonfirmasi dialog bila diminta, dan menunggu respons metode bisnis yang sesuai |
| `authenticateApi(request, role)` | Login context HTTP tanpa membuka SPA browser |
| `trainingIndex(page)` | Membaca index ID fixture dari parameter latihan |
| `openAction(page, action)` | Membuka route action Odoo dan menunggu action manager |
| `openRecord(page, action, id)` | Membuka satu record dan menunggu form |

`rpc()` memeriksa `body.error`, karena respons HTTP yang berhasil dikirim tetap dapat membawa error bisnis JSON-RPC. Assertion tidak cukup berhenti pada status HTTP 200.

Bagian awal `clickWorkflow()` memasang penunggu sebelum klik:

```javascript
export async function clickWorkflow(page, model, method, buttonName, { confirm = false } = {}) {
    const [response] = await Promise.all([
        page.waitForResponse((candidate) => {
            const request = candidate.request();
            if (request.method() !== "POST" || !new URL(candidate.url()).pathname.startsWith("/web/dataset/call_button")) return false;
            try {
                const params = request.postDataJSON()?.params;
                return params?.model === model && params?.method === method;
            } catch {
                return false;
            }
        }),
```

Bagian berikut pada fungsi lengkap mengklik tombol berdasarkan accessible name, menerima dialog jika perlu, memeriksa respons JSON-RPC, lalu menunggu field penanda pada dokumen native yang dibuka. Purchase order ditunggu melalui `order_line`, picking melalui `move_ids`.

Tujuannya agar assertion setelah klik tidak mendahului penyelesaian request bisnis. Jangan menggantinya dengan jeda tetap beberapa detik. Halaman yang terlihat cepat pada satu komputer belum menjamin transaksi sudah selesai saat komputer lain lebih lambat.

## 10. Telusuri sembilan workflow

[workflows.spec.js](../../tests/browser/workflows.spec.js) berisi urutan berikut:

| Tes | Pemeriksaan |
| --- | --- |
| `workspace counts, filters and keyboard navigation` | Angka sesuai RPC, empat filter, All requests, nomor terbaru, fokus/Tab/Enter/Escape, dan error JavaScript |
| `workspace recovers from RPC failure and fits a narrow screen` | Loading yang dikendalikan, Refresh disabled, respons kosong, error, retry, dan viewport 390 px |
| `purchase request QWeb produces a real PDF` | Endpoint laporan memberi MIME PDF, signature `%PDF-`, dan isi nonkosong |
| `requester creates a request through the form and withdraws it` | Pemilihan pemasok/gudang/produk, kuantitas/harga, submit, dan konfirmasi withdraw |
| `requester cannot approve, independent approver creates one native RFQ` | Sesi pengaju ditolak; sesi reviewer lain menyetujui serta membuka RFQ native tunggal |
| `supplier review creates return without completing warehouse transfer` | Tindakan review/retur dan pembukaan picking native tertaut |
| `rejection, revision and approval cancellation work through form buttons` | Alasan penolakan, revisi, pengajuan baru, persetujuan, dan pembatalan |
| `shortage resolution and issue cancellation work through form buttons` | Penyelesaian shortage tanpa picking dan varian pembatalan pelapor/Approver |
| `separate HTTP sessions cannot create duplicate RFQs or excess returns` | Panggilan bersamaan pada transaksi HTTP terpisah |

Periksa judul dan isi tes bersama. Beberapa skenario menyiapkan data lewat RPC, kemudian memeriksa tindakan lewat UI. Itu berbeda cakupan dari mengetik semua input pada form. Tes permintaan keempat memang mengisi form dari New. Tes kondisi kosong/error sengaja mengganti respons RPC sementara; respons sintetis itu hanya fixture UI yang diberi label, bukan hasil statistik bisnis sebenarnya.

Bagian PDF pada tes memeriksa:

```javascript
    const response = await page.request.get(`/report/pdf/supplyflow_office.report_request/${index.request_approved}`);
    expect(response.ok()).toBe(true);
    expect(response.headers()["content-type"]).toContain("application/pdf");
    const pdf = await response.body();
    expect(pdf.subarray(0, 5).toString()).toBe("%PDF-");
    expect(pdf.length).toBeGreaterThan(2000);
```

Endpoint ini membuktikan PDF benar-benar dihasilkan. Pemeriksaan itu belum menjadi audit tata letak seluruh panjang purpose, jumlah baris, atau variasi nama pemasok. PDF lokal juga disimpan di `.local/request-summary.pdf`, yang tidak masuk Git.

### Mengapa perlu sesi HTTP terpisah untuk konkurensi?

Dua panggilan berurutan hanya membuktikan pengulangan. Uji konkurensi membuat empat context HTTP independen, login sesuai peran, lalu mengirim dua aksi pada waktu yang berdekatan:

```javascript
        const results = await Promise.allSettled([
            rpc(reviewerOne, "supplyflow.request", "action_create_rfq", [[id]]),
            rpc(reviewerTwo, "supplyflow.request", "action_create_rfq", [[id]]),
        ]);
```

Setelah respons selesai, tes membaca dokumen hasil dan menghitung purchase order berdasarkan origin. Harus ada tepat satu RFQ. Setiap respons yang berhasil harus menunjuk ID RFQ tertaut yang sama. Tes tidak mensyaratkan kedua request selalu berhasil; penolakan lock/transaksi tertentu dapat terjadi, sedangkan invariant satu dokumen harus tetap terpenuhi.

Bagian retur membuat dua kasus dengan jumlah masing-masing lebih dari separuh sisa sumber, lalu memanggil `action_create_return` melalui reviewer context berbeda. Tepat satu keberhasilan dan satu kasus bertaut picking diperiksa. Picking verifikasi dibatalkan setelahnya agar reservasi uji tidak terus memakai jatah stok latihan.

## 11. Ambil screenshot dari aplikasi yang berjalan

[screenshots.spec.js](../../tests/browser/screenshots.spec.js) mempunyai fungsi `capture(page, name)`. Fungsi menunggu loading indicator hilang, lalu menyimpan screenshot `fullPage` pada `docs/screenshots`. Tes `@capture real ERP screens` mengunjungi delapan keadaan:

1. Operations desktop.
2. Daftar purchase requests.
3. Permintaan approved.
4. Purchase order/RFQ native tertaut.
5. Kasus supplier approved.
6. Receipt native selesai.
7. Sales order native.
8. Operations pada viewport 390×844.

Perintahnya:

```powershell
cd 'D:\Latihan-Odoo\supplyflow-office'
$env:COMPOSE_PROJECT_NAME = 'supplyflow-belajar'
npm run screenshots
```

Perintah menulis ulang gambar pada `docs/screenshots`. Periksa setiap hasil sebelum commit: teks terbaca, data latihan sesuai, layar bukan loading/error, dan tidak ada kredensial/data pribadi yang ikut tampil. Screenshot membuktikan keadaan layar yang ditangkap; aturan bisnis tetap dibuktikan oleh assertion model dan workflow.

## 12. Cari error dari lapisan yang paling dekat

Dari folder latihan, perintah inspeksi awal:

```powershell
cd 'D:\Latihan-Odoo\supplyflow-office'
$env:COMPOSE_PROJECT_NAME = 'supplyflow-belajar'
docker compose ps
docker compose logs --tail=150 odoo
docker compose logs --tail=100 postgres
```

`ps` menunjukkan layanan berjalan/sehat. Log Odoo memuat traceback Python, pemuatan XML, dan request laporan. Log PostgreSQL membantu ketika koneksi database gagal. Jangan menyalin isi `.secrets` atau `.runtime/odoo.conf` ke issue publik saat meminta bantuan.

| Gejala | Tempat yang diperiksa | Langkah berikutnya |
| --- | --- | --- |
| `Field ... does not exist` saat update | Model, import `models/__init__.py`, dan XML field | Pastikan model final sudah dimuat sebelum view final; periksa nama field |
| External ID tidak ditemukan | Manifest dan `ref` XML/action | Periksa nama addon, ID, serta urutan file `data` |
| Menu tidak tampil | `groups.xml`, kelompok akun, ACL, dan menu | Pastikan akun mendapat kelompok addon; jangan mengatasinya dengan `sudo()` menyeluruh |
| Tombol disembunyikan | `invisible`, `groups`, status, dan pengaju | Bandingkan aktor/status dengan rancangan, lalu periksa guard Python |
| Tombol ada tetapi AccessError/UserError | Metode model dan respons RPC | Baca pesan bisnis; periksa hak native Purchase/Inventory dan perusahaan aktif |
| Workspace kosong padahal ada data | `get_overview`, context perusahaan, state dokumen | Pahami bahwa metrik hanya menghitung status tertentu dan record yang boleh dibaca |
| Workspace menampilkan error | Network `get_overview`, Console, log Odoo | Cari error asli server; gunakan Try again setelah penyebabnya selesai |
| `Missing template` atau action tidak ditemukan | Manifest assets, `t-name`, `static template`, key registry | Cocokkan nama, update addon, lalu muat ulang asset |
| Perubahan XML tidak terlihat | Hasil update addon dan cache browser | Hentikan Odoo, jalankan `manage.py update`, nyalakan ulang, lalu refresh |
| PDF 500 | Traceback QWeb, `report_name`, dan template | Periksa field yang dirujuk serta pola span di dalam td |
| Playwright timeout setelah klik | Network `call_button`, hasil bisnis, locator form native | Pastikan respons metode selesai; gunakan locator field yang sesuai mode readonly/edit |
| Tes ORM melaporkan nol tes | Import tes, tag, dan parameter runner | Cocokkan `tests/__init__.py` serta `--test-tags /supplyflow_office` |
| Browser tidak dapat login setelah ORM | Status container Odoo | `Test.ps1` menghentikan Odoo; jalankan kembali Start dengan data latihan |
| Halaman pertama lama memuat | Log pemuatan asset dan sumber daya komputer | Tunggu bukti pemuatan/health; jangan langsung menghapus volume data |

Field relasi yang sedang editable dapat menaruh nama pemasok pada nilai `<input>`, sedangkan field readonly dapat menampilkannya sebagai teks/link. Assertion browser harus membaca elemen yang sesuai. Mengubah assertion dari nilai ke teks tanpa memeriksa DOM dapat menyebabkan tes gagal meskipun tindakan bisnis berhasil.

Untuk menjalankan satu kelompok browser saat debugging, panggil CLI langsung dengan filter judul:

```powershell
cd 'D:\Latihan-Odoo\supplyflow-office'
$env:COMPOSE_PROJECT_NAME = 'supplyflow-belajar'
node .\node_modules\@playwright\test\cli.js test --grep 'requester cannot approve'
```

Sesudah error diperbaiki, jalankan kembali skenario yang terdampak beserta pemeriksaan lain yang relevan. Jangan mengubah assertion menjadi lebih longgar hanya agar hasilnya hijau.

## 13. Susun urutan CI yang dapat diulang

[.github/workflows/verify.yml](../../.github/workflows/verify.yml) berjalan pada push dan pull request dengan izin repository `contents: read`. Job pada runner Ubuntu baru melakukan:

1. Checkout sumber dan setup Node 22 dengan cache npm.
2. `npm ci` dari lockfile.
3. Jalankan 25 validator arsip melalui unittest.
4. Pasang Chromium beserta dependensi sistem Playwright.
5. Jalankan `Test.ps1` untuk instalasi/database unik serta tes ORM.
6. Jalankan `Start.ps1 -WithTrainingData -SkipPull` untuk instance browser.
7. Jalankan `npm run test:browser` dengan channel Chromium.
8. Jika gagal, cetak log container dan unggah `playwright-report`/`test-results` dengan retensi tiga hari.

Trace browser disimpan pada kegagalan di CI. Lokal memakai trace off secara default untuk mengurangi beban komputer. Kedua lingkungan memakai satu worker. Runtime lokal Windows/Edge dan CI Ubuntu/Chromium berbeda, sehingga keberhasilan keduanya memberi bukti pada dua lingkungan yang benar-benar dicoba, bukan jaminan seluruh browser/platform.

[Run verifikasi implementasi](https://github.com/zalamanga/supplyflow-odoo/actions/runs/40655694868) telah lulus untuk 42 tes ORM, 25 tes arsip, dan sembilan workflow Chromium. Saat mengikuti tutorial pada commit baru, baca hasil run commit tersebut. Hasil lama tidak otomatis membuktikan perubahan baru.

Checkpoint akhir: jelaskan satu tes positif, satu penolakan izin, satu assertion stok, dan satu tes konkurensi dengan kata-kata sendiri. Untuk setiap tes, sebutkan kondisi awal, tindakan, hasil yang wajib terjadi, serta hasil yang wajib tidak terjadi. Lanjutkan ke [07. Operasi dan latihan](07-operasi-dan-latihan.md).
