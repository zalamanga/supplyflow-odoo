. (Join-Path $PSScriptRoot 'Common.ps1')
Initialize-LocalConfiguration
Invoke-Compose up -d --wait postgres
$runningOdoo = @(& docker compose --project-directory $script:ProjectRoot ps --status running --quiet odoo)
if ($LASTEXITCODE -ne 0) { throw 'Could not read the Odoo service state.' }
if ($runningOdoo.Count -gt 0) { Invoke-Compose stop odoo }
try {
    Invoke-Compose run --rm -T odoo python3 /opt/supplyflow/manage.py seed
} finally {
    if ($runningOdoo.Count -gt 0) { Invoke-Compose up -d --wait odoo }
}
Write-Host 'Synthetic training records loaded. Existing training identifiers are not duplicated.'
