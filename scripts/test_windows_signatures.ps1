param([Parameter(Mandatory)][string]$Folder)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$testRoot = Join-Path $env:RUNNER_TEMP 'qc-signature-gate-test'
New-Item -ItemType Directory -Force $testRoot | Out-Null
$verifier = Join-Path $PSScriptRoot 'verify_windows_signatures.ps1'
$report = Join-Path $testRoot 'unsigned.json'
$catalog = Join-Path $testRoot 'catalog.txt'

# Exercise the actual unsigned PyInstaller output, not mocked signature objects.
& pwsh -NoProfile -File $verifier -Folder $Folder -Report $report -Catalog $catalog
if ($LASTEXITCODE -ne 0) { throw 'Unsigned diagnostic scan failed' }
$result = Get-Content $report -Raw | ConvertFrom-Json
if ($result.application.status -ne 'NotSigned' -or $result.unsigned_count -lt 1) {
    throw 'Expected the freshly built application to be unsigned before signing'
}
if (!(Select-String -LiteralPath $catalog -SimpleMatch 'Product-QC-Daily.exe' -Quiet)) {
    throw 'Signing catalog must include the application'
}
& pwsh -NoProfile -File $verifier -Folder $Folder -Report (Join-Path $testRoot 'required.json') -RequireSigned
if ($LASTEXITCODE -eq 0) { throw 'Required-signature gate accepted an unsigned application' }
$empty = Join-Path $testRoot 'empty'
New-Item -ItemType Directory -Force $empty | Out-Null
& pwsh -NoProfile -File $verifier -Folder $empty -Report (Join-Path $testRoot 'empty.json')
if ($LASTEXITCODE -eq 0) { throw 'Signature gate accepted a missing application' }
Write-Output 'Signature gate negative-path tests: PASS'
exit 0
