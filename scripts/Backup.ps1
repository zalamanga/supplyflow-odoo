param(
    [string]$OutputDirectory
)

. (Join-Path $PSScriptRoot 'Common.ps1')

if (-not (Test-Path -LiteralPath (Join-Path $script:ProjectRoot '.runtime/odoo.conf'))) {
    throw 'Konfigurasi lokal belum ada. Jalankan scripts/Start.ps1 terlebih dahulu.'
}
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $script:ProjectRoot '.backups' }
$backupDirectory = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $backupDirectory -Force | Out-Null
$backupDirectory = (Resolve-Path -LiteralPath $backupDirectory).ProviderPath
$archiveName = 'supplyflow-{0}-{1}.zip' -f [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ'), [Guid]::NewGuid().ToString('N').Substring(0,8)
$archivePath = Join-Path $backupDirectory $archiveName
$containerName = 'supplyflow-backup-' + [Guid]::NewGuid().ToString('N')
$backupContainerId = $null
$creationAttempted = $false
$composeConfiguration = & docker compose --project-directory $script:ProjectRoot config --format json
if ($LASTEXITCODE -ne 0) { throw 'Gagal membaca identitas proyek Compose.' }
$expectedProject = (($composeConfiguration -join "`n") | ConvertFrom-Json).name
$composeConfiguration = $null
if (-not $expectedProject -or $containerName -notmatch '^supplyflow-backup-[0-9a-f]{32}$') {
    throw 'Identitas proyek atau nama container backup tidak valid.'
}
$existingBackup = @(& docker container ls --all --quiet --no-trunc --filter "name=^/$containerName`$")
if ($LASTEXITCODE -ne 0 -or $existingBackup.Count -ne 0) {
    throw 'Nama container backup harus baru dan tidak boleh menimpa container yang sudah ada.'
}

function Assert-BackupContainerOwnership {
    param([Parameter(Mandatory=$true)][string]$ContainerId)
    if ($ContainerId -notmatch '^[0-9a-f]{64}$') { throw 'ID container backup tidak valid.' }
    $inspectionLines = & docker container inspect $ContainerId
    if ($LASTEXITCODE -ne 0) { throw 'Gagal memeriksa container backup.' }
    $container = @(($inspectionLines -join "`n") | ConvertFrom-Json)[0]
    if ($container.Id -ne $ContainerId -or $container.Name -ne "/$containerName" -or
        $container.Config.Labels.'com.docker.compose.project' -ne $expectedProject -or
        $container.Config.Labels.'com.docker.compose.service' -ne 'odoo' -or
        $container.Config.Labels.'com.docker.compose.oneoff' -ne 'True') {
        throw 'Menolak operasi pada container yang bukan pekerjaan backup SupplyFlow ini.'
    }
}

$runningOdoo = @(& docker compose --project-directory $script:ProjectRoot ps --status running --quiet odoo)
if ($LASTEXITCODE -ne 0) { throw 'Gagal membaca status layanan Odoo.' }
$restartOdoo = $runningOdoo.Count -gt 0

try {
    if ($restartOdoo) { Invoke-Compose stop --timeout 30 odoo }
    $creationAttempted = $true
    $createdOutput = & docker compose --project-directory $script:ProjectRoot run --detach -T --no-deps --name $containerName odoo python3 /opt/supplyflow/backup.py --output "/tmp/$archiveName"
    if ($LASTEXITCODE -ne 0) { throw 'Container backup gagal dibuat.' }
    $createdIds = @($createdOutput | Where-Object { $_ -match '^[0-9a-f]{64}$' })
    if ($createdIds.Count -ne 1) { throw 'Docker tidak mengembalikan satu ID container backup.' }
    $backupContainerId = $createdIds[0]
    Assert-BackupContainerOwnership $backupContainerId
    $exitStatus = & docker wait $backupContainerId
    if ($LASTEXITCODE -ne 0 -or ($exitStatus -join '').Trim() -ne '0') {
        & docker logs $backupContainerId
        throw 'Pembuatan arsip pada container backup gagal.'
    }
    if (Test-Path -LiteralPath $archivePath) { throw 'Berkas tujuan sudah ada; arsip tidak ditimpa.' }
    & docker cp "${backupContainerId}:/tmp/$archiveName" $archivePath
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $archivePath -PathType Leaf)) {
        throw 'Arsip tidak berhasil disalin dari container ke host.'
    }
    Write-Host "Cadangan tersimpan: $archivePath"
    Write-Host 'Arsip berisi data bisnis dan hash password pengguna. Simpan privat, di luar Git.'
}
finally {
    try {
        if (-not $backupContainerId -and $creationAttempted) {
            $candidates = @(& docker container ls --all --quiet --no-trunc --filter "name=^/$containerName`$")
            if ($LASTEXITCODE -ne 0 -or $candidates.Count -gt 1) { throw 'Gagal mengidentifikasi pekerjaan backup yang perlu dibersihkan.' }
            if ($candidates.Count -eq 1) { $backupContainerId = $candidates[0] }
        }
        if ($backupContainerId) {
            Assert-BackupContainerOwnership $backupContainerId
            & docker rm --force $backupContainerId | Out-Null
            if ($LASTEXITCODE -ne 0) { throw 'Container backup milik pekerjaan ini gagal dibersihkan.' }
        }
    }
    finally {
        if ($restartOdoo) { Invoke-Compose up -d --no-deps odoo }
    }
}
