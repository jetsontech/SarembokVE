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
