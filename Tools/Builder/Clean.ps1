$ROOT="C:\Sarembok_VE"

$folders=@(
"$ROOT\Intermediate",
"$ROOT\Saved"
)

foreach($folder in $folders)
{
    if(Test-Path $folder)
    {
        Remove-Item `
        $folder `
        -Recurse `
        -Force
    }
}

Write-Host "Sarembok clean complete"
