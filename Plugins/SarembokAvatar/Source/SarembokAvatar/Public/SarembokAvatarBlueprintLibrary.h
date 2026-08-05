// ============================================================
// SarembokAvatarBlueprintLibrary.h
// Blueprint Interface Layer
// ============================================================

#pragma once

#include "Kismet/BlueprintFunctionLibrary.h"
#include "SarembokAvatarBlueprintLibrary.generated.h"


class USarembokAvatarComponent;


/**
 * Sarembok Avatar Blueprint Utilities
 */
UCLASS()
class SAREMBOKAVATAR_API USarembokAvatarBlueprintLibrary 
    : public UBlueprintFunctionLibrary
{

    GENERATED_BODY()


public:


    /**
     * Initialize Avatar Component
     */
    UFUNCTION(
        BlueprintCallable,
        Category="Sarembok|Avatar"
    )
    static void InitializeSarembokAvatar(
        USarembokAvatarComponent* Component
    );


    /**
     * Send speech command
     */
    UFUNCTION(
        BlueprintCallable,
        Category="Sarembok|Avatar"
    )
    static void AvatarSpeak(
        USarembokAvatarComponent* Component,
        FString Text
    );


};
