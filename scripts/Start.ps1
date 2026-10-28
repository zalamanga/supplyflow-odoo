param([switch]$WithTrainingData, [switch]$SkipPull)
. (Join-Path $PSScriptRoot 'Common.ps1')
Initialize-LocalConfiguration
if (-not $SkipPull) { Invoke-Compose pull odoo postgres }
Invoke-Compose up -d --wait postgres
Invoke-Compose stop odoo
Invoke-Compose run --rm -T odoo python3 /opt/supplyflow/manage.py initialize
if ($WithTrainingData) { Invoke-Compose run --rm -T odoo python3 /opt/supplyflow/manage.py seed }
Invoke-Compose up -d --wait odoo
Write-Host 'SupplyFlow Office: http://localhost:8070'
Write-Host 'Login details: .secrets/LOCAL-CREDENTIALS.txt'
