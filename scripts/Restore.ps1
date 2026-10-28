param(
    [Parameter(Mandatory=$true)][string]$Archive,
    [switch]$ReplaceDatabase
)

. (Join-Path $PSScriptRoot 'Common.ps1')

if (-not $ReplaceDatabase) {
    throw 'Restore mengganti database dan filestore supplyflow. Gunakan -ReplaceDatabase hanya untuk arsip milik sendiri yang dipercaya, setelah membuat cadangan data saat ini.'
}
if (-not (Test-Path -LiteralPath (Join-Path $script:ProjectRoot '.runtime/odoo.conf'))) {
    throw 'Konfigurasi lokal belum ada. Jalankan scripts/Start.ps1 terlebih dahulu. Pertahankan secret koneksi lokal untuk restore.'
}
$archiveItem = Get-Item -LiteralPath $Archive
if ($archiveItem.PSIsContainer -or ($archiveItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'Archive harus menunjuk berkas ZIP biasa, bukan folder atau symlink.'
}
$archiveDirectory = $archiveItem.Directory.FullName
$containerArchive = '/backups/' + $archiveItem.Name

# Validasi pertama tidak menghentikan aplikasi atau mengubah database.
Invoke-Compose run --rm -T --no-deps --volume "${archiveDirectory}:/backups:ro" odoo python3 /opt/supplyflow/restore.py --archive $containerArchive --validate-only
$runningOdoo = @(& docker compose --project-directory $script:ProjectRoot ps --status running --quiet odoo)
if ($LASTEXITCODE -ne 0) { throw 'Gagal membaca status layanan Odoo.' }
$restartOdoo = $runningOdoo.Count -gt 0
$restoreSucceeded = $false
$odooStopped = -not $restartOdoo

try {
    if ($restartOdoo) {
        Invoke-Compose stop --timeout 30 odoo
        $odooStopped = $true
    }
    Invoke-Compose run --rm -T --no-deps --volume "${archiveDirectory}:/backups:ro" odoo python3 /opt/supplyflow/restore.py --archive $containerArchive --replace-database
    $restoreSucceeded = $true
    Write-Host 'Database dan filestore supplyflow telah dipulihkan.'
    Write-Host 'Login memakai password pengguna dari saat backup dibuat. Secret koneksi database dan master Odoo tetap memakai konfigurasi lokal saat ini.'
}
finally {
    if ($restoreSucceeded -and $restartOdoo) {
        Invoke-Compose up -d --no-deps odoo
    }
    elseif (-not $restoreSucceeded) {
        if ($odooStopped) {
            Write-Warning 'Restore gagal atau terhenti. Odoo dibiarkan berhenti agar database dan filestore tidak dipakai dalam keadaan yang belum diperiksa. Baca docs/OPERATIONS.md sebelum menyalakan kembali.'
        }
        else {
            Write-Warning 'Layanan Odoo gagal dihentikan; restore belum dijalankan. Periksa status Docker sebelum mengulangi perintah.'
        }
    }
}
