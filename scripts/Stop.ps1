. (Join-Path $PSScriptRoot 'Common.ps1')
Invoke-Compose stop odoo postgres
Write-Host 'SupplyFlow stopped. Database and filestore volumes are preserved.'
