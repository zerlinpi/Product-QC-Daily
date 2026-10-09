[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Folder,
    [Parameter(Mandatory)][string]$Report,
    [string]$Catalog,
    [switch]$RequireSigned,
    [string]$ExpectedPublisher
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $Folder).Path
if (!(Test-Path -LiteralPath (Join-Path $root 'Product-QC-Daily.exe') -PathType Leaf)) {
    throw 'The packaged application is missing; signature verification cannot pass.'
}
$files = @(Get-ChildItem -LiteralPath $root -Recurse -File -Force |
    Where-Object { $_.Extension -in '.exe', '.dll', '.pyd' } | Sort-Object FullName)
$items = @($files | ForEach-Object {
    $signature = Get-AuthenticodeSignature -LiteralPath $_.FullName
    [pscustomobject]@{
        path = [IO.Path]::GetRelativePath($root, $_.FullName)
        sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        status = $signature.Status.ToString()
        publisher = $signature.SignerCertificate.Subject
        certificate_thumbprint = $signature.SignerCertificate.Thumbprint
        timestamp_thumbprint = $signature.TimeStamperCertificate.Thumbprint
    }
})
$unsigned = @($items | Where-Object { $_.status -eq 'NotSigned' })
$invalid = @($items | Where-Object { $_.status -notin 'Valid', 'NotSigned' })
$application = @($items | Where-Object { $_.path -eq 'Product-QC-Daily.exe' })[0]
$result = [ordered]@{
    schema_version = 1
    commit = $env:GITHUB_SHA
    signature_required = [bool]$RequireSigned
    application = $application
    binary_count = $items.Count
    unsigned_count = $unsigned.Count
    invalid_count = $invalid.Count
    files = $items
    smartscreen_acceptance = 'NOT_VERIFIED_ON_USER_DEVICE'
}
$reportPath = [IO.Path]::GetFullPath($Report)
New-Item -ItemType Directory -Force ([IO.Path]::GetDirectoryName($reportPath)) | Out-Null
$result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $reportPath -Encoding utf8
if ($Catalog) {
    $catalogPath = [IO.Path]::GetFullPath($Catalog)
    $catalogDirectory = [IO.Path]::GetDirectoryName($catalogPath)
    New-Item -ItemType Directory -Force $catalogDirectory | Out-Null
    $relativePaths = @($unsigned | ForEach-Object {
        [IO.Path]::GetRelativePath($catalogDirectory, (Join-Path $root $_.path))
    })
    [IO.File]::WriteAllLines($catalogPath, [string[]]$relativePaths)
}
Write-Output "Authenticode: application=$($application.status); binaries=$($items.Count); unsigned=$($unsigned.Count); invalid=$($invalid.Count)"
if ($invalid.Count) { throw 'Invalid Authenticode signatures were found; refusing to package them.' }
if ($RequireSigned) {
    if ($unsigned.Count) { throw 'Signing is required, but unsigned binaries remain.' }
    if (!$application.timestamp_thumbprint) { throw 'The application signature has no trusted timestamp.' }
    if ($ExpectedPublisher -and $application.publisher -cne $ExpectedPublisher) {
        throw 'The application publisher does not match the configured identity.'
    }
} elseif ($application.status -eq 'NotSigned') {
    Write-Warning 'The application is unsigned. Windows trust prompts are NOT resolved.'
}
