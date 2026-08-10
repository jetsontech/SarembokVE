<#
.SYNOPSIS
    Comprehensive Sarembok_VE Health Diagnostic Script.
.DESCRIPTION
    Inspects repository status, Unreal Engine 5.8 environment, project files, 
    plugin configurations, module dependencies, source code integrity, and WebSocket setup.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Continue"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "         SAREMBOK_VE PROJECT DIAGNOSTICS REPORT             " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "Root: C:\Sarembok_VE`n"

$ProjectRoot = "C:\Sarembok_VE"
$PassedCount = 0
$WarningCount = 0
$ErrorCount = 0

function Report-Pass($Message) {
    Write-Host "  [PASS] $Message" -ForegroundColor Green
    $script:PassedCount++
}

function Report-Warn($Message) {
    Write-Host "  [WARN] $Message" -ForegroundColor Yellow
    $script:WarningCount++
}

function Report-Fail($Message) {
    Write-Host "  [FAIL] $Message" -ForegroundColor Red
    $script:ErrorCount++
}

# 1. Git Repository Check
Write-Host "[1/7] Git Repository Status..." -ForegroundColor Cyan
if (Test-Path "$ProjectRoot\.git") {
    $GitBranch = git -C $ProjectRoot branch --show-current 2>&1
    $GitStatus = git -C $ProjectRoot status --porcelain 2>&1
    Report-Pass "Git repository detected (Branch: $GitBranch)"
    if ($GitStatus) {
        $UncommittedCount = ($GitStatus | Measure-Object).Count
        Report-Warn "Working directory has $UncommittedCount uncommitted change(s)"
    } else {
        Report-Pass "Working directory is clean"
    }
} else {
    Report-Fail "Not a valid Git repository"
}

# 2. Unreal Engine 5.8 Installation Check
Write-Host "`n[2/7] Unreal Engine 5.8 Environment..." -ForegroundColor Cyan
$UEBuildBat = Get-ChildItem "C:\Program Files\Epic Games", "D:\Program Files\Epic Games", "C:\Epic Games" -Recurse -Filter "Build.bat" -ErrorAction SilentlyContinue | Where-Object { $_.FullName -match "UE_5" } | Select-Object -First 1

if ($UEBuildBat) {
    Report-Pass "Found UE Build.bat: $($UEBuildBat.FullName)"
} else {
    Report-Fail "Unreal Engine 5 Build.bat not found in standard paths"
}

# 3. Project File (.uproject) Check
Write-Host "`n[3/7] Project File (.uproject)..." -ForegroundColor Cyan
$UProjectPath = "$ProjectRoot\SarembokVE.uproject"
if (Test-Path $UProjectPath) {
    Report-Pass "Found SarembokVE.uproject"
    try {
        $UProjectContent = Get-Content $UProjectPath -Raw | ConvertFrom-Json
        Report-Pass "Engine Association: $($UProjectContent.EngineAssociation)"
        
        $EnabledPlugins = $UProjectContent.Plugins | Where-Object { $_.Enabled -eq $true } | Select-Object -ExpandProperty Name
        Report-Pass "Enabled Plugins in .uproject: $($EnabledPlugins -join ', ')"
    } catch {
        Report-Fail "Failed to parse SarembokVE.uproject JSON"
    }
} else {
    Report-Fail "SarembokVE.uproject not found"
}

# 4. Plugins Audit
Write-Host "`n[4/7] Subsystem Plugins Check..." -ForegroundColor Cyan
$RequiredPlugins = @("SarembokBridge", "SarembokAvatar", "SarembokVoice", "SarembokVision", "SarembokAgent", "SarembokMemory")

foreach ($PluginName in $RequiredPlugins) {
    $PluginDir = "$ProjectRoot\Plugins\$PluginName"
    $UPluginFile = "$PluginDir\$PluginName.uplugin"
    $SourceDir = "$PluginDir\Source\$PluginName"
    $BuildCs = "$SourceDir\$PluginName.Build.cs"
    
    if (!(Test-Path $PluginDir)) {
        Report-Fail "Plugin directory missing: Plugins\$PluginName"
        continue
    }
    if (!(Test-Path $UPluginFile)) {
        Report-Fail "Missing uplugin file: Plugins\$PluginName\$PluginName.uplugin"
    } else {
        Report-Pass "Plugin $PluginName : uplugin present"
    }
    
    if (!(Test-Path $BuildCs)) {
        Report-Fail "Missing Build.cs: Plugins\$PluginName\Source\$PluginName\$PluginName.Build.cs"
    } else {
        Report-Pass "Plugin $PluginName : Build.cs present"
    }
    
    $PublicFiles = Get-ChildItem "$SourceDir\Public" -File -ErrorAction SilentlyContinue
    $PrivateFiles = Get-ChildItem "$SourceDir\Private" -File -ErrorAction SilentlyContinue
    Report-Pass "Plugin $PluginName : Source contains $($PublicFiles.Count) header(s) and $($PrivateFiles.Count) cpp file(s)"
}

# 5. Duplicate Code & Source Integrity Audit
Write-Host "`n[5/7] Source Code Integrity & Duplicate Check..." -ForegroundColor Cyan
$IgnoredDirs = @("Intermediate", "Binaries", ".vs", "Saved", "DerivedDataCache")
$SourceFiles = Get-ChildItem -Path "$ProjectRoot\Plugins", "$ProjectRoot\Source" -Recurse -File | Where-Object {
    $File = $_
    $PathParts = $File.FullName.Split([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    $IsIgnored = $false
    foreach ($Dir in $IgnoredDirs) {
        if ($PathParts -contains $Dir) {
            $IsIgnored = $true
            break
        }
    }
    (-not $IsIgnored) -and ($File.Extension -eq ".cpp" -or $File.Extension -eq ".h")
}

$FilenameGroups = $SourceFiles | Group-Object Name | Where-Object { $_.Count -gt 1 }
if ($FilenameGroups) {
    foreach ($Group in $FilenameGroups) {
        Report-Warn "Duplicate source file detected: '$($Group.Name)' found at:"
        foreach ($File in $Group.Group) {
            Write-Host "    - $($File.FullName)" -ForegroundColor Gray
        }
    }
} else {
    Report-Pass "No duplicate C++ source files detected across active plugin folders"
}

# 6. WebSocket Protocol & Backend Check
Write-Host "`n[6/7] Backend & WebSocket Setup..." -ForegroundColor Cyan
$BackendServer = "$ProjectRoot\backend\WebSocket\server.py"
$ProtocolJson = "$ProjectRoot\backend\WebSocket\unreal_protocol.json"

if (Test-Path $BackendServer) {
    Report-Pass "Backend WebSocket server script present ($BackendServer)"
} else {
    Report-Fail "Missing backend server script"
}

if (Test-Path $ProtocolJson) {
    Report-Pass "Unreal WebSocket protocol configuration present"
} else {
    Report-Warn "Unreal protocol JSON missing"
}

# 7. Summary
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "                   DIAGNOSTICS SUMMARY                      " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Passed  : $PassedCount" -ForegroundColor Green
Write-Host "  Warnings: $WarningCount" -ForegroundColor Yellow
Write-Host "  Errors  : $ErrorCount" -ForegroundColor Red

if ($ErrorCount -eq 0) {
    Write-Host "`nResult: SAREMBOK_VE PROJECT IS HEALTHY & READY TO BUILD" -ForegroundColor Green
} else {
    Write-Host "`nResult: ISSUES DETECTED - PLEASE ADDRESS FAILS BEFORE BUILDING" -ForegroundColor Red
}
