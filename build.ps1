# build.ps1 — 배포물 만들기 (D011, D040). 절차는 docs/RELEASE.md
# 결과: release\AVD-v{버전}-win64.zip (exe 폴더), release\AVD-v{버전}-src.zip (같은 커밋의 소스)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# 소스 zip 이 exe 와 같은 코드여야 한다 (LGPL 소스 제공) — 커밋 안 된 변경이 있으면 멈춘다
if (git status --porcelain) { throw "커밋 안 된 변경이 있습니다. 커밋한 뒤 다시 실행하세요." }

$version = (Select-String utils\updater.py -Pattern '^APP_VERSION = "(.+)"').Matches[0].Groups[1].Value
$name = "AVD-v$version"

venv\Scripts\pyinstaller AVD.spec --noconfirm
if ($LASTEXITCODE) { throw "PyInstaller 실패 ($LASTEXITCODE)" }
Copy-Item LICENSE, NOTICE, THIRD_PARTY_LICENSES, README.md dist\AVD\

New-Item -ItemType Directory -Force release | Out-Null
Remove-Item "release\$name-*.zip" -ErrorAction SilentlyContinue
Compress-Archive dist\AVD "release\$name-win64.zip"
git archive --format=zip --prefix="$name/" -o "release\$name-src.zip" HEAD
if ($LASTEXITCODE) { throw "git archive 실패 ($LASTEXITCODE)" }

Get-ChildItem "release\$name-*.zip" | Select-Object Name, @{ n = "MB"; e = { [math]::Round($_.Length / 1MB, 1) } }
