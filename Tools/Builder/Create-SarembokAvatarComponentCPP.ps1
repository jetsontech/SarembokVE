# ============================================================
# Create-SarembokAvatarComponentCPP.ps1
# Sarembok VE Avatar Runtime Component Implementation
# ============================================================

$ProjectRoot = "C:\Sarembok_VE"

$CPPPath = Join-Path $ProjectRoot `
"Plugins\SarembokAvatar\Source\SarembokAvatar\Private\SarembokAvatarComponent.cpp"

$Dir = Split-Path $CPPPath -Parent


if (!(Test-Path $Dir)) {
    New-Item `
        -ItemType Directory `
        -Path $Dir `
        -Force | Out-Null
}


$Content = @'

// ============================================================
// SarembokAvatarComponent.cpp
// ============================================================

#include "SarembokAvatarComponent.h"
#include "SarembokAvatarManager.h"


USarembokAvatarComponent::USarembokAvatarComponent()
{
    PrimaryComponentTick.bCanEverTick = false;

    AvatarManager = nullptr;

    Identity = TEXT("DefaultAvatar");
}



void USarembokAvatarComponent::BeginPlay()
{
    Super::BeginPlay();


    AvatarManager = NewObject<USarembokAvatarManager>(
        this
    );


    InitializeAvatar();
}



void USarembokAvatarComponent::InitializeAvatar()
{
    if (AvatarManager)
    {
        AvatarManager->InitializeAvatar();

        UE_LOG(
            LogTemp,
            Display,
            TEXT("Sarembok Avatar Component Initialized: %s"),
            *Identity
        );
    }
}



void USarembokAvatarComponent::Speak(
    FString Text
)
{
    if (AvatarManager)
    {
        AvatarManager->SynchronizeVoice(
            Text
        );


        UE_LOG(
            LogTemp,
            Display,
            TEXT("Avatar Speaking: %s"),
            *Text
        );
    }
}



void USarembokAvatarComponent::SetIdentity(
    FString AvatarID
)
{
    Identity = AvatarID;


    UE_LOG(
        LogTemp,
        Display,
        TEXT("Avatar Identity Set: %s"),
        *Identity
    );
}

'@


Set-Content `
    -Path $CPPPath `
    -Value $Content `
    -Encoding UTF8


Write-Host ""
Write-Host "Created:"
Write-Host $CPPPath
Write-Host ""