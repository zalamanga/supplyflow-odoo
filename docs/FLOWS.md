# Alur SupplyFlow Office

Diagram ini menjelaskan rancangan proses dan batas tanggung jawabnya. Status hasil pengujian harus dibaca dari catatan verifikasi implementasi, bukan dari keberadaan diagram.

## Permintaan pembelian sampai RFQ

```mermaid
flowchart TD
    A[Pengaju mengisi draft] --> B{Data dan baris valid?}
    B -- Tidak --> A
    B -- Ya --> C[Ajukan: submitted]
    C --> D[Isi pokok dan baris dibekukan]
    D --> E{Penyetuju berbeda dari pengaju dan pembuat?}
    E -- Tidak --> F[Tolak aksi di server]
    E -- Ya --> G{Keputusan}
    G -- Tolak dengan alasan --> H[rejected]
    H --> I[Pengaju reset ke draft]
    I --> A
    G -- Setujui --> J[approved]
    J --> K{Hak membuat Purchase Order tersedia?}
    K -- Tidak --> L[Tolak aksi tanpa menambah izin]
    K -- Ya --> M[Kunci permintaan dan periksa tautan RFQ]
    M --> N{RFQ sudah tertaut?}
    N -- Ya --> O[Buka RFQ yang sama]
    N -- Tidak --> P[Buat draft RFQ dengan operasi incoming gudang]
    P --> Q[Tautkan RFQ: rfq_created]
    Q --> O
    O --> R[Petugas pembelian mengolah RFQ di Odoo]
    R --> S[Konfirmasi PO mengikuti aturan Odoo]
```

Pengaju dapat membatalkan draft, pengajuan yang masih menunggu, atau permintaan yang ditolak. Pembatalan setelah persetujuan memerlukan penyetuju independen; pelaksana dan waktu dicatat pada riwayat. Dokumen yang sudah menghasilkan RFQ tidak dibatalkan lewat alur permintaan; petugas pembelian mengelola RFQ/PO tertaut menurut status dan izin Odoo.

Persetujuan mengizinkan pembuatan RFQ dari permintaan. Persetujuan itu tidak memesan barang, menerima barang, atau membayar pemasok. RFQ tetap dapat diperbarui di Purchase, sehingga estimasi permintaan bukan kontrol atas seluruh perubahan harga RFQ.

## Receipt bermasalah dan retur pemasok

```mermaid
flowchart TD
    A[Receipt incoming selesai di Odoo] --> B[Pelapor membuat kasus]
    B --> C[Pilih jenis masalah, sumber, barang, dan jumlah]
    C --> D{Sumber dan baris valid?}
    D -- Tidak --> E[Tampilkan alasan penolakan]
    E --> B
    D -- Ya --> F[Ajukan kasus dan bekukan isi]
    F --> G{Penyetuju independen?}
    G -- Tidak --> H[Tolak aksi di server]
    G -- Ya --> I{Keputusan}
    I -- Selesaikan tanpa retur / shortage --> N[Penyetuju menulis catatan penyelesaian]
    N --> O[Kasus selesai tanpa perpindahan stok]
    I -- Setujui retur barang fisik --> L[Kasus disetujui untuk retur]
    L --> P[Kunci kasus dan periksa retur tertaut]
    P --> Q{Retur sudah ada?}
    Q -- Ya --> R[Buka picking yang sama]
    Q -- Tidak --> S[Periksa sisa jumlah yang dapat diretur]
    S --> T[Buat retur melalui mekanisme Odoo]
    T --> R
    R --> U[Gudang memeriksa barang dan picking retur]
    U --> V[Gudang memvalidasi retur di Inventory]
    V --> W[Odoo mencatat perpindahan stok]
```

Pembuatan picking retur dan validasi picking merupakan dua tindakan terpisah. Retur yang masih menunggu validasi belum membuktikan bahwa barang sudah dikirim balik. Catatan penyelesaian shortage tidak otomatis membuat refund, credit note, atau jurnal.

Kasus tidak mempunyai alur tolak/reset ke draft. Pelapor atau anggota Approver dapat membatalkan kasus pada status yang diizinkan. Pembatalan kasus yang sudah disetujui memerlukan grup Approver, tetapi aksi pembatalan ini tidak menerapkan pemeriksaan reviewer independen. Kasus yang sudah diterima penyelesaiannya atau menghasilkan picking retur tidak dibatalkan lewat alur kasus.

## Penjualan dan pengiriman

```mermaid
flowchart LR
    A[Quotation pelanggan] --> B[Konfirmasi sales order]
    B --> C[Odoo membuat delivery]
    C --> D[Gudang periksa ketersediaan dan jumlah]
    D --> E{Jumlah lengkap?}
    E -- Ya --> F[Validasi delivery]
    E -- Sebagian --> G[Validasi jumlah aktual]
    G --> H{Sisa tetap akan dikirim?}
    H -- Ya --> I[Backorder mengikuti pilihan Odoo]
    H -- Tidak --> J[Tutup sisa sesuai pilihan Odoo]
    I --> D
    F --> K[Stok dan status delivery diperbarui]
    J --> K
```

Alur ini memakai Sales dan Inventory standar. Addon permintaan/masalah penerimaan tidak mengganti perhitungan stok, reservasi, lokasi, atau aturan backorder Odoo.

## Pembelian dan penerimaan

```mermaid
flowchart LR
    A[Draft RFQ] --> B[Petugas pembelian tinjau vendor dan harga]
    B --> C[Konfirmasi purchase order]
    C --> D[Receipt gudang tujuan]
    D --> E[Gudang masukkan jumlah yang diterima]
    E --> F[Validasi receipt]
    F --> G{Ada sisa penerimaan?}
    G -- Ya --> H[Pilih backorder sesuai kebutuhan]
    G -- Tidak --> I[Receipt selesai]
    H --> I
    I --> J{Ada masalah yang perlu ditinjau?}
    J -- Ya --> K[Buat kasus SupplyFlow pada receipt selesai]
    J -- Tidak --> L[Proses penerimaan selesai]
```

Jumlah yang kurang masih dapat dikelola melalui backorder native. Kasus shortage merupakan catatan penanganan masalah dan keputusan; kasus itu tidak mengubah kuantitas barang yang sebenarnya diterima.

## Setup lokal dan komponen

```mermaid
flowchart TD
    A[Pengembang menjalankan scripts/Start.ps1] --> B[Siapkan secret lokal yang diabaikan Git]
    B --> P[Tarik image resmi bila SkipPull tidak dipilih]
    P --> C[Docker Compose menjalankan PostgreSQL 17]
    C --> D[Tunggu database siap]
    D --> E[Inisialisasi database dan instal supplyflow_office]
    E --> F[Atur kredensial pengguna aplikasi]
    F --> G{Opsi WithTrainingData dipilih?}
    G -- Ya --> H[Masukkan data sintetis berlabel latihan]
    G -- Tidak --> I[Database tanpa transaksi latihan]
    H --> J[Jalankan layanan Odoo]
    I --> J
    J --> K[Browser ke 127.0.0.1:8070]
    K --> L[Login pengguna Odoo]
```

```mermaid
flowchart LR
    U[Browser pengguna] -->|HTTP lokal 8070| O[Odoo 19 Community]
    O --> N[Sales / Purchase / Inventory / Mail]
    O --> C[Addon supplyflow_office]
    C -->|ORM dan metode bisnis| N
    O -->|Koneksi internal Compose| P[(PostgreSQL 17)]
    O --> F[(Filestore dan data Odoo)]
    A[Kode addon pada host] -->|Bind mount read-only| O
    Q[Script container pada host] -->|Bind mount read-only| O
    S[Secret lokal] -->|Konfigurasi runtime| O
    S -->|Password role database| P
```

PostgreSQL tidak mempunyai port host pada rancangan lokal ini. Database memuat data terstruktur, sedangkan filestore menyimpan berkas seperti lampiran. Cadangan harus mempertahankan keduanya dari keadaan yang konsisten.
