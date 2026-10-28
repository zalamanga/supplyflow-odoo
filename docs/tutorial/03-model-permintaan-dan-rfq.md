# 03. Membuat model permintaan pembelian dan RFQ

Bab ini mengikuti file [models/purchase_request.py](../../addons/supplyflow_office/models/purchase_request.py) pada SupplyFlow Office. Hasilnya adalah dokumen permintaan pembelian yang diajukan oleh satu pengguna, ditinjau pengguna lain, lalu menghasilkan RFQ standar Odoo.

Kamu akan membaca kode dalam urutan pembuatannya: bentuk data, aturan angka, aturan pemilik, penyimpanan, perpindahan status, dan hubungan ke Purchase. Semua cuplikan Python di bab ini diambil dari source proyek. Cuplikan berlabel fungsi lengkap tetap merupakan bagian kelas, bukan file mandiri yang bisa langsung dijalankan dengan `python purchase_request.py`.

Untuk latihan yang dapat dijalankan, gunakan file lengkap dari repo beserta manifest, import, ACL, aturan perusahaan, sequence, dan XML view. Jangan mengganti file lengkap dengan gabungan beberapa cuplikan pilihan. Penjagaan akses pada implementasi ini saling bergantung.

Jika mengikuti pembangunan di folder kosong dari bab 02, **ganti seluruh isi file model minimal** dengan file final yang dijelaskan di bab ini. Jangan menambahkan kelas `SupplyFlowRequest` kedua di bawah kelas percobaan. Bab 03 dan 04 menyusun model final; instalasi lengkap pertama pada folder latihan dilakukan di [bab 05](05-tampilan-workspace-dan-pdf.md), setelah manifest, keamanan, view, report, dan aset final tersedia bersama. Latihan UI pada akhir bab ini dijalankan di salinan proyek referensi yang sudah lengkap.

## 1. Tentukan dokumen yang hendak dibuat

Misalnya staf distributor ingin membeli kertas untuk memenuhi pesanan kantor pelanggan. Pengaju mencatat pemasok, gudang tujuan, tanggal kebutuhan, alasan, dan daftar barang. Approver menilai kebutuhan tersebut sebelum membuat RFQ.

Terdapat dua model buatan sendiri dalam satu file:

| Kelas Python | Nama model Odoo | Isi |
| --- | --- | --- |
| `SupplyFlowRequest` | `supplyflow.request` | Satu permintaan: siapa yang mengajukan, pemasok, gudang, status, keputusan, RFQ terkait |
| `SupplyFlowRequestLine` | `supplyflow.request.line` | Satu jenis barang pada permintaan, jumlah, satuan, estimasi harga, subtotal |

Permintaan berisi banyak baris barang. Setiap baris menunjuk satu permintaan. Ketika RFQ dibuat, addon membuat record `purchase.order` dan `purchase.order.line` milik Odoo. Kita memakai proses pembelian yang sudah tersedia.

Istilah yang dipakai di bawah:

| Istilah | Arti pada kode ini |
| --- | --- |
| Model | Definisi jenis data beserta aturan dan perilakunya |
| Record | Satu dokumen atau satu baris barang yang sudah dibuat |
| Recordset | Kumpulan record; `self` bisa berisi satu atau beberapa record |
| ORM | Cara model Python membaca dan menyimpan data melalui Odoo |
| `self.env` | Lingkungan akses model, pengguna, perusahaan, dan context saat ini |
| `self.env.uid` / `self.env.user` | ID pengguna / record pengguna yang sedang melakukan operasi |
| `values` | Dictionary nilai field yang akan disimpan |
| Context | Nilai tambahan untuk operasi, misalnya perusahaan aktif atau default field; masukan context perlu diperiksa |
| `super()` | Melanjutkan operasi ke implementasi induk Odoo setelah pemeriksaan addon selesai |

## 2. Buat identitas kelas dan field dokumen

Lokasi: `addons/supplyflow_office/models/purchase_request.py`, kelas `SupplyFlowRequest`. Letakkan definisi field setelah identitas kelas dan sebelum kumpulan method. Berikut bagian awal kelas yang lengkap sampai constraint referensinya; ini cuplikan dari file, bukan seluruh kelas.


```python
class SupplyFlowRequest(models.Model):
    _name = "supplyflow.request"
    _description = "Purchase Requisition"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"
    _check_company_auto = True

    name = fields.Char(required=True, readonly=True, copy=False, default="New", index=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True
    )
    currency_id = fields.Many2one(related="company_id.currency_id", store=True)
    requester_id = fields.Many2one(
        "res.users", required=True, readonly=True, copy=False,
        default=lambda self: self.env.user, check_company=True, tracking=True,
    )
    vendor_id = fields.Many2one("res.partner", required=True, check_company=True, tracking=True)
    warehouse_id = fields.Many2one(
        "stock.warehouse", required=True, check_company=True, tracking=True,
        default=lambda self: self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        ),
    )
    requested_date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    purpose = fields.Text(required=True, tracking=True)
    line_ids = fields.One2many("supplyflow.request.line", "request_id", string="Items", copy=True)
    amount_estimated = fields.Monetary(
        string="Estimated Total", compute="_compute_amount_estimated", store=True,
        help="Estimated amount before taxes, in the company's currency.",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"), ("submitted", "Awaiting Approval"),
            ("approved", "Approved"), ("rejected", "Rejected"),
            ("rfq_created", "RFQ Created"), ("cancelled", "Cancelled"),
        ], default="draft", required=True, readonly=True, copy=False, index=True, tracking=True,
    )
    decision_reason = fields.Text(string="Decision Note", copy=False, tracking=True)
    submitted_by_id = fields.Many2one("res.users", readonly=True, copy=False, check_company=True)
    submitted_at = fields.Datetime(readonly=True, copy=False)
    approved_by_id = fields.Many2one("res.users", readonly=True, copy=False, check_company=True)
    approved_at = fields.Datetime(readonly=True, copy=False)
    rejected_by_id = fields.Many2one("res.users", readonly=True, copy=False, check_company=True)
    rejected_at = fields.Datetime(readonly=True, copy=False)
    purchase_order_id = fields.Many2one(
        "purchase.order", string="Request for Quotation", readonly=True, copy=False,
        check_company=True, ondelete="restrict", index=True,
    )
    _unique_rfq = models.Constraint(
        "UNIQUE(purchase_order_id)", "An RFQ can only belong to one requisition."
    )
    _unique_reference = models.Constraint(
        "UNIQUE(company_id, name)", "The requisition reference must be unique within its company."
    )
```

