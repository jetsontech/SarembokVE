# ============================================================
# Sarembok GPU / Unreal Rendering Diagnostic
# One-shot diagnostic collector
# ============================================================

$ErrorActionPreference = "SilentlyContinue"

$Root = "C:\Sarembok_VE"
$OutDir = Join-Path $Root "Saved\Diagnostics"
$TimeStamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Report = Join-Path $OutDir "Sarembok_Rendering_Diagnostic_$TimeStamp.txt"
$DxDiag = Join-Path $OutDir "DxDiag_$TimeStamp.txt"

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function Section {
    param([string]$Name)

    Add-Content $Report ""
    Add-Content $Report "============================================================"
    Add-Content $Report " $Name"
    Add-Content $Report "============================================================"
}

function Run-Command {
    param([string]$Title, [scriptblock]$Command)

    Section $Title

    try {
        $Result = & $Command 2>&1
        if ($null -ne $Result) {
            $Result | Out-File -FilePath $Report -Append -Encoding utf8
        }
    }
    catch {
        Add-Content $Report "ERROR: $($_.Exception.Message)"
    }
}

# Header
@"
SAREMBOK VE
UNREAL ENGINE 5.8
GPU / ADVANCED RENDERING DIAGNOSTIC

Generated: $(Get-Date)
Computer: $env:COMPUTERNAME
User: $env:USERNAME
Project: $Root

This diagnostic is READ-ONLY.
No project settings or system settings are modified.
"@ | Out-File $Report -Encoding utf8

# ------------------------------------------------------------
# SYSTEM
# ------------------------------------------------------------

Run-Command "SYSTEM INFORMATION" {
    Get-CimInstance Win32_ComputerSystem |
        Select-Object Manufacturer, Model, SystemType,
            @{N="RAM_GB";E={[math]::Round($_.TotalPhysicalMemory / 1GB,2)}}
}

Run-Command "WINDOWS VERSION" {
    Get-CimInstance Win32_OperatingSystem |
        Select-Object Caption, Version, BuildNumber,
            OSArchitecture, LastBootUpTime
}

# ------------------------------------------------------------
# GPU
# ------------------------------------------------------------

Run-Command "GPU INFORMATION" {
    Get-CimInstance Win32_VideoController |
        Select-Object Name,
            DriverVersion,
            DriverDate,
            VideoProcessor,
            AdapterRAM,
            CurrentHorizontalResolution,
            CurrentVerticalResolution,
            CurrentRefreshRate,
            Status
}

Run-Command "DISPLAY DEVICES" {
    Get-PnpDevice -Class Display |
        Format-List Status, FriendlyName, InstanceId
}

# ------------------------------------------------------------
# DIRECTX
# ------------------------------------------------------------

Section "DIRECTX DIAGNOSTICS"

Write-Host ""
Write-Host "Running DirectX diagnostic..." -ForegroundColor Cyan

dxdiag /t $DxDiag | Out-Null

Start-Sleep -Seconds 2

if (Test-Path $DxDiag) {

    Add-Content $Report "DxDiag file:"
    Add-Content $Report $DxDiag
    Add-Content $Report ""

    $DxText = Get-Content $DxDiag -Raw

    foreach ($Pattern in @(
        "Card name",
        "Manufacturer",
        "Chip type",
        "Display Memory",
        "Dedicated Memory",
        "Shared Memory",
        "Driver Version",
        "Driver Date",
        "Feature Levels",
        "Shader Model",
        "WDDM"
    )) {

        $Matches = Select-String -Path $DxDiag -Pattern $Pattern

        if ($Matches) {
            $Matches | ForEach-Object {
                Add-Content $Report $_.Line
            }
        }
    }
}

# ------------------------------------------------------------
# UNREAL PROJECT
# ------------------------------------------------------------

