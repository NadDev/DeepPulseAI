# CRBot Quick Launcher
# Redirects to the main launcher script

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot
& "$projectRoot\scripts\launch\start-all.ps1" @args