`_name` memberi nama model yang dipakai XML, ACL, dan `self.env["supplyflow.request"]`. `_inherit` menambahkan chatter dan aktivitas. Karena mewarisi `models.Model`, kelas ini memiliki operasi seperti `create`, `write`, `search`, dan `unlink`.

Beberapa pilihan field menentukan hubungan data:

- `vendor_id` adalah `Many2one` ke `res.partner`: satu permintaan memilih satu pemasok.
- `warehouse_id` menunjuk `stock.warehouse`. Default mencari gudang pada perusahaan aktif, bukan mengambil gudang sembarang perusahaan.
- `line_ids` adalah `One2many` dengan pasangan `request_id` pada model baris.
- `currency_id` mengambil mata uang dari perusahaan. Estimasi di bab ini menggunakan mata uang perusahaan dan belum termasuk pajak.
- `purchase_order_id` menyimpan RFQ hasil konversi. `ondelete="restrict"` menjaga agar RFQ yang dirujuk tidak mudah dihapus sehingga tautannya putus.
- `copy=False` mencegah nilai seperti nomor, status, dan jejak persetujuan ikut tersalin melalui mekanisme salin field Odoo.

`readonly=True` membantu tampilan form, tetapi server tetap memeriksa field yang dilindungi di `create()` dan `write()`. Pengguna tidak cukup dibatasi dengan menyembunyikan input atau tombol.

Dua `models.Constraint` menambah penjagaan database: satu RFQ tidak boleh dipakai dua permintaan dan nomor permintaan harus unik dalam perusahaan. Constraint tersebut melengkapi pemeriksaan Python.

### Siapkan identitas model di paket addon

[models/__init__.py](../../addons/supplyflow_office/models/__init__.py) memuat `purchase_request`. File import itu membuat Odoo membaca kelas Python saat addon dimuat. Definisi sequence berada di [data/sequences.xml](../../addons/supplyflow_office/data/sequences.xml). Nama kode sequence yang dicari nanti adalah `supplyflow.request`.

Jangan menamai file sembarang lalu lupa mengimpornya. XML yang merujuk `supplyflow.request` memerlukan model tersebut sudah terdaftar.

## 3. Buat bentuk baris dan perhitungan estimasi

Lokasi: file yang sama, kelas `SupplyFlowRequestLine`, setelah kelas permintaan. Bagian berikut memuat identitas, field, dan constraint baris; ini cuplikan kelas.


```python
class SupplyFlowRequestLine(models.Model):
    _name = "supplyflow.request.line"
    _description = "Purchase Requisition Item"
    _order = "id"
    _check_company_auto = True

    request_id = fields.Many2one("supplyflow.request", required=True, ondelete="cascade", index=True, check_company=True)
    company_id = fields.Many2one(related="request_id.company_id", store=True, index=True)
    currency_id = fields.Many2one(related="request_id.currency_id")
    product_id = fields.Many2one("product.product", required=True, check_company=True, ondelete="restrict")
    name = fields.Char(string="Description", required=True, compute="_compute_name", store=True, readonly=False, precompute=True)
    product_uom_id = fields.Many2one("uom.uom", string="Unit", compute="_compute_product_uom_id", store=True)
    product_qty = fields.Float(string="Quantity", default=1, required=True, digits="Product Unit")
    price_estimated = fields.Monetary(string="Estimated Unit Price", required=True, default=0)
    subtotal = fields.Monetary(compute="_compute_subtotal", store=True)

    _positive_quantity = models.Constraint("CHECK(product_qty > 0)", "Item quantity must be greater than zero.")
    _nonnegative_price = models.Constraint("CHECK(price_estimated >= 0)", "Estimated price cannot be negative.")
```

`request_id` adalah pasangan dari `line_ids`. Dengan `ondelete="cascade"`, baris ikut dihapus ketika permintaan induk boleh dihapus. Izin menghapus induk tetap diperiksa di `unlink()` milik permintaan.

`name` mengambil nama produk sebagai awal dan dapat diedit sebagai deskripsi. `product_uom_id` dihitung dari satuan produk, sehingga pengguna tidak memasukkan satuan berbeda melalui field manual. Perusahaan dan mata uang baris mengikuti induknya.

Lokasi: dalam `SupplyFlowRequestLine`, setelah deklarasi field. Tiga fungsi berikut lengkap sebagaimana source.


```python
    @api.depends("product_id")
    def _compute_name(self):
        for line in self:
            line.name = line.product_id.display_name
```


```python
    @api.depends("product_id")
    def _compute_product_uom_id(self):
        for line in self:
            line.product_uom_id = line.product_id.uom_id
```


```python
    @api.depends("product_qty", "price_estimated")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.product_qty * line.price_estimated
```

`@api.depends` menyatakan field pemicu perhitungan ulang. Ketika jumlah atau estimasi harga berubah, subtotal dihitung ulang. `store=True` pada field hasil membuat nilai hasilnya tersimpan.

Contoh angka latihan, bukan data bisnis nyata: 12 unit dengan estimasi harga 8,5 menghasilkan subtotal 102. Harga nol diperbolehkan karena pengguna mungkin belum mengetahui penawaran pemasok. Jumlah nol dan harga negatif ditolak.

Lokasi: dalam `SupplyFlowRequest`, setelah deklarasi field dan konstanta. Fungsi berikut menjumlahkan subtotal semua baris.


```python
    @api.depends("line_ids.subtotal")
    def _compute_amount_estimated(self):
        for request in self:
            total = sum(request.line_ids.mapped("subtotal"))
            try:
                rounded = request.currency_id.round(total)
            except (ValueError, OverflowError) as error:
                raise ValidationError(_("The estimated total is outside the currency's supported numeric range.")) from error
            if not math.isfinite(rounded):
                raise ValidationError(_("The estimated total must be finite."))
            request.amount_estimated = total
```

`mapped("subtotal")` mengambil nilai subtotal dari kumpulan baris. `currency_id.round(total)` dipakai untuk memastikan nilai dapat ditangani aturan mata uang. Bila penjumlahan terlalu besar atau menghasilkan angka tidak terhingga, model mengembalikan `ValidationError`.

Nilai `amount_estimated` yang disimpan tetap `total`, sesuai source. Jangan menyebutnya saldo anggaran, total faktur, atau realisasi pembayaran. Nilai ini hanya estimasi permintaan sebelum pajak.

### Validasi angka sebelum Odoo mengonversi field

Lokasi: `SupplyFlowRequestLine`, fungsi lengkap `_validate_numeric_input()`. Fungsi ini dipanggil oleh `create()` dan `write()` baris sebelum penyimpanan.


```python
    @api.model
    def _validate_numeric_input(self, quantity, price, unit, currency):
        try:
            quantity, price = float(quantity), float(price)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValidationError(_("Enter numeric quantities and estimated prices.")) from error
        if not all(math.isfinite(value) for value in (quantity, price, quantity * price)):
            raise ValidationError(_("Quantity and estimated price must be finite numbers."))
        if quantity <= 0:
            raise ValidationError(_("Item quantity must be greater than zero."))
        if price < 0:
            raise ValidationError(_("Estimated price cannot be negative."))
        if unit:
            try:
                is_positive = unit.compare(quantity, 0) > 0
            except (ValueError, OverflowError) as error:
                raise ValidationError(_("The quantity is outside the supported numeric range.")) from error
            if not is_positive:
                raise ValidationError(_("Item quantity must be greater than zero at the product's unit precision."))
        try:
            monetary_values = [currency.round(value) for value in (price, quantity * price)]
        except (ValueError, OverflowError) as error:
            raise ValidationError(_("The estimated price or subtotal is outside the currency's supported numeric range.")) from error
        if not all(math.isfinite(value) for value in monetary_values):
            raise ValidationError(_("Estimated price and subtotal must be finite."))
        return quantity, price
```

Urutan pemeriksaannya mempunyai tujuan berbeda:

1. Ubah masukan menjadi angka. Teks yang tidak bisa dikonversi mendapat pesan validasi.
2. Tolak `NaN`, tak terhingga, atau hasil perkalian yang tidak terhingga.
3. Pastikan jumlah positif dan harga tidak negatif.
4. Periksa jumlah memakai ketelitian satuan produk. Angka positif yang terlalu kecil hingga terbaca nol pada satuan produk tetap ditolak.
5. Pastikan harga dan subtotal dapat dibulatkan oleh mata uang. Angka yang masih finite dapat terlalu besar untuk operasi pembulatan tersebut.

Pemeriksaan sebelum `super().create()` atau `super().write()` mencegah nilai bermasalah mencapai konversi field atau SQL lebih dahulu.

Fungsi `_check_line_details()` kemudian memeriksa kembali angka, satuan, kelayakan produk, dan perusahaan setelah nilai berada pada record. Produk harus bisa dibeli (`purchase_ok`) dan dilacak stoknya (`is_storable`). Barang milik perusahaan lain tidak dapat dicampur. Constraint database untuk jumlah dan harga memberi lapisan tambahan, tetapi tidak menggantikan pesan validasi Python yang lebih spesifik.

## 4. Siapkan pemeriksaan bersama sebelum menyimpan dan mengganti status

Lokasi: kelas `SupplyFlowRequest`, sebelum `create()`. Bagian ini merupakan kumpulan fungsi lengkap yang dipakai bersama oleh action dan operasi penyimpanan.


```python
    @api.model
    def _require_group(self, group="supplyflow_office.group_user"):
        if not self.env.user.has_group(group):
            raise AccessError(_("You do not have the required SupplyFlow role."))
```


```python
    def _lock_for_change(self):
        self._require_group()
        self.check_access("write")
        self.flush_recordset()
        self.lock_for_update()
        self.invalidate_recordset()
        self.check_access("write")
```


```python
    def _require_requester(self):
        if any(request.requester_id != self.env.user for request in self):
            raise AccessError(_("Only the requester can edit or withdraw this requisition."))
```


```python
    def _require_independent_approver(self):
        self._require_group("supplyflow_office.group_approver")
        if any(
            self.env.user in (request.requester_id | request.create_uid)
            for request in self
        ):
            raise AccessError(_("Another approver must review your own requisition."))
```


```python
    def _require_draft(self):
        self._require_requester()
        if any(request.state != "draft" for request in self):
            raise UserError(_("Items and requisition details can only be edited in Draft."))
```

`_require_group()` memastikan pengguna memiliki peran SupplyFlow yang diperlukan. Hak membaca atau menulis record tetap diperiksa oleh Odoo. Pembatasan perusahaan pada [security/company_rules.xml](../../addons/supplyflow_office/security/company_rules.xml) bekerja bersama guard ini.

`_lock_for_change()` memeriksa akses, melakukan flush, mengunci record untuk perubahan, menghapus cache record, lalu memeriksa akses lagi. Action yang akan memutuskan status membaca data yang diperiksa setelah langkah ini. Dua permintaan HTTP yang berdekatan tidak cukup dilindungi dengan membuat tombol terlihat nonaktif di browser.

Penguncian dapat menghasilkan konflik transaksi ketika dua operasi bersaing. Jangan menganggap kedua klik selalu berhasil. Hasil yang hendak dijaga adalah satu konversi yang sah dan tidak ada RFQ kedua untuk permintaan yang sama. Uji HTTP konkurensi dicatat pada [VERIFICATION.md](../VERIFICATION.md).

`_require_independent_approver()` menolak pengguna yang sama dengan `requester_id` maupun `create_uid`. Jadi, pengguna yang punya peran Approver juga tetap perlu orang lain untuk meninjau permintaan buatannya sendiri.

`_require_draft()` menggabungkan dua syarat: pengguna adalah pengaju dan dokumen masih Draft. Pengguna SupplyFlow lain dalam perusahaan aktif dapat membaca sesuai ACL/rule, tetapi tidak mendapat hak mengubah draft milik orang lain dari guard ini.

### Bedakan validasi tersimpan dan bantuan pada form

`_check_request_details()` menolak alasan kosong, gudang dari perusahaan berbeda, serta pemasok yang secara khusus dimiliki perusahaan berbeda. Pemasok bersama, yang `company_id`-nya kosong, tetap dapat dipakai.

`_onchange_company_id()` memilih ulang default gudang ketika perusahaan di form berubah. Onchange membantu pengisian form; aturan server tetap diperlukan untuk operasi lewat API. Model ini tidak mengizinkan mengganti perusahaan permintaan tersimpan ke perusahaan lain. Buat permintaan baru jika perusahaan tujuannya berbeda.

## 5. Tulis `create()` dan `write()` dokumen induk

Lokasi: `SupplyFlowRequest`, setelah kumpulan guard. Sebelum fungsi tersebut, source menentukan field yang dilindungi dan field yang hanya bisa diedit saat Draft. Cuplikan konstanta berikut lengkap.


```python
    _AUDIT_FIELDS = frozenset({
        "name", "requester_id", "state", "purchase_order_id", "currency_id", "amount_estimated",
        "submitted_by_id", "submitted_at", "approved_by_id", "approved_at",
        "rejected_by_id", "rejected_at", "create_uid", "create_date", "write_uid", "write_date",
    })
    _DRAFT_FIELDS = frozenset({
        "company_id", "vendor_id", "warehouse_id", "requested_date", "purpose", "line_ids",
    })
```

`_AUDIT_FIELDS` mencakup status, identitas pengaju, total, jejak keputusan, dan tautan RFQ. `_DRAFT_FIELDS` mencakup isi permintaan yang ditinjau approver. Jika isinya berubah setelah diajukan, keputusan approver bisa mengacu pada data yang berbeda; karena itu field tersebut dibekukan sampai revisi Draft.

Fungsi lengkap `create()` berikut menghasilkan referensi otomatis dan memastikan dokumen baru selalu dimulai sebagai draft milik pengguna saat ini.

| Masukan fungsi | Keluaran jika berhasil | Contoh penolakan |
| --- | --- | --- |
| Daftar dictionary pemasok, gudang, tanggal, tujuan, dan baris barang | Recordset permintaan baru dengan nomor sequence, pengguna saat ini, dan status Draft | Pengaju palsu, perusahaan tidak aktif, atau status awal Approved |


```python
    @api.model_create_multi
    def create(self, vals_list):
        self._require_group()
        prepared = []
        for original in vals_list:
            values = dict(original)
            forbidden = self._AUDIT_FIELDS.intersection(values) - {"state", "requester_id", "name"}
            if forbidden or values.get("state", "draft") != "draft":
                raise AccessError(_("Approval, audit and RFQ fields are set by workflow actions."))
            if values.get("requester_id", self.env.uid) != self.env.uid:
                raise AccessError(_("Create requisitions under your own user account."))
            if values.get("name", "New") not in (False, "New"):
                raise AccessError(_("The requisition reference is assigned automatically."))
            company_id = values.get("company_id", self.env.company.id)
            if company_id not in self.env.companies.ids:
                raise AccessError(_("This company is not in your active companies."))
            company = self.env["res.company"].browse(company_id)
            reference = self.env["ir.sequence"].with_company(company).next_by_code("supplyflow.request")
            if not reference:
                raise UserError(_("The purchase requisition sequence is missing. Update SupplyFlow Office."))
            values.update({
                "name": reference, "company_id": company_id, "requester_id": self.env.uid,
                "state": "draft", "purchase_order_id": False, "decision_reason": False,
                "submitted_by_id": False, "submitted_at": False,
                "approved_by_id": False, "approved_at": False,
                "rejected_by_id": False, "rejected_at": False,
            })
            prepared.append(values)
        safe_context = {
            key: value for key, value in self.env.context.items()
            if key not in {f"default_{field}" for field in self._AUDIT_FIELDS}
        }
        return super(SupplyFlowRequest, self.with_context(safe_context)).create(prepared)
```

`@api.model_create_multi` menerima daftar dictionary agar operasi membuat beberapa record tetap mendapat pemeriksaan yang sama. `dict(original)` membuat salinan nilai masukan sebelum kode menambah atau menormalkannya.

Perhatikan beberapa keputusan di dalamnya:

- Nilai seperti `approved_by_id` ditolak jika dikirim langsung. Status awal selain `draft` juga ditolak.
- Pengaju tidak boleh mengatasnamakan pengguna lain dan nomor tidak boleh ditentukan manual.
- Perusahaan yang dipilih harus berada dalam perusahaan aktif pengguna.
- Nomor didapat dari `ir.sequence` dengan perusahaan yang sesuai. Sequence yang tidak tersedia menghasilkan pesan kesalahan, bukan nomor acak pengganti.
- Jejak persetujuan dan hubungan RFQ dikosongkan secara eksplisit.
- Key context seperti `default_state` atau `default_approved_by_id` dibuang untuk field yang dilindungi sebelum meneruskan create ke Odoo.

Default context juga merupakan masukan. Memeriksa `values` saja belum cukup apabila Odoo masih boleh mengambil default dari context setelahnya.

Fungsi lengkap `write()` berikut mengatur perubahan pada dokumen yang sudah ada.

| Masukan fungsi | Keluaran jika berhasil | Contoh penolakan |
| --- | --- | --- |
| Recordset dan dictionary perubahan | Nilai tersimpan setelah guard; hasil dari `super().write()` | Pengguna lain mengedit draft atau pengaju mengubah jumlah setelah Submit |


```python
    def write(self, values):
        self._lock_for_change()
        if self._AUDIT_FIELDS.intersection(values):
            raise AccessError(_("Approval, audit and RFQ fields are set by workflow actions."))
        if self._DRAFT_FIELDS.intersection(values):
            self._require_draft()
        if "company_id" in values and any(request.company_id.id != values["company_id"] for request in self):
            raise UserError(_("Create a new requisition to use another company."))
        if "decision_reason" in values:
            self._require_independent_approver()
            if any(request.state != "submitted" for request in self):
                raise UserError(_("Decision notes can only be entered while awaiting approval."))
        return super().write(values)
```

Semua penulisan lewat fungsi ini diawali guard dan lock. Penulisan langsung status, pengaju, field audit, total, atau tautan RFQ ditolak. Perubahan isi memerlukan draft milik pengaju.

`decision_reason` mempunyai aturan tersendiri: hanya approver independen dan hanya selama status `submitted`. Inilah alasan catatan keputusan tidak dimasukkan begitu saja ke daftar field editable Draft.

Untuk `unlink()`, source memanggil `_lock_for_change()` lalu `_require_draft()` sebelum `super().unlink()`. Akibatnya pengguna hanya dapat menghapus draft miliknya. Dokumen yang sudah diajukan perlu diselesaikan lewat workflow.

## 6. Bangun perpindahan status satu per satu

