# ============================================================
# Create-SarembokAvatarComponentHeader.ps1
# Sarembok VE Avatar Runtime Component
# ============================================================

$ProjectRoot = "C:\Sarembok_VE"

$Path = Join-Path $ProjectRoot `
"Plugins\SarembokAvatar\Source\SarembokAvatar\Public\SarembokAvatarComponent.h"

$Dir = Split-Path $Path -Parent

if (!(Test-Path $Dir)) {
    New-Item -ItemType Directory -Path $Dir -Force | Out-Null
}


$Content = @'
// ============================================================
// SarembokAvatarComponent.h
// Runtime Avatar Component
// ============================================================

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "SarembokAvatarComponent.generated.h"


class USarembokAvatarManager;


/**
 * Runtime component attached to
 * MetaHuman / Digital Human actors
 */
UCLASS(
    ClassGroup=(Sarembok),
    meta=(BlueprintSpawnableComponent)
)
class SAREMBOKAVATAR_API USarembokAvatarComponent 
    : public UActorComponent
{

    GENERATED_BODY()


public:

    USarembokAvatarComponent();


    virtual void BeginPlay() override;


    /**
     * Initialize avatar runtime
     */
    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void InitializeAvatar();


    /**
     * Send speech event
     */
    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void Speak(
        FString Text
    );


    /**
     * Set avatar identity
     */
    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void SetIdentity(
        FString AvatarID
    );


protected:

    UPROPERTY()
    USarembokAvatarManager* AvatarManager;


    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Sarembok")
    FString Identity;


};
'@


Set-Content `
    -Path $Path `
    -Value $Content `
    -Encoding UTF8


Write-Host ""
Write-Host "Created:"
Write-Host $Path