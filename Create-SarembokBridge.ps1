# ==========================================
# Sarembok VE - Create Bridge Plugin
# Unreal Engine 5.8
# ==========================================

$ProjectRoot = Get-Location

$PluginRoot = Join-Path $ProjectRoot "Plugins\SarembokBridge"
$SourceRoot = Join-Path $PluginRoot "Source\SarembokBridge"

$PublicDir = Join-Path $SourceRoot "Public"
$PrivateDir = Join-Path $SourceRoot "Private"

# Create directories

$Folders = @(
    $PluginRoot,
    $SourceRoot,
    $PublicDir,
    $PrivateDir
)

foreach ($Folder in $Folders) {
    if (!(Test-Path $Folder)) {
        New-Item -ItemType Directory -Path $Folder | Out-Null
        Write-Host "Created: $Folder"
    }
}


# -----------------------------
# SarembokBridge.uplugin
# -----------------------------

@'
{
	"FileVersion": 3,
	"Version": 1,
	"VersionName": "0.1.0",
	"FriendlyName": "Sarembok Bridge",
	"Description": "Communication bridge between Sarembok VE and AI Core.",
	"Category": "Sarembok",
	"CreatedBy": "Sarembok VE",
	"CanContainContent": false,
	"Modules": [
		{
			"Name": "SarembokBridge",
			"Type": "Runtime",
			"LoadingPhase": "Default"
		}
	]
}
'@ | Out-File `
    "$PluginRoot\SarembokBridge.uplugin" `
    -Encoding utf8


# -----------------------------
# Build.cs
# -----------------------------

@'
using UnrealBuildTool;

public class SarembokBridge : ModuleRules
{
	public SarembokBridge(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(
			new string[]
			{
				"Core",
				"CoreUObject",
				"Engine"
			}
		);

		PrivateDependencyModuleNames.AddRange(
			new string[]
			{
				"Projects"
			}
		);

		CppStandard = CppStandardVersion.Cpp20;
	}
}
'@ | Out-File `
    "$SourceRoot\SarembokBridge.Build.cs" `
    -Encoding utf8


# -----------------------------
# Header
# -----------------------------

@'
#pragma once

#include "Modules/ModuleManager.h"

class FSarembokBridgeModule : public IModuleInterface
{
public:

	virtual void StartupModule() override;

	virtual void ShutdownModule() override;
};
'@ | Out-File `
    "$PublicDir\SarembokBridgeModule.h" `
    -Encoding utf8


# -----------------------------
# CPP
# -----------------------------

@'
#include "SarembokBridgeModule.h"

void FSarembokBridgeModule::StartupModule()
{
	UE_LOG(
		LogTemp,
		Display,
		TEXT("Sarembok Bridge Initialized")
	);
}


void FSarembokBridgeModule::ShutdownModule()
{
	UE_LOG(
		LogTemp,
		Display,
		TEXT("Sarembok Bridge Shutdown")
	);
}


IMPLEMENT_MODULE(
	FSarembokBridgeModule,
	SarembokBridge
)
'@ | Out-File `
    "$PrivateDir\SarembokBridgeModule.cpp" `
    -Encoding utf8


Write-Host ""
Write-Host "================================="
Write-Host " SarembokBridge Plugin Created"
Write-Host " Unreal Engine 5.8 Ready"
Write-Host "================================="