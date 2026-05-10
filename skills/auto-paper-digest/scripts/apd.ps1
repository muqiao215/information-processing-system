$ErrorActionPreference = 'Stop'

$repo = 'E:\web\tools\auto-paper-digest'

if (-not (Test-Path $repo)) {
  throw "Missing repo: $repo"
}

Set-Location $repo

if ($args.Count -eq 0) {
  python -m apd.cli --help
  exit $LASTEXITCODE
}

python -m apd.cli @args
exit $LASTEXITCODE
