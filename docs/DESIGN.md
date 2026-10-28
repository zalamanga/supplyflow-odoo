# Arah antarmuka SupplyFlow Office

SupplyFlow Office memakai web client Odoo Community. Arah visualnya mengikuti sistem yang sudah digunakan Sales, Purchase, dan Inventory agar staf dapat membuka RFQ, receipt, atau retur tanpa mempelajari pola antarmuka kedua.

Dokumen ini merangkum keputusan desain untuk implementasi, bukan bukti bahwa pemeriksaan UI telah selesai. Tidak ada logo baru, foto profil, ilustrasi pemasok, atau identitas perusahaan nyata yang dibuat untuk proyek ini.

## Identitas dan pengguna

Nama produk ditampilkan sebagai teks SupplyFlow Office. Bidang usahanya distributor perlengkapan kantor. Pengguna bekerja dengan daftar produk, kebutuhan pembelian, receipt, keputusan, dan picking retur. Informasi yang perlu menonjol adalah status dokumen, tindakan berikutnya, gudang tujuan, jumlah, dan orang yang bertanggung jawab.

Nada antarmuka langsung dan operasional. Pesan kesalahan menyebut hal yang perlu diperbaiki, misalnya pemasok belum dipilih atau jumlah harus lebih dari nol. Teks tidak menjanjikan keamanan, kepatuhan, atau penghematan yang belum dibuktikan.

## Pembacaan desain

| Dial | Nilai | Penerapan |
| --- | --- | --- |
| ENERGY | 2 dari 3 | Memakai aksen dan status Odoo untuk menonjolkan tindakan kerja; tidak menambah efek dekoratif |
| RHYTHM | 2 dari 3 | Daftar untuk membandingkan dokumen, form untuk mengerjakan satu dokumen, ringkasan untuk menuju pekerjaan yang menunggu |
| MOTION | 1 dari 3 | Perilaku interaksi native; tidak ada carousel, animasi latar, atau transisi tambahan |

Angka dial adalah keputusan desain, bukan metrik hasil penelitian pengguna. Motif identitas berasal dari alur dokumen: nomor permintaan, status, gudang, dan tautan ke RFQ/receipt/retur selalu memakai lokasi serta istilah yang konsisten.

## Warna, tipografi, dan komponen

Palet, font, ukuran kontrol, jarak, focus ring, dan dialog mengikuti Odoo. Tidak ada tema gelap atau penggantian font khusus. Pilihan ini mempertahankan keterbacaan dan konsistensi dengan layar native, bukan membentuk landing page promosi.

Label field readonly pada dua form addon memakai `#495057` dengan opacity penuh. Label tetap dibutuhkan untuk membaca dokumen yang sudah diajukan; mengurangi kontrasnya seperti kontrol nonaktif akan menyulitkan pembacaan pada ponsel. Aturan CSS dibatasi ke kelas `sf_document`, sehingga tidak mengganti tema aplikasi native lain.

| Elemen | Tujuan |
| --- | --- |
| Statusbar form | Menunjukkan posisi dokumen dalam alur persetujuan |
| Tombol tindakan native | Menunjukkan aksi yang sesuai status serta izin pengguna |
| Smart button/tautan dokumen | Membuka RFQ, receipt sumber, atau picking retur yang benar-benar ada |
| Daftar baris produk | Membandingkan produk, jumlah, satuan, dan estimasi tanpa menggulir antar kartu |
| Chatter | Menelusuri pengajuan, keputusan, dan alasan pada konteks dokumen |
| Filter pencarian | Memisahkan draft, menunggu persetujuan, disetujui, dan dokumen hasil |
| Nilai ringkasan | Membuka daftar yang mendasari angka, bila ringkasan tersedia |

Tidak ada kartu statistik dengan angka hardcode. Jika ringkasan pekerjaan ditambahkan, nilai dihitung dari dokumen yang boleh dibaca pengguna pada perusahaan aktif. Keadaan kosong harus menyebut bahwa belum ada dokumen yang sesuai filter, bukan menampilkan angka keberhasilan fiktif.

## Susunan layar

### Daftar permintaan

Kolom utama menampilkan nomor, tanggal kebutuhan, pengaju, pemasok, gudang, estimasi, dan status. Pengguna dapat mencari nomor atau pihak terkait dan memfilter status. Status serta tanggal membantu memilih pekerjaan tanpa harus membuka seluruh form.

### Workspace

Workspace Owl merangkum pekerjaan yang perlu ditindaklanjuti sebelum menampilkan permintaan terbaru. Angka membuka daftar dengan filter yang sesuai, sedangkan nomor permintaan membuka form terkait. Petunjuk singkat menyebut aplikasi standar untuk RFQ, receipt, delivery, dan laporan stok.

Prioritas visualnya adalah pekerjaan menunggu keputusan atau terlambat, bukan angka dekoratif. Ringkasan retur hanya menghitung picking tertaut yang belum selesai atau dibatalkan; status kasus dan status perpindahan fisik tidak disamakan.

### Form permintaan

Bagian atas menampilkan nomor, status, dan tindakan. Informasi pemasok, gudang, tanggal, dan alasan berada sebelum baris produk. Estimasi total mengikuti baris. Keputusan serta tautan RFQ harus mudah ditemukan tanpa mencampur estimasi dengan nilai pesanan akhir.

Setelah pengajuan, form menunjukkan nilai yang dibekukan. Pengguna yang tidak mempunyai aksi berikutnya tetap dapat memahami siapa yang perlu memproses dokumen. Pesan penolakan persetujuan mandiri menjelaskan bahwa diperlukan pengguna lain.

### Daftar dan form masalah receipt

Receipt sumber, jenis masalah, pelapor, status, dan hasil penanganan menjadi informasi utama. Form menghubungkan baris masalah dengan barang yang benar-benar berasal dari receipt tersebut. Label membedakan kasus disetujui, picking retur dibuat, dan picking retur divalidasi.

Penyelesaian tanpa retur menampilkan catatan keputusan. Layar tidak menyamakan catatan itu dengan penggantian barang, pembayaran, atau kredit pemasok.

## Perilaku dan keadaan

Form kosong harus dapat disimpan sebagai draft bila field minimum terpenuhi, sedangkan pengajuan menerapkan validasi lengkap. Saat aksi gagal, pengguna tetap berada pada dokumennya dan mendapat alasan yang dapat ditindaklanjuti. Aksi berulang pada RFQ/retur yang sudah tertaut membuka dokumen yang sama.

Tampilan field readonly dan tombol tersembunyi membantu penggunaan, tetapi aturan sesungguhnya diperiksa pada server. Antarmuka tidak boleh menampilkan pesan berhasil jika transaksi server dibatalkan.

Navigasi keyboard mengikuti web client Odoo. Pemeriksaan akhir harus mencatat kemampuan memilih field relasi, berpindah ke baris produk, menekan aksi, menutup dialog, dan membuka dokumen tertaut dengan keyboard. Penggunaan nama/status yang jelas tidak boleh bergantung pada warna saja.

## Layar sempit dan screenshot

UI menggunakan reflow serta mode daftar/form Odoo. Pemeriksaan layar sempit harus memperhatikan tombol aksi, isian relasi panjang, baris produk, dan dialog keputusan. Tabel yang memang memerlukan scroll harus tetap dapat diakses tanpa menyebabkan seluruh halaman terpotong.

Screenshot untuk README harus diambil dari aplikasi yang dijalankan. Setiap gambar menunjukkan satu tugas yang jelas, seperti pengajuan disetujui beserta RFQ tertaut atau kasus barang rusak beserta retur. Data sintetis diberi konteks sebagai data latihan; gambar tidak boleh menampilkan password, token, email pribadi, atau dokumen kerja pengguna.

## Pemeriksaan sebelum publikasi

Hasil akhir perlu memeriksa layar daftar dan form, setiap aksi bisnis yang ditambahkan, akses terbatas, keadaan kosong, pesan validasi, serta tautan ke dokumen native. Pemeriksaan juga mencakup keterbacaan pada desktop dan layar sempit yang ukuran viewport-nya dicatat.

Desain ini tidak menambahkan aset visual atau pola navigasi dekoratif. Keputusan yang belum tersedia pada kode tidak boleh dipresentasikan sebagai fitur selesai. Catatan verifikasi akhir harus membedakan pemeriksaan yang sudah dijalankan dari target yang masih belum dibuktikan.
