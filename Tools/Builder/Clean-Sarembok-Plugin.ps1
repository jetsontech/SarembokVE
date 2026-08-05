Write-Host "Cleaning SarembokBridge duplicate source files..." -ForegroundColor Cyan

$Plugin = "C:\Sarembok_VE\Plugins\SarembokBridge\Source\SarembokBridge"

$RootFiles = Get-ChildItem $Plugin -File

foreach ($file in $RootFiles) {

    if ($file.Extension -eq ".cpp" -or $file.Extension -eq ".h") {

        $name = $file.Name

        if ($name -ne "SarembokBridge.Build.cs") {

            Write-Host "Removing duplicate root file: $name"

            Remove-Item $file.FullName -Force
        }
    }
}


# Ensure folders exist

New-Item "$Plugin\Public" -ItemType Directory -Force | Out-Null
New-Item "$Plugin\Private" -ItemType Directory -Force | Out-Null


# Move any remaining misplaced headers

Get-ChildItem $Plugin -Filter *.h -File | ForEach-Object {

    if ($_.DirectoryName -eq $Plugin) {

        Move-Item $_.FullName "$Plugin\Public\$($_.Name)" -Force

    }

}


# Move cpp files

Get-ChildItem $Plugin -Filter *.cpp -File | ForEach-Object {

    if ($_.DirectoryName -eq $Plugin) {

        Move-Item $_.FullName "$Plugin\Private\$($_.Name)" -Force

    }

}


# Clean Unreal generated data

Write-Host "Cleaning Unreal intermediates..."

Remove-Item "C:\Sarembok_VE\Intermediate" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Sarembok_VE\Binaries" -Recurse -Force -ErrorAction SilentlyContinue


Write-Host ""
Write-Host "Sarembok Plugin Structure Cleaned" -ForegroundColor Green