#requires -Version 5.1
[CmdletBinding()]
param([switch]$SkipBuild)

$ErrorActionPreference='Stop'
$ProjectRoot='C:\Sarembok_VE'
$ProjectFile=Join-Path $ProjectRoot 'SarembokVE.uproject'
$EngineIni=Join-Path $ProjectRoot 'Config\DefaultEngine.ini'
$UE='C:\Program Files\Epic Games\UE_5.8'
$BuildBat=Join-Path $UE 'Engine\Build\BatchFiles\Build.bat'
$UBT=Join-Path $UE 'Engine\Binaries\DotNET\UnrealBuildTool\UnrealBuildTool.exe'
$Stamp=Get-Date -Format 'yyyyMMdd_HHmmss'
$Diag=Join-Path $ProjectRoot 'Saved\Diagnostics\RenderingRepair'
$Backup=Join-Path $Diag "Backup_$Stamp"
$Report=Join-Path $Diag "Sarembok_RenderingRepair_$Stamp.txt"

function Step($s){Write-Host "`n============================================================" -ForegroundColor Cyan;Write-Host $s -ForegroundColor Cyan;Write-Host "============================================================" -ForegroundColor Cyan}
function Report($s){$s|Out-File $Report -Append -Encoding utf8}

New-Item -ItemType Directory -Force -Path $Diag,$Backup|Out-Null
"SAREMBOK VE RENDERING REPAIR`nGenerated: $(Get-Date)`nProject: $ProjectRoot"|Out-File $Report -Encoding utf8

Step '1. VERIFY PROJECT'
if(!(Test-Path $ProjectRoot)){throw "Project root not found: $ProjectRoot"}
if(!(Test-Path $ProjectFile)){throw "Project file not found: $ProjectFile"}
if(!(Test-Path $BuildBat)){throw "UE Build.bat not found: $BuildBat"}
if(!(Test-Path $UBT)){throw "UnrealBuildTool not found: $UBT"}
Write-Host "Project: $ProjectRoot" -ForegroundColor Green
Write-Host "Engine : $UE" -ForegroundColor Green

Step '2. BACKUP'
if(Test-Path $EngineIni){Copy-Item $EngineIni (Join-Path $Backup 'DefaultEngine.ini.before-repair') -Force}
Copy-Item $ProjectFile (Join-Path $Backup 'SarembokVE.uproject') -Force
Write-Host "Backup: $Backup" -ForegroundColor Green
Report "Backup: $Backup"

Step '3. GPU CHECK'
try{Get-CimInstance Win32_VideoController|Where-Object {$_.Name -match 'Intel|NVIDIA|AMD|Radeon|GeForce|Arc'}|ForEach-Object{Write-Host "GPU: $($_.Name) | Driver: $($_.DriverVersion)" -ForegroundColor Yellow;Report "GPU: $($_.Name) | Driver: $($_.DriverVersion)"}}catch{Report "GPU query warning: $($_.Exception.Message)"}

Step '4. WRITE HARDWARE-ADAPTIVE UE5.8 RENDERING BASELINE'
New-Item -ItemType Directory -Force -Path (Split-Path $EngineIni)|Out-Null
$ini=@'
; Sarembok VE - UE 5.8 hardware-adaptive baseline
; Current machine: Intel Iris Xe iGPU. UE log shows SM6 request -> SM5 fallback.
; Do not force unsupported SM6/Lumen/Nanite/Virtual Shadow Maps/RT on this machine.

[/Script/Engine.RendererSettings]
r.DefaultFeature.AutoExposure.Method=0
r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange=True
DefaultGraphicsRHI=DefaultGraphicsRHI_DX12
r.DynamicGlobalIlluminationMethod=0
r.ReflectionMethod=0
r.Nanite.ProjectEnabled=False
r.VirtualTextures=True
r.GenerateMeshDistanceFields=True
r.Shadow.Virtual.Enable=0
r.TemporalAA.Upsampling=True
r.RayTracing=False
r.Lumen.HardwareRayTracing.HitLighting.Allowed=0
r.Lumen.DiffuseIndirect.Allow=0
r.Lumen.Reflections.Allow=0
r.ScreenPercentage=100
r.DynamicRes.OperationMode=0

