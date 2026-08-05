# ==========================================================
# Fix Sarembok Builder v3 Function Order
# ==========================================================

$FILE="C:\Sarembok_VE\Tools\Builder\SarembokBuilder.ps1"


$content = Get-Content $FILE -Raw


if($content -match "function Create-Module")
{

    Write-Host "Moving Create-Module before switch..."


    # Extract function block

    $start = $content.IndexOf(
        "function Create-Module"
    )


    $functionBlock =
        $content.Substring($start)


    # Remove from bottom

    $content =
        $content.Substring(0,$start)



    # Find switch location

    $switchIndex =
        $content.IndexOf(
            "switch($Create)"
        )


    if($switchIndex -lt 0)
    {
        throw "Switch block not found"
    }



    # Insert function before switch

    $newContent =
        $content.Insert(
            $switchIndex,
            "`r`n$functionBlock`r`n"
        )


    Set-Content `
    $FILE `
    $newContent `
    -Encoding UTF8


    Write-Host ""
    Write-Host "Function order repaired"
}
else
{
    Write-Host "Create-Module not found"
}