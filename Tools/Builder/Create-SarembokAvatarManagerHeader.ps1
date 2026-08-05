# ============================================================
# Create-SarembokAvatarManagerHeader.ps1
# Sarembok VE - Avatar Plugin Header Generator
# ============================================================

$ProjectRoot = "C:\Sarembok_VE"

$HeaderPath = Join-Path $ProjectRoot `
"Plugins\SarembokAvatar\Source\SarembokAvatar\Public\SarembokAvatarManager.h"

$HeaderDirectory = Split-Path $HeaderPath -Parent


Write-Host ""
Write-Host "========================================"
Write-Host " Sarembok Avatar Manager Header Creator"
Write-Host "========================================"
Write-Host ""

# Create directory tree
if (!(Test-Path $HeaderDirectory)) {

    Write-Host "Creating directory:"
    Write-Host $HeaderDirectory

    New-Item `
        -ItemType Directory `
        -Path $HeaderDirectory `
        -Force | Out-Null
}


$HeaderContent = @'
// ============================================================
// SarembokAvatarManager.h
// Sarembok Autonomous AI Virtual Entity Platform
// Avatar Runtime Manager
// ============================================================

#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "SarembokAvatarManager.generated.h"


/**
 * Avatar lifecycle state
 */
UENUM(BlueprintType)
enum class ESarembokAvatarState : uint8
{
    Uninitialized UMETA(DisplayName="Uninitialized"),
    Loading       UMETA(DisplayName="Loading"),
    Ready         UMETA(DisplayName="Ready"),
    Speaking      UMETA(DisplayName="Speaking"),
    Listening     UMETA(DisplayName="Listening"),
    Thinking      UMETA(DisplayName="Thinking"),
    Disabled      UMETA(DisplayName="Disabled")
};


/**
 * Sarembok Avatar Runtime Manager
 *
 * Controls:
 * - Digital human lifecycle
 * - Avatar state
 * - Animation communication
 * - Voice synchronization
 * - AI runtime events
 */
UCLASS(Blueprintable)
class SAREMBOKAVATAR_API USarembokAvatarManager : public UObject
{

    GENERATED_BODY()


public:

    USarembokAvatarManager();


    /**
     * Initialize Avatar subsystem
     */
    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void InitializeAvatar();


    /**
     * Shutdown Avatar subsystem
     */
    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void ShutdownAvatar();


    /**
     * Update avatar state
     */
    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void SetAvatarState(
        ESarembokAvatarState NewState
    );


    /**
     * Get current avatar state
     */
    UFUNCTION(BlueprintPure, Category="Sarembok|Avatar")
    ESarembokAvatarState GetAvatarState() const;


    /**
     * Trigger facial animation
     */
    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void TriggerExpression(
        FString ExpressionName
    );


    /**
     * Synchronize speech animation
     */
    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void SynchronizeVoice(
        FString AudioReference
    );


private:

    UPROPERTY()
    ESarembokAvatarState CurrentState;


};

'@


Write-Host "Writing header..."

Set-Content `
    -Path $HeaderPath `
    -Value $HeaderContent `
    -Encoding UTF8


Write-Host ""
Write-Host "SUCCESS:"
Write-Host $HeaderPath
Write-Host ""