[/Script/WindowsTargetPlatform.WindowsTargetSettings]
DefaultGraphicsRHI=DefaultGraphicsRHI_DX12
+D3D12TargetedShaderFormats=PCD3D_SM5
+D3D12TargetedShaderFormats=PCD3D_SM6

[/Script/Engine.Engine]
bAllowMultiThreadedShaderCompile=True

[/Script/AndroidFileServerEditor.AndroidFileServerRuntimeSettings]
'@
Set-Content $EngineIni $ini -Encoding utf8
Write-Host 'DefaultEngine.ini updated.' -ForegroundColor Green
Report 'DefaultEngine.ini: UPDATED'

Step '5. VERIFY SAREMBOK PLUGINS'
try{
 $j=Get-Content $ProjectFile -Raw|ConvertFrom-Json
 foreach($n in @('SarembokBridge','SarembokAvatar','SarembokVoice','SarembokVision','SarembokAgent','SarembokMemory')){
  $x=$j.Plugins|Where-Object Name -eq $n
  if($x -and $x.Enabled){Write-Host "$n : ENABLED" -ForegroundColor Green;Report "$n : ENABLED"}
  else{Write-Host "$n : NOT ENABLED / MISSING" -ForegroundColor Yellow;Report "$n : NOT ENABLED / MISSING"}
 }
}catch{Report "uproject parse warning: $($_.Exception.Message)"}

Step '6. CLEAR GENERATED PROJECT STATE'
foreach($d in @((Join-Path $ProjectRoot 'Binaries'),(Join-Path $ProjectRoot 'Intermediate'),(Join-Path $ProjectRoot '.vs'))){
 if(Test-Path $d){Write-Host "Removing $d" -ForegroundColor Yellow;Remove-Item $d -Recurse -Force -ErrorAction SilentlyContinue;Report "Removed: $d"}
}
$ddc=Join-Path $ProjectRoot 'DerivedDataCache'
if(Test-Path $ddc){Remove-Item $ddc -Recurse -Force -ErrorAction SilentlyContinue;Report 'Removed project DerivedDataCache'}

Step '7. REGENERATE PROJECT FILES'
& $UBT -projectfiles "-project=$ProjectFile" -game -rocket -progress
if($LASTEXITCODE -ne 0){throw "Project-file generation failed: exit code $LASTEXITCODE"}

if($SkipBuild){Step '8. BUILD SKIPPED'}else{
 Step '8. BUILD SAREMBOK VE EDITOR'
 & $BuildBat SarembokVEEditor Win64 Development "-Project=$ProjectFile" -WaitMutex
 if($LASTEXITCODE -ne 0){throw "SarembokVEEditor build failed: exit code $LASTEXITCODE"}
 Write-Host 'BUILD SUCCESSFUL' -ForegroundColor Green
}

Step '9. FINAL CHECK'
foreach($x in @(
 @{N='Project';P=$ProjectFile},
 @{N='DefaultEngine.ini';P=$EngineIni},
 @{N='Project Binaries';P=(Join-Path $ProjectRoot 'Binaries\Win64')}
)){
 if(Test-Path $x.P){Write-Host "$($x.N): OK" -ForegroundColor Green;Report "$($x.N): OK"}
 else{Write-Host "$($x.N): MISSING" -ForegroundColor Yellow;Report "$($x.N): MISSING"}
}

Step 'COMPLETE'
Write-Host 'SAREMBOK VE RENDERING REPAIR COMPLETE' -ForegroundColor Green
Write-Host "Backup: $Backup"
Write-Host "Report: $Report"
Write-Host ''
Write-Host 'Next: launch SarembokVEEditor and check the rendering popup.' -ForegroundColor Cyan
Report 'RESULT: COMPLETE'
