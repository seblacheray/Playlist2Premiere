param([string]$FFprobe = '')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if ($env:OS -ne 'Windows_NT') { throw 'Build Windows requis sur Windows.' }
$argsList = @('--noconfirm', '--clean', '--onefile', '--windowed', '--name', 'Playlist2Premiere', '--paths', 'src', '--additional-hooks-dir', 'scripts/pyinstaller_hooks')
if ($FFprobe) {
    if (!(Test-Path $FFprobe)) { throw 'FFprobe introuvable.' }
    $argsList += @('--add-binary', "$FFprobe;.")
}
python -m PyInstaller @argsList scripts/windows_entry.py
if ($LASTEXITCODE -ne 0) { throw 'Échec PyInstaller' }
