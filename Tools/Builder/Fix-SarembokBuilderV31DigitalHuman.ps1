# ==========================================================
# Sarembok Builder v3.1 DigitalHuman Command Patch
# ==========================================================

$FILE="C:\Sarembok_VE\Tools\Builder\SarembokBuilder.ps1"


$content = Get-Content $FILE -Raw


if($content -notmatch '"DigitalHuman"')
{

$content =
$content.Replace(
'"Memory",
        "All"',
'"Memory",
        "DigitalHuman",
        "All"'
)


$content =
$content.Replace(
'"All"
{
',
'"DigitalHuman"
{
    Create-Bridge

    Create-Module "Avatar"
    Create-Module "Voice"
    Create-Module "Vision"
    Create-Module "Agent"
    Create-Module "Memory"
}


"All"
{
'
)


Set-Content `
$FILE `
$content `
-Encoding UTF8

}


Write-Host ""
Write-Host "========================================"
Write-Host " DigitalHuman command added"
Write-Host "========================================"