$ErrorActionPreference = 'Stop'
$script:ProjectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))

function Invoke-Compose {
    # Keep native flags such as -d and -v out of PowerShell common-parameter binding.
    & docker compose --project-directory $script:ProjectRoot @args
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose failed (exit $LASTEXITCODE)." }
}

function New-LocalPassword {
    $bytes = New-Object byte[] 30
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($bytes) } finally { $generator.Dispose() }
    return [Convert]::ToBase64String($bytes)
}

function Initialize-LocalConfiguration {
    $utf8 = New-Object Text.UTF8Encoding($false)
    $secrets = Join-Path $script:ProjectRoot '.secrets'
    $runtime = Join-Path $script:ProjectRoot '.runtime'
    $projectName = if ($env:COMPOSE_PROJECT_NAME) { $env:COMPOSE_PROJECT_NAME } else { 'supplyflow-office' }
    $existingVolumes = @(& docker volume ls --filter "label=com.docker.compose.project=$projectName" --filter 'label=com.docker.compose.volume=postgres_data' --quiet)
    if ($LASTEXITCODE -ne 0) { throw 'Docker is unavailable. Start Docker Desktop before running this script.' }
    if ($existingVolumes.Count -gt 0) {
        foreach ($name in @('postgres_password','db_password','admin_password','master_password','training_credentials.json')) {
            if (-not (Test-Path -LiteralPath (Join-Path $secrets $name))) {
                throw "Existing SupplyFlow data was found but .secrets/$name is missing. Recover the original secrets before starting; no replacement password was generated."
            }
        }
    }
    New-Item -ItemType Directory -Path $secrets,$runtime -Force | Out-Null
    foreach ($name in @('postgres_password','db_password','admin_password','master_password')) {
        $target = Join-Path $secrets $name
        if (-not (Test-Path -LiteralPath $target)) {
            [IO.File]::WriteAllText($target, (New-LocalPassword), $utf8)
        }
    }
    $trainingPath = Join-Path $secrets 'training_credentials.json'
    if (-not (Test-Path -LiteralPath $trainingPath)) {
        $training = [ordered]@{ buyer = (New-LocalPassword); approver = (New-LocalPassword); warehouse = (New-LocalPassword) }
        [IO.File]::WriteAllText($trainingPath, ($training | ConvertTo-Json), $utf8)
    }
    $databasePassword = [IO.File]::ReadAllText((Join-Path $secrets 'db_password')).Trim()
    $masterPassword = [IO.File]::ReadAllText((Join-Path $secrets 'master_password')).Trim()
    $configuration = @"
[options]
addons_path = /mnt/extra-addons
data_dir = /var/lib/odoo
admin_passwd = $masterPassword
db_host = postgres
db_port = 5432
db_user = supplyflow
db_password = $databasePassword
db_name = supplyflow
dbfilter = ^supplyflow$
list_db = False
workers = 0
max_cron_threads = 1
db_maxconn = 16
limit_memory_soft = 1073741824
limit_memory_hard = 1342177280
limit_time_cpu = 120
limit_time_real = 240
proxy_mode = False
without_demo = True
"@
    [IO.File]::WriteAllText((Join-Path $runtime 'odoo.conf'), $configuration, $utf8)
    $adminPassword = [IO.File]::ReadAllText((Join-Path $secrets 'admin_password')).Trim()
    $training = Get-Content -LiteralPath $trainingPath -Raw | ConvertFrom-Json
    $credentials = @"
SupplyFlow Office (local only)
URL: http://localhost:8070
Database: supplyflow
Login: admin
Password: $adminPassword

The following users exist only after Start.ps1 -WithTrainingData:
buyer / $($training.buyer)
approver / $($training.approver)
warehouse / $($training.warehouse)

Keep this file private. Change application passwords through Odoo when needed.
"@
    [IO.File]::WriteAllText((Join-Path $secrets 'LOCAL-CREDENTIALS.txt'), $credentials, $utf8)
}
