param([switch]$SkipPull, [switch]$KeepDatabase)
. (Join-Path $PSScriptRoot 'Common.ps1')
Initialize-LocalConfiguration
if (-not $SkipPull) { Invoke-Compose pull odoo postgres }
Invoke-Compose up -d --wait postgres
Invoke-Compose stop odoo
$testDatabase = 'supplyflow_test_' + [Guid]::NewGuid().ToString('N')
Invoke-Compose exec -T postgres psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE $testDatabase OWNER supplyflow;"
try {
    Invoke-Compose -f (Join-Path $script:ProjectRoot 'compose.yaml') -f (Join-Path $script:ProjectRoot 'compose.test.yaml') run --rm -T odoo odoo --config=/run/odoo/odoo.conf "--database=$testDatabase" "--db-filter=^$testDatabase`$" --no-http --max-cron-threads=0 --stop-after-init --without-demo=True -i supplyflow_office --test-enable --test-tags /supplyflow_office --log-level=test
} finally {
    if ($KeepDatabase) {
        Write-Host "Test database retained: $testDatabase"
    } else {
        Invoke-Compose exec -T postgres dropdb -U postgres --if-exists --force $testDatabase
        Invoke-Compose run --rm -T --no-deps odoo python3 /opt/supplyflow/clean_test_filestore.py $testDatabase
    }
}
