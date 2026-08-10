$ErrorActionPreference = "Continue"

$Project = "C:\Sarembok_VE"
$LogDir = "$Project\Saved\Diagnostics"
$Report = "$LogDir\SarembokSmokeTest.txt"

New-Item -ItemType Directory -Force $LogDir | Out-Null

"========================================" | Set-Content $Report
"SAREMBOK VE - AUTOMATED SMOKE TEST"     | Add-Content $Report
"$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Add-Content $Report
"========================================" | Add-Content $Report

function Test-Step($Name, $Pass, $Detail) {
    if ($Pass) {
        $Status = "PASS"
    } else {
        $Status = "FAIL"
    }

    "$Status : $Name" | Add-Content $Report
    "       $Detail" | Add-Content $Report
    Write-Host "$Status : $Name" -ForegroundColor $(if ($Pass) { "Green" } else { "Red" })
}

# 1. Project
Test-Step `
    "Project exists" `
    (Test-Path "$Project\SarembokVE.uproject") `
    "$Project\SarembokVE.uproject"

# 2. Runtime Python
$PythonProcesses = Get-Process python -ErrorAction SilentlyContinue
Test-Step `
    "Python runtime process exists" `
    ($null -ne $PythonProcesses) `
    "$(@($PythonProcesses).Count) Python process(es)"

# 3. WebSocket
$Socket = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue

Test-Step `
    "Sarembok WebSocket port 8765 listening" `
    ($null -ne $Socket) `
    $(if ($Socket) {
        "PID $($Socket[0].OwningProcess) listening on $($Socket[0].LocalAddress):8765"
    } else {
        "Nothing listening on TCP 8765"
    })

# 4. Unreal
$UE = Get-Process UnrealEditor -ErrorAction SilentlyContinue

Test-Step `
    "Unreal Editor running" `
    ($null -ne $UE) `
    $(if ($UE) {
        "PID $($UE[0].Id)"
    } else {
        "UnrealEditor.exe not running"
    })

# 5. Project log
$Log = "$Project\Saved\Logs\SarembokVE.log"

$Connected = $false
$Received = $false
$Bridge = $false
$RuntimeManager = $false

if (Test-Path $Log) {
    $Connected = Select-String -Path $Log -Pattern "CONNECTED TO SAREMBOK RUNTIME" -Quiet
    $Received = Select-String -Path $Log -Pattern "RX FROM SAREMBOK RUNTIME" -Quiet
    $Bridge = Select-String -Path $Log -Pattern "Sarembok Bridge Initialized" -Quiet
    $RuntimeManager = Select-String -Path $Log -Pattern "Sarembok Runtime Manager Initialized" -Quiet
}

Test-Step "SarembokBridge initialized" $Bridge "Bridge module initialization"
Test-Step "Runtime Manager initialized" $RuntimeManager "Runtime manager initialization"
Test-Step "WebSocket connected" $Connected "Unreal connected to ws://127.0.0.1:8765"
Test-Step "Runtime message received" $Received "Unreal received a command from Sarembok Runtime"

$Failures = Select-String -Path $Report -Pattern "^FAIL :" -ErrorAction SilentlyContinue

"`n========================================" | Add-Content $Report

if ($Failures) {
    "SAREMBOK SYSTEM: FAIL" | Add-Content $Report
    Write-Host "`nSAREMBOK SYSTEM: FAIL" -ForegroundColor Red
} else {
    "SAREMBOK SYSTEM: PASS" | Add-Content $Report
    Write-Host "`nSAREMBOK SYSTEM: PASS" -ForegroundColor Green
}

"Report: $Report" | Add-Content $Report
Write-Host "Report: $Report"