Urutan utama:

```text
Draft -> Awaiting Approval -> Approved -> RFQ Created
                         -> Rejected -> Draft (revisi lalu ajukan lagi)
```

`Cancelled` dapat dicapai melalui aturan pembatalan yang dijelaskan di bawah. Menyimpan `state="approved"` lewat `write()` bukan jalur perpindahan status yang didukung.

Lokasi: `SupplyFlowRequest`, setelah operasi CRUD. Fungsi lengkap `_transition()` menyediakan jalur internal yang dipakai action setelah guard dan validasi.


```python
    def _transition(self, values):
        # Only private, validated actions use this path; RPC context flags cannot unlock it.
        return super().write(values)
```

`super().write(values)` di helper internal ini melewati override `write()` pada kelas yang sama, sehingga action dapat mengisi field audit yang memang ditolak pada penulisan biasa. Karena itu pemanggilnya wajib sudah memeriksa pengguna, status, dan data. Jangan menambahkan flag context publik seperti `skip_approval=True` untuk membuka jalur tersebut.

### Ajukan permintaan

Fungsi lengkap `action_submit()` dipanggil tombol **Submit for Approval**.


```python
    def action_submit(self):
        self._lock_for_change()
        self._require_draft()
        for request in self:
            if not request.line_ids:
                raise UserError(_("Add at least one item before submitting."))
            request._check_request_details()
            request.line_ids._check_line_details()
            request._check_company()
        self._transition({
            "state": "submitted", "submitted_by_id": self.env.uid,
            "submitted_at": fields.Datetime.now(), "decision_reason": False,
        })
        for request in self:
            request.message_post(body=_("Submitted for independent review."))
        return True
```

Kodenya menolak pengaju yang salah, status selain draft, dan permintaan tanpa barang. Detail induk, setiap baris, serta kecocokan perusahaan diperiksa lagi sebelum status berubah. `submitted_by_id` dan `submitted_at` berasal dari lingkungan server. `message_post()` menambahkan catatan ke chatter.

### Setujui oleh pengguna lain

Fungsi lengkap `action_approve()` berikut hanya menerima permintaan yang sedang menunggu persetujuan.


```python
    def action_approve(self):
        self._lock_for_change()
        self._require_independent_approver()
        if any(request.state != "submitted" for request in self):
            raise UserError(_("Only submitted requisitions can be approved."))
        self._transition({
            "state": "approved", "approved_by_id": self.env.uid,
            "approved_at": fields.Datetime.now(),
        })
        for request in self:
            request.message_post(body=_("Approved. Decision note: %s", request.decision_reason or "No note supplied."))
        return True
```

Setelah disetujui, barang belum dibeli dan stok belum bertambah. Status ini hanya membuat dokumen layak dikonversi menjadi RFQ.

### Tolak dengan alasan

Fungsi lengkap `action_reject()` membutuhkan catatan keputusan yang sudah diisi approver.


```python
    def action_reject(self):
        self._lock_for_change()
        self._require_independent_approver()
        if any(request.state != "submitted" for request in self):
            raise UserError(_("Only submitted requisitions can be rejected."))
        if any(not (request.decision_reason or "").strip() for request in self):
            raise UserError(_("Enter a decision note explaining the rejection."))
        self._transition({
            "state": "rejected", "rejected_by_id": self.env.uid,
            "rejected_at": fields.Datetime.now(),
        })
        for request in self:
            request.message_post(body=_("Rejected: %s", request.decision_reason))
        return True
```

Approver mengisi `decision_reason` melalui `write()` yang tadi dijaga, lalu menjalankan action ini. Spasi saja tetap dianggap kosong. Penyimpanan alasan serta pencatatan penolakannya memakai transaksi operasi Odoo yang sedang berjalan.

### Kembalikan ke Draft untuk revisi

Fungsi lengkap `action_reset_draft()` dipakai oleh pengaju setelah penolakan.


```python
    def action_reset_draft(self):
        self._lock_for_change()
        self._require_requester()
        if any(request.state != "rejected" for request in self):
            raise UserError(_("Only rejected requisitions can return to Draft."))
        self._transition({
            "state": "draft", "decision_reason": False,
            "submitted_by_id": False, "submitted_at": False,
            "approved_by_id": False, "approved_at": False,
            "rejected_by_id": False, "rejected_at": False,
        })
        for request in self:
            request.message_post(body=_("Returned to Draft for revision; previous decisions remain in the chatter."))
        return True
```

Field keputusan aktif dikosongkan karena data berikutnya akan diajukan sebagai revisi. Pesan keputusan sebelumnya tetap ada pada chatter, sebagaimana diperiksa tes. Mengubah jumlah pada permintaan `rejected` langsung tetap ditolak; pengaju menekan **Revise Draft**, mengedit, lalu mengajukan ulang. Revisi tersebut memerlukan persetujuan baru sebelum RFQ.

### Batalkan sesuai status dan pelakunya

`action_cancel()` memakai guard yang sama, kemudian menerapkan aturan berikut:

| Status sebelum pembatalan | Pengguna yang boleh membatalkan | Tombol form |
| --- | --- | --- |
| `draft`, `submitted`, `rejected` | Pengaju dokumen | Withdraw |
| `approved` | Approver independen | Cancel Approval |
| `rfq_created`, `cancelled` | Ditolak oleh action ini | Kelola RFQ yang sudah ada melalui Purchase |

Pembatalan persetujuan tidak mensyaratkan alasan tambahan pada implementasi ini. Identitas pelaku dicatat ke chatter. Membatalkan dokumen SupplyFlow setelah RFQ tercipta tidak disediakan, karena RFQ sudah menjadi transaksi native dengan aturan pembatalannya sendiri.

## 7. Ubah permintaan yang disetujui menjadi RFQ native

Lokasi: `SupplyFlowRequest`, fungsi lengkap `action_create_rfq()`. Bagian ini menghubungkan addon ke aplikasi Purchase.

| Masukan fungsi | Keluaran jika berhasil | Contoh penolakan |
| --- | --- | --- |
| Satu permintaan yang disetujui dan pengguna dengan peran serta izin Purchase | Satu RFQ native tertaut dan dictionary pembuka form; pemanggilan berikutnya membuka RFQ yang sama | Draft belum disetujui atau pelaku tidak memiliki izin membuat pembelian |


```python
    def action_create_rfq(self):
        self.ensure_one()
        self._lock_for_change()
        self._require_group("supplyflow_office.group_approver")
        if self.purchase_order_id:
            self.purchase_order_id.check_access("read")
            return self._rfq_action()
        if self.state != "approved":
            raise UserError(_("Approve this requisition before creating an RFQ."))
        self._check_request_details()
        self.line_ids._check_line_details()
        self._check_company()
        self.vendor_id.check_access("read")
        self.warehouse_id.check_access("read")
        self.line_ids.product_id.check_access("read")
        order = self.env["purchase.order"].with_company(self.company_id).create({
            "partner_id": self.vendor_id.id,
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "picking_type_id": self.warehouse_id.in_type_id.id,
            "origin": self.name,
            "user_id": self.env.uid,
            "state": "draft",
            "locked": False,
            "order_line": [fields.Command.create({
                "product_id": line.product_id.id,
                "name": line.name,
                "product_uom_id": line.product_uom_id.id,
                "product_qty": line.product_qty,
                "price_unit": line.price_estimated,
                "date_planned": datetime.combine(self.requested_date, time(hour=12)),
            }) for line in self.line_ids],
        })
        order.order_line._compute_tax_id()
        # Native vendor computations can replace input prices, including an intentional zero estimate.
        for requested, purchased in zip(self.line_ids, order.order_line):
            purchased.write({
                "name": requested.name,
                "price_unit": requested.price_estimated,
                "technical_price_unit": requested.price_estimated,
                "date_planned": datetime.combine(self.requested_date, time(hour=12)),
            })
        self._transition({"state": "rfq_created", "purchase_order_id": order.id})
        self.message_post(body=_("RFQ %s created. Review vendor prices and taxes in Purchase before confirmation.", order.name))
        return self._rfq_action()
```

Baca fungsi tersebut menurut urutan operasinya:

1. `ensure_one()` menuntut satu permintaan. Konversi ini tidak memproses kumpulan dokumen sekaligus.
2. Perubahan dikunci dan pelaku memerlukan peran Approver. Hak native untuk membuat Purchase Order tetap diperlukan karena kode tidak menggunakan `sudo()` pada pembuatannya.
3. Bila sudah ada `purchase_order_id`, kode memeriksa akses baca RFQ dan membuka dokumen itu. Inilah perilaku idempotent: menjalankan konversi lagi tidak membuat pembelian kedua.
4. Tanpa RFQ yang ada, status wajib `approved`. Data dan hak baca pemasok, gudang, serta produk diperiksa ulang.
5. `purchase.order` dibuat dengan perusahaan, pemasok, mata uang, dan incoming picking type milik gudang permintaan. `origin` menyimpan nomor permintaan agar operator dapat menelusuri sumbernya.
6. Setiap baris menjadi `fields.Command.create(...)` untuk `purchase.order.line`. Pada Odoo 19 yang dipakai proyek, field satuan baris PO adalah `product_uom_id`.
7. Kode meminta kalkulasi pajak native, lalu mengembalikan deskripsi, estimasi harga, technical price, dan tanggal yang bersumber dari permintaan. Perhitungan native pemasok dapat mengganti harga masukan, termasuk estimasi nol, sehingga bagian penulisan ulang ini diuji khusus.
8. Setelah berhasil, permintaan menyimpan tautan RFQ, berganti `rfq_created`, dan menambahkan pesan. Fungsi mengembalikan action untuk membuka form Purchase.

Tanggal rencana pada source dibentuk dari `requested_date` dengan jam 12. Kebijakan ini ada pada contoh proyek; sesuaikan bila kebutuhan bisnis kelak memerlukan waktu penerimaan yang lebih rinci.

Lokasi: setelah `action_create_rfq()`, fungsi lengkap `_rfq_action()` menghasilkan instruksi tampilan ke web client.


```python
    def _rfq_action(self):
        return {
            "type": "ir.actions.act_window", "name": _("Request for Quotation"),
            "res_model": "purchase.order", "view_mode": "form",
            "res_id": self.purchase_order_id.id, "target": "current",
        }
```

Dictionary tersebut meminta Odoo membuka form `purchase.order` dengan ID RFQ terkait pada jendela saat ini. Dictionary ini tidak memindahkan barang.

RFQ yang dibuat masih `draft`. Operator harus memeriksa harga, pajak, dan syarat pemasok dalam Purchase, mengonfirmasi pembelian, lalu memproses receipt. Stok bertambah melalui validasi penerimaan barang oleh proses Inventory. Membuat permintaan, menyetujuinya, atau membuat RFQ belum menambah stok.

Batas kebijakan juga perlu dipahami: persetujuan ini mengatur dokumen SupplyFlow. Pengguna yang memiliki hak native Purchase dapat tetap membuat RFQ langsung melalui aplikasi Purchase. Addon ini belum menjadikan persetujuan SupplyFlow sebagai gerbang wajib untuk semua pembelian native.

## 8. Jaga setiap jalur edit baris barang

Form induk yang readonly belum melindungi model baris dari pemanggilan langsung. Karena itu `SupplyFlowRequestLine` juga memiliki `create()`, `write()`, dan `unlink()` sendiri.

Lokasi: kelas `SupplyFlowRequestLine`, setelah validator angka. Fungsi lengkap `create()` berikut memeriksa induk sebelum menambahkan baris.


```python
    @api.model_create_multi
    def create(self, vals_list):
        self.env["supplyflow.request"]._require_group()
        defaults = self.default_get(["product_id", "product_qty", "price_estimated"])
        prepared = []
        for original in vals_list:
            values = dict(original)
            if {"company_id", "currency_id", "subtotal", "product_uom_id", "create_uid", "create_date", "write_uid", "write_date"}.intersection(values):
                raise AccessError(_("Item company, unit and totals are assigned automatically."))
            request_id = values.get("request_id", self.env.context.get("default_request_id"))
            if not request_id:
                raise ValidationError(_("An item must belong to a requisition."))
            request = self.env["supplyflow.request"].browse(request_id)
            request._lock_for_change()
            request._require_draft()
            values["request_id"] = request_id
            product = self.env["product.product"].browse(values.get("product_id", defaults.get("product_id")))
            values["product_qty"], values["price_estimated"] = self._validate_numeric_input(
                values.get("product_qty", defaults.get("product_qty", 1)),
                values.get("price_estimated", defaults.get("price_estimated", 0)),
                product.uom_id, request.currency_id,
            )
            prepared.append(values)
        protected_defaults = {
            f"default_{field}" for field in (
                "company_id", "currency_id", "subtotal", "product_uom_id",
                "create_uid", "create_date", "write_uid", "write_date",
            )
        }
        safe_context = {key: value for key, value in self.env.context.items() if key not in protected_defaults}
        return super(SupplyFlowRequestLine, self.with_context(safe_context)).create(prepared)
```

Kode mengambil `request_id` dari nilai eksplisit atau default context, memastikan ada induknya, lalu mengunci induk dan memeriksa draft milik pengaju. Satuan, total, perusahaan, serta metadata audit tidak boleh ditentukan langsung oleh pemanggil. Default context untuk field tersebut juga disaring.

`default_get()` mengambil default produk, jumlah, dan harga yang memang dipakai untuk input barang. Default angka tetap melewati `_validate_numeric_input()`; keberadaan kata default tidak membuatnya otomatis dipercaya.

Fungsi lengkap `write()` berikut mencegah baris dipindahkan ke permintaan lain dan memeriksa angka baru terhadap produk serta mata uang yang benar.


```python
    def write(self, values):
        self.check_access("write")
        requests = self.mapped("request_id")
        requests._lock_for_change()
        requests._require_draft()
        if {"request_id", "company_id", "currency_id", "subtotal", "product_uom_id", "create_uid", "create_date", "write_uid", "write_date"}.intersection(values):
            raise AccessError(_("Items cannot be moved between requisitions or assigned manual totals or units."))
        for line in self:
            unit = self.env["product.product"].browse(values["product_id"]).uom_id if "product_id" in values else line.product_uom_id
            line._validate_numeric_input(
                values.get("product_qty", line.product_qty),
                values.get("price_estimated", line.price_estimated), unit, line.currency_id,
            )
        return super().write(values)
```

Jika `product_id` ikut berubah, pemeriksaan menggunakan satuan produk baru. Bila tidak, satuan dari baris saat ini dipakai. Pemeriksaan jumlah dan harga melihat kombinasi nilai yang akan terbentuk, bukan hanya angka yang kebetulan dikirim pada panggilan tersebut.

Fungsi lengkap `unlink()` memeriksa hak hapus baris dan kondisi induknya.


```python
    def unlink(self):
        self.check_access("unlink")
        requests = self.mapped("request_id")
        requests._lock_for_change()
        requests._require_draft()
        return super().unlink()
```

Ketiga operasi tersebut menutup jalur terpisah: menambah barang ke permintaan yang sudah diajukan, mengubah jumlah melalui model baris langsung, menghapus barang sesudah review, serta memindahkan baris agar lolos aturan induk.

## 9. Hubungkan fungsi ke form XML

Sumber tampilan: [views/purchase_request_views.xml](../../addons/supplyflow_office/views/purchase_request_views.xml). Cuplikan berikut adalah dua elemen tombol utuh dari bagian `<header>` form; ini bukan seluruh file XML.

```xml
                    <button name="action_submit" string="Submit for Approval" type="object" class="oe_highlight" invisible="state != 'draft' or requester_id != uid"/>
                    <button name="action_approve" string="Approve" type="object" class="oe_highlight" groups="supplyflow_office.group_approver" invisible="state != 'submitted' or requester_id == uid"/>
```

`type="object"` menghubungkan klik tombol dengan method model pada field `name`. `groups` membatasi penampilan berdasarkan grup. `invisible` mengatur kapan tombol tampil sesuai status dan pengguna.

Tombol Approve disembunyikan dari pengaju, sedangkan `_require_independent_approver()` di server juga memeriksa pembuat record. Pemeriksaan server tetap menjadi batas penolakan ketika fungsi dipanggil tanpa melalui tombol.

Di bagian Requested Items, XML menampilkan `line_ids` sebagai daftar yang dapat diedit saat draft. Domain produk menyaring produk yang dapat dibeli dan dilacak stoknya. Validasi model tetap diperlukan karena domain hanyalah pilihan yang disediakan UI.

`action_requests` pada akhir file adalah `ir.actions.act_window` dengan `res_model` yang sama dan `view_mode="list,form"`. Menu mengarahkan pengguna ke action tersebut. Penjelasan view, menu, ACL, dan report secara menyeluruh dilanjutkan pada bab antarmuka dan keamanan tutorial ini.

## 10. Uji satu alur melalui akun latihan

Gunakan repo lengkap dan database latihan lokal. Hindari memakai data perusahaan nyata saat mencoba penolakan, pembatalan, atau perubahan jumlah.

1. Dari folder proyek, jalankan `./scripts/Start.ps1 -WithTrainingData -SkipPull` bila image sudah tersedia. Untuk mesin yang belum mengunduh image, gunakan `./scripts/Start.ps1 -WithTrainingData`. Buka `http://localhost:8070` dan baca kredensial lokal dari `.secrets/LOCAL-CREDENTIALS.txt`.
2. Masuk sebagai `buyer`. Buka **SupplyFlow Office > Purchase requests**, buat permintaan baru, pilih pemasok dan gudang dengan awalan `[Training]`, lalu isi tujuan pembelian.
3. Tambah produk latihan yang dilacak stok, isi jumlah 12 dan estimasi harga 8,5. Pastikan subtotal dan total menjadi 102 dalam mata uang perusahaan. Angka ini contoh hitungan, bukan rekomendasi harga barang.
4. Simpan, lalu pilih **Submit for Approval**. Pastikan status menjadi Awaiting Approval dan isi barang tidak dapat diedit lagi.
5. Gunakan browser atau profil terpisah untuk masuk sebagai `approver`. Buka permintaan dari buyer. Isi catatan keputusan jika diperlukan, lalu pilih **Approve**.
6. Pilih **Create RFQ**. Pastikan form Purchase terbuka dan pemasok, jumlah, satuan, gudang tujuan, serta harga awal sesuai permintaan. Tinjau harga dan pajak sebelum mengonfirmasi pembelian.
7. Kembali ke permintaan, pilih **Open RFQ**. ID atau nomor RFQ yang dibuka harus tetap sama. Pada tahap ini pembuatan RFQ saja belum mengubah stok.
8. Buat permintaan latihan kedua untuk jalur penolakan. Ajukan sebagai buyer, isi alasan lalu Reject sebagai approver. Buyer menekan **Revise Draft**, mengubah jumlah, dan mengajukan ulang. Periksa bahwa persetujuan baru tetap diperlukan serta alasan sebelumnya terlihat di chatter.

Jangan menggunakan satu akun untuk seluruh latihan persetujuan. Server akan menolak approver yang mencoba menyetujui permintaannya sendiri.

### Cocokkan perilaku dengan tes yang sudah dibuat

Sumber: [tests/test_purchase_request.py](../../addons/supplyflow_office/tests/test_purchase_request.py). File ini berisi 17 method tes. Tabel berikut memberi titik baca untuk keputusan utama, bukan hasil menjalankan ulang tes saat membaca tutorial.

| Yang hendak dipahami | Method tes |
| --- | --- |
| Data permintaan masuk ke RFQ pada perusahaan/gudang yang benar | `test_request_to_native_rfq_uses_company_warehouse_and_estimate` |
| Klik konversi kedua membuka RFQ yang sama | `test_rfq_conversion_is_idempotent` |
| Estimasi nol tetap dipertahankan saat vendor mempunyai harga | `test_rfq_preserves_estimate_even_when_vendor_prices_are_configured` |
| Pengguna tidak boleh menyetujui permintaan sendiri | `test_approval_needs_an_independent_reviewer` |
| Penolakan, revisi, chatter, dan persetujuan ulang | `test_reject_and_revision_preserve_chatter_then_require_new_approval` |
| Manipulasi status/audit/link melalui `write` ditolak | `test_direct_state_audit_and_link_changes_are_blocked` |
| Default context tidak dapat memalsukan persetujuan | `test_context_defaults_cannot_forge_approval_or_link` |
| Semua jalur mutasi baris dibekukan setelah submit | `test_submitted_parent_and_every_line_mutation_path_are_frozen` |
| Peran SupplyFlow tidak menggantikan izin native Purchase | `test_standard_purchase_rights_are_still_required` |
| Nilai angka bermasalah ditolak sebelum konversi field | `test_numeric_edits_are_validated_before_database_conversion` |

Tes lain dalam file itu mencakup perusahaan, produk non-stok, edit draft pengguna lain, langkah status yang tidak sah, pembatalan persetujuan, dan pengguna tanpa peran. Alur penerimaan dan perubahan stok yang sesungguhnya terdapat dalam [tests/test_distribution_flow.py](../../addons/supplyflow_office/tests/test_distribution_flow.py).

Untuk menjalankan paket tes ORM proyek dari PowerShell, gunakan `./scripts/Test.ps1 -SkipPull`. Script ini menghentikan layanan aplikasi proyek untuk pengujian, menggunakan database tes terpisah, lalu membersihkan database tes sesuai opsi script. Setelah selesai, nyalakan kembali dengan `./scripts/Start.ps1 -SkipPull` bila perlu. Ikuti [OPERATIONS.md](../OPERATIONS.md) untuk detail operasional.

## Peta fungsi yang belum dikutip utuh

Seluruh implementasi tetap berada pada [purchase_request.py](../../addons/supplyflow_office/models/purchase_request.py). Lima fungsi berikut dijelaskan di bab ini tanpa menyalin seluruh isinya:

| Kelas | Fungsi | Letak saat menyusun file | Tujuan |
| --- | --- | --- | --- |
| `SupplyFlowRequest` | `_onchange_company_id` | Setelah perhitungan total | Mengisi ulang pilihan default gudang pada form |
| `SupplyFlowRequest` | `_check_request_details` | Setelah onchange | Menolak alasan kosong dan relasi lintas perusahaan yang tidak sesuai |
| `SupplyFlowRequest` | `unlink` | Setelah `write` | Menghapus hanya draft milik pengaju setelah guard dan lock |
| `SupplyFlowRequest` | `action_cancel` | Setelah aksi revisi dan sebelum konversi RFQ | Menentukan pelaku pembatalan menurut status dan mencatatnya ke chatter |
| `SupplyFlowRequestLine` | `_check_line_details` | Setelah perhitungan subtotal | Memeriksa angka, ketelitian satuan, kelayakan produk, dan perusahaan pada record |

## Kesalahan yang sering membuat implementasi berbeda dari tujuan

| Kesalahan | Dampak | Periksa bagian ini |
| --- | --- | --- |
| Hanya mengunci input atau menyembunyikan tombol di XML | Operasi langsung ke model dapat melewati aturan tampilan | Guard Python serta override `create`, `write`, `unlink` |
| Memberi semua pengguna `sudo()` saat membuat PO | Izin native Purchase tidak lagi menjadi batas operasi tersebut | `action_create_rfq` dan tes hak native |
| Menjaga induk tetapi membiarkan model baris bebas diedit | Jumlah barang bisa berubah setelah approver meninjau | Ketiga operasi CRUD pada `SupplyFlowRequestLine` |
| Memercayai `default_state` atau `default_approved_by_id` dari context | Record baru dapat menerima default yang tidak semestinya | Penyaringan default dan pengisian audit pada `create` |
| Memanggil `write({"state": "approved"})` dari tombol | Override `write` menolak perubahan audit langsung | Action tervalidasi dan `_transition` internal |
| Membuat PO tanpa mengecek `purchase_order_id` yang sudah ada | Percobaan berulang dapat menggandakan transaksi | Guard, lock, dan jalur membuka RFQ yang sama |
| Menganggap harga estimasi sudah merupakan harga pemasok dan pajak final | Operator melewati peninjauan Purchase | Catatan RFQ dan pemeriksaan sebelum konfirmasi |
| Menganggap RFQ yang tercipta otomatis menambah barang | Jumlah stok yang diharapkan tidak sesuai proses Inventory | Receipt dan validasi transfer native |
| Menggunakan nama field dari versi Odoo berbeda | Pembuatan PO bisa gagal dengan field tidak dikenal | Source proyek Odoo 19, khususnya `product_uom_id` pada baris PO |

Pada akhir bab ini, telusuri satu klik **Create RFQ** dari tombol XML ke `action_create_rfq()`, pembuatan `purchase.order`, penyimpanan `purchase_order_id`, lalu action pembuka form. Jika urutan tersebut sudah jelas, kamu dapat menjelaskan hubungan kode addon dengan proses Purchase tanpa menganggap setiap langkah ERP ditulis ulang sendiri.