Run-Command "UNREAL PROJECT FILE" {

    $Project = Join-Path $Root "SarembokVE.uproject"

    if (Test-Path $Project) {
        Get-Content $Project
    }
    else {
        Write-Output "SarembokVE.uproject NOT FOUND"
    }
}

# ------------------------------------------------------------
# UNREAL CONFIG
# ------------------------------------------------------------

Run-Command "UNREAL CONFIGURATION FILES" {

    $ConfigRoot = Join-Path $Root "Config"

    if (Test-Path $ConfigRoot) {

        Get-ChildItem $ConfigRoot -Recurse -File |
            Where-Object {
                $_.Extension -in ".ini",".cfg"
            } |
            ForEach-Object {

                Write-Output ""
                Write-Output "----- $($_.FullName) -----"

                Select-String -Path $_.FullName `
                    -Pattern "r\.|Lumen|Nanite|RayTracing|Rendering|FeatureLevel|ShaderModel|DefaultRenderer|GraphicsAdapter|D3D12" |
                    ForEach-Object {
                        $_.Line
                    }
            }
    }
}

# ------------------------------------------------------------
# LATEST UNREAL LOG
# ------------------------------------------------------------

$Log = Get-ChildItem "$Root\Saved\Logs\*.log" `
    -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

Section "LATEST UNREAL LOG"

if ($Log) {

    Add-Content $Report "Latest log:"
    Add-Content $Report $Log.FullName
    Add-Content $Report "Last modified: $($Log.LastWriteTime)"
    Add-Content $Report ""

    Add-Content $Report "--- RHI / GPU / RENDERING EVENTS ---"

    Select-String -Path $Log.FullName `
        -Pattern `
        "LogRHI|LogD3D12RHI|LogRendererCore|LogVulkanRHI|LogD3D11RHI|RayTracing|Lumen|Nanite|Feature Level|Shader Model|GPU|Adapter|Intel Extensions|atomic64|SM6|SM5|advanced rendering" |
        Select-Object -First 300 |
        ForEach-Object {
            Add-Content $Report $_.Line
        }

    Add-Content $Report ""
    Add-Content $Report "--- ERRORS / WARNINGS / CRASHES ---"

    Select-String -Path $Log.FullName `
        -Pattern `
        "Error:|Warning:|Assertion failed|Critical error|Fatal error|appError|EXCEPTION|ensure|crash" |
        Select-Object -Last 200 |
        ForEach-Object {
            Add-Content $Report $_.Line
        }

}
else {
    Add-Content $Report "No Unreal log found."
}

# ------------------------------------------------------------
# UNREAL ENGINE VERSION
# ------------------------------------------------------------

Run-Command "UNREAL ENGINE INSTALLATION" {

    $UE = "C:\Program Files\Epic Games\UE_5.8"

    if (Test-Path $UE) {

        Write-Output "Engine: $UE"

        $BuildVersion = Join-Path $UE "Engine\Build\Build.version"

        if (Test-Path $BuildVersion) {
            Get-Content $BuildVersion
        }
    }
    else {
        Write-Output "UE_5.8 installation not found."
    }
}

# ------------------------------------------------------------
# SAREMBOK PLUGINS
# ------------------------------------------------------------

Run-Command "SAREMBOK PLUGINS" {

    $PluginRoot = Join-Path $Root "Plugins"

    if (Test-Path $PluginRoot) {

        Get-ChildItem $PluginRoot -Directory |
            Select-Object Name, FullName
    }
}

# ------------------------------------------------------------
# BUILD BINARIES
# ------------------------------------------------------------

Run-Command "SAREMBOK BUILD OUTPUT" {

    Get-ChildItem "$Root\Plugins" -Recurse `
        -Include "*.dll" `
        -ErrorAction SilentlyContinue |
        Where-Object {
            $_.FullName -match "Binaries\\Win64"
        } |
        Select-Object Name, Length, LastWriteTime, FullName
}

# ------------------------------------------------------------
# CRASH REPORTS
# ------------------------------------------------------------

Run-Command "UNREAL CRASH REPORTS" {

    $CrashDirs = @(
        "$Root\Saved\Crashes",
        "$env:LOCALAPPDATA\UnrealEngine\Common\DerivedDataCache"
    )

    foreach ($Dir in $CrashDirs) {

        if (Test-Path $Dir) {

            Write-Output ""
            Write-Output "Directory: $Dir"

            Get-ChildItem $Dir -Recurse -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTime -Descending |
                Select-Object -First 20 Name, FullName, LastWriteTime
        }
    }
}

# ------------------------------------------------------------
# FINAL ANALYSIS
# ------------------------------------------------------------

Section "AUTOMATED FINDINGS"

$Findings = @()

if ($Log) {

    $LogText = Get-Content $Log.FullName -Raw

    if ($LogText -match "Adapter only supports up to Feature Level 'SM5'") {
        $Findings += "CRITICAL: Unreal requested SM6 but selected GPU was limited to SM5."
    }

    if ($LogText -match "RHI D3D12 with Feature Level SM5 is supported and will be used") {
        $Findings += "D3D12 is active, but Unreal is operating at SM5 feature level."
    }

    if ($LogText -match "Intel Extensions Framework not supported") {
        $Findings += "Intel Extensions Framework is not supported by the installed driver."
    }

    if ($LogText -match "Integrated GPU \(iGPU\): true") {
        $Findings += "Unreal confirmed that the selected GPU is an integrated GPU."
    }

    if ($LogText -match "Ray tracing is disabled") {
        $Findings += "Ray tracing is currently disabled by project settings."
    }

    if ($LogText -match "r.Nanite.ProjectEnabled:1") {
        $Findings += "Nanite is enabled in project configuration."
    }

    if ($LogText -match "r.Lumen.DiffuseIndirect.Allow:1") {
        $Findings += "Lumen diffuse indirect lighting is enabled."
    }

    if ($LogText -match "Assertion failed: Index >= 0") {
        $Findings += "CRITICAL: Previous UObjectArray Index >= 0 shutdown assertion was detected."
    }

    if ($LogText -match "FSarembokBridgeModule::ShutdownModule") {
        $Findings += "SarembokBridge ShutdownModule appeared in the crash stack."
    }

    if ($LogText -match "Sarembok Runtime Manager Shutdown") {
        $Findings += "Sarembok Runtime Manager shutdown sequence executed."
    }

    if ($LogText -match "\[SAREMBOK\] WebSocket Client Disconnected") {
        $Findings += "Sarembok WebSocket client disconnected cleanly."
    }
}

if ($Findings.Count -eq 0) {
    Add-Content $Report "No predefined diagnostic conditions detected."
}
else {
    $Findings | ForEach-Object {
        Add-Content $Report " - $_"
    }
}

# ------------------------------------------------------------
# ZIP EVERYTHING
# ------------------------------------------------------------

$Zip = Join-Path $OutDir "Sarembok_Rendering_Diagnostic_$TimeStamp.zip"

$FilesToZip = @(
    $Report
)

if (Test-Path $DxDiag) {
    $FilesToZip += $DxDiag
}

Compress-Archive `
    -Path $FilesToZip `
    -DestinationPath $Zip `
    -Force

# ------------------------------------------------------------
# CONSOLE SUMMARY
# ------------------------------------------------------------

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " SAREMBOK RENDERING DIAGNOSTIC COMPLETE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Report:" -ForegroundColor Yellow
Write-Host $Report
Write-Host ""
Write-Host "ZIP:" -ForegroundColor Yellow
Write-Host $Zip
Write-Host ""

if ($Findings.Count -gt 0) {

    Write-Host "FINDINGS:" -ForegroundColor Yellow

    foreach ($Finding in $Findings) {
        Write-Host "  $Finding"
    }

}
else {
    Write-Host "No predefined problems detected." -ForegroundColor Green
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan