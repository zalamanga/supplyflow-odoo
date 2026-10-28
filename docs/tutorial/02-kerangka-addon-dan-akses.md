# 2. Kerangka addon dan hak akses

Hasil bab ini: addon minimal terpasang, mempunyai model permintaan, dan membuka daftar kosong dari menu. Belum ada pengajuan, persetujuan, RFQ, baris produk, atau retur. Tujuan tahap ini adalah memahami cara Odoo menemukan Python dan XML sebelum menambahkan aturan bisnis.

Semua contoh berlabel **starter** pada bab ini hanya untuk folder latihan bab 1. Jangan menimpa addon lengkap di folder proyek utama. Kode starter berikut adalah isi lengkap setiap file yang disebutkan.

## 2.1 Susun folder addon

Di `D:\Latihan-Odoo\supplyflow-office`, buat struktur berikut:

```text
addons/
  supplyflow_office/
    __init__.py
    __manifest__.py
    models/
      __init__.py
      purchase_request.py
    security/
      groups.xml
      ir.model.access.csv
      company_rules.xml
    views/
      purchase_request_views.xml
      menus.xml
```

Nama teknis folder `supplyflow_office` harus sama dengan nama yang dipasang oleh `manage.py`. Nama yang tampil di layar dapat berbeda, tetapi namespace XML dan nama modul harus konsisten.

## 2.2 Daftarkan addon melalui manifest

Isi starter `addons/supplyflow_office/__manifest__.py`:

```python
{
    "name": "SupplyFlow Office",
    "summary": "Kerangka latihan permintaan perlengkapan kantor",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["purchase_stock", "sale_stock", "mail"],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "security/company_rules.xml",
        "views/purchase_request_views.xml",
        "views/menus.xml",
    ],
    "application": True,
    "installable": True,
}
```

Manifest adalah dictionary Python yang dibaca loader Odoo. `depends` meminta modul dasar dipasang lebih dahulu. `data` menentukan urutan XML/CSV: grup sebelum ACL yang menunjuk grup, view sebelum menu yang menunjuk action. Pada tahap ini belum ada `assets`, report, atau file kasus pemasok karena file tersebut belum dibuat.

Bandingkan dengan [manifest final](../../addons/supplyflow_office/__manifest__.py) setelah seluruh bab selesai. Jangan menggunakan daftar file final sementara file yang dirujuk belum ada.

## 2.3 Hubungkan import Python

Isi lengkap starter `addons/supplyflow_office/__init__.py`:

```python
from . import models
```

Isi lengkap starter `addons/supplyflow_office/models/__init__.py`:

```python
from . import purchase_request
```

Titik pada `from .` berarti import relatif di dalam package. File Python yang tidak diimpor tidak otomatis menjadi model aktif hanya karena disimpan di folder `models`.

Rantai pemuatannya:

```text
Odoo membaca __manifest__.py
  -> mengimpor package supplyflow_office
  -> __init__.py mengimpor models
  -> models/__init__.py mengimpor purchase_request
  -> class model didaftarkan
  -> loader membaca data XML/CSV sesuai manifest
```

## 2.4 Tulis model pertama

Isi lengkap starter `addons/supplyflow_office/models/purchase_request.py`:

```python
from odoo import fields, models


class SupplyFlowRequest(models.Model):
    _name = "supplyflow.request"
    _description = "SupplyFlow learning request"
    _check_company_auto = True

    name = fields.Char(required=True, default="New")
    company_id = fields.Many2one(
        "res.company", required=True,
        default=lambda self: self.env.company,
    )
    purpose = fields.Text(string="Purpose")
```

`class` mengelompokkan definisi model. `models.Model` memberi perilaku ORM Odoo. `_name` adalah nama teknis model yang dipakai pada XML, ACL, dan `env["supplyflow.request"]`. Secara bawaan, ORM memetakan model ini ke tabel `supplyflow_request`.

`fields.Char` menampung teks pendek. `fields.Text` menampung uraian. `fields.Many2one("res.company")` menghubungkan satu permintaan ke satu perusahaan. Database menyimpan referensi record, bukan menyalin seluruh perusahaan ke setiap permintaan.

`self` adalah recordset tempat method berjalan. `self.env` menyediakan model lain, pengguna, context, perusahaan, dan cursor transaksi. `lambda self: self.env.company` dievaluasi sebagai default ketika record dibuat, sehingga tidak mengunci perusahaan tertentu pada waktu file Python diimpor.

`_check_company_auto` membantu pemeriksaan relasi yang memakai `check_company=True`. Ia bukan pengganti record rule atau pemeriksaan perusahaan pada aturan bisnis.

Pada checkpoint kerangka ini, kita belum membuat transaksi. Ini mencegah record percobaan yang belum mempunyai field wajib final mengganggu upgrade tahap berikutnya.

## 2.5 Buat kelompok pengguna

Isi lengkap starter `security/groups.xml`, sama dengan [source final](../../addons/supplyflow_office/security/groups.xml):

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="privilege_supplyflow" model="res.groups.privilege">
        <field name="name">SupplyFlow Office</field>
        <field name="category_id" ref="base.module_category_supply_chain"/>
        <field name="sequence">25</field>
    </record>
    <record id="group_user" model="res.groups">
        <field name="name">Requester</field>
        <field name="privilege_id" ref="privilege_supplyflow"/>
        <field name="sequence">10</field>
        <field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
    </record>
    <record id="group_approver" model="res.groups">
        <field name="name">Approver</field>
        <field name="privilege_id" ref="privilege_supplyflow"/>
        <field name="sequence">20</field>
        <field name="implied_ids" eval="[(4, ref('group_user'))]"/>
        <field name="user_ids" eval="[(4, ref('base.user_admin'))]"/>
    </record>
</odoo>
```

`record` membuat atau memperbarui record konfigurasi. `id="group_user"` membentuk external ID `supplyflow_office.group_user`, yang stabil untuk rujukan antarfile. `ref` mencari external ID lain, bukan angka ID database yang dapat berbeda antarinstalasi.

`implied_ids` berarti anggota Approver juga mendapat Requester. Command `(4, id)` menambahkan relasi tanpa mengganti semua relasi yang sudah ada. Ini sama keluarga konsepnya dengan `Command.link(id)` pada kode Python.

`group_approver` sudah disediakan pada starter karena script konfigurasi pertama mencari external ID tersebut. Izin grup native Purchase dan Inventory tetap merupakan pengaturan terpisah.

## 2.6 ACL: boleh melakukan operasi apa?

Isi lengkap starter `security/ir.model.access.csv`:

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_request_user,SupplyFlow request,model_supplyflow_request,group_user,1,0,0,0
```

Baris ini memberikan **read saja** untuk anggota Requester. Hak create/write/unlink sengaja belum dibuka pada kerangka. Administrator tetap memiliki kemampuan administratif lebih luas, sehingga view juga menyembunyikan pembuatan record pada checkpoint ini.

`model_supplyflow_request` adalah external ID model yang dibentuk Odoo dari `_name`. Empat kolom terakhir berarti baca, ubah, buat, dan hapus. Nilai ACL bersifat pemberian hak; angka nol pada satu baris tidak mencabut hak yang diberikan grup lain.

ACL final mempunyai empat model dan memberikan operasi kepada anggota addon. Pembatasan status/pemilik dilakukan lagi di method Python. Jangan menyalin ACL final empat baris sebelum model baris dan kasus terkait sudah terdaftar.

## 2.7 Record rule: record mana yang boleh terlihat?

Isi lengkap starter `security/company_rules.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="request_company_rule" model="ir.rule">
        <field name="name">SupplyFlow request company isolation</field>
        <field name="model_id" ref="model_supplyflow_request"/>
        <field name="domain_force">[('company_id', 'in', company_ids)]</field>
    </record>
</odoo>
```

Domain adalah daftar kondisi pencarian. `company_ids` pada evaluasi rule mengikuti perusahaan aktif yang diizinkan pada environment pengguna. Rule ini global karena tidak dibatasi ke grup tertentu. Pada aplikasi final, rule setara ditambahkan untuk request line, issue, dan issue line.

ACL memperbolehkan membaca model. Rule membatasi record yang memenuhi domain. Method bisnis kemudian memeriksa pemilik, status, dan peran. Contohnya, boleh membaca permintaan satu perusahaan tidak berarti boleh menyetujui permintaan sendiri.

## 2.8 Buat daftar, form, dan action

Isi lengkap starter `views/purchase_request_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_request_list" model="ir.ui.view">
        <field name="name">supplyflow.request.list</field>
        <field name="model">supplyflow.request</field>
        <field name="arch" type="xml">
            <list create="false" edit="false" delete="false">
                <field name="name"/>
                <field name="company_id"/>
                <field name="purpose"/>
            </list>
        </field>
    </record>
    <record id="view_request_form" model="ir.ui.view">
        <field name="name">supplyflow.request.form</field>
        <field name="model">supplyflow.request</field>
        <field name="arch" type="xml">
            <form create="false" edit="false" delete="false">
                <sheet>
                    <group>
                        <field name="name"/>
                        <field name="company_id"/>
                        <field name="purpose"/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>
    <record id="action_requests" model="ir.actions.act_window">
        <field name="name">Purchase Requisitions</field>
        <field name="res_model">supplyflow.request</field>
        <field name="view_mode">list,form</field>
    </record>
</odoo>
```

View menjelaskan cara menampilkan model. `<list>` menampilkan banyak record dan `<form>` satu record. `field name="purpose"` harus cocok dengan field Python. Action menentukan model dan jenis view yang dibuka; ia belum menjadi menu sampai dihubungkan pada file berikutnya.

`create="false"` membantu menjaga checkpoint tetap kosong. Pembatasan UI ini bukan mekanisme keamanan server; karena itu ACL starter juga belum memberikan create.

## 2.9 Hubungkan menu ke action

Isi lengkap starter `views/menus.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <menuitem id="menu_supplyflow" name="SupplyFlow Office"
              sequence="10" groups="supplyflow_office.group_user"/>
    <menuitem id="menu_requests" name="Purchase requests"
              parent="menu_supplyflow" action="action_requests"
              sequence="20"/>
</odoo>
```

`parent` menempatkan submenu di bawah aplikasi. `action` menghubungkan klik ke window action yang sudah dibuat. ID starter mengikuti ID final untuk menu root dan permintaan, sehingga pembaruan tahap final tidak menciptakan menu duplikat dengan ID berbeda.

## 2.10 Jalankan checkpoint kerangka

Di terminal khusus latihan, pastikan proyek utama tidak sedang memakai port 8070. Jalankan tanpa data latihan:

```powershell
cd 'D:\Latihan-Odoo\supplyflow-office'
$env:COMPOSE_PROJECT_NAME = 'supplyflow-belajar'
.\scripts\Start.ps1
```

Hasil yang diharapkan: Odoo memasang modul, login admin dari secret lokal bekerja, dan aplikasi SupplyFlow Office membuka daftar permintaan yang masih kosong. Belum ada tombol workflow karena view starter tidak mendefinisikannya.

Setelah mengecek menu, hentikan layanan:

```powershell
Set-Location -LiteralPath 'D:\Latihan-Odoo\supplyflow-office' -ErrorAction Stop
$env:COMPOSE_PROJECT_NAME = 'supplyflow-belajar'
.\scripts\Stop.ps1
```

Jangan gunakan `-WithTrainingData` pada starter. Dataset final mencari field dan model yang baru dijelaskan pada bab berikutnya.

## 2.11 Mengganti starter dengan kode lengkap

Bab 3 dan 4 membahas model lengkap fungsi demi fungsi. Di folder latihan, ganti seluruh `purchase_request.py` starter dengan source final; tambahkan `supplier_issue.py` dan `workspace.py`. Jangan menambahkan class kedua di bawah class starter.

Sesudah mengganti model, tunggu bab 5 untuk memasang seluruh file XML, ACL, report, asset, import, dan manifest final secara bersama. Jangan menyalakan server di tengah kombinasi model final dan view/ACL starter yang belum lengkap.

Tiga hal yang perlu kamu kuasai sebelum lanjut: mengapa file perlu diimpor, bagaimana menu menemukan action, serta perbedaan ACL, record rule, dan pemeriksaan method. Gunakan nama `supplyflow.request` untuk mengikuti rujukannya di setiap file.
