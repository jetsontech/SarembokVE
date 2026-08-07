#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "SarembokAvatarManager.generated.h"

UENUM(BlueprintType)
enum class ESarembokAvatarState : uint8
{
    Uninitialized UMETA(DisplayName="Uninitialized"),
    Loading UMETA(DisplayName="Loading"),
    Ready UMETA(DisplayName="Ready"),
    Speaking UMETA(DisplayName="Speaking"),
    Listening UMETA(DisplayName="Listening"),
    Thinking UMETA(DisplayName="Thinking"),
    Disabled UMETA(DisplayName="Disabled")
};

USTRUCT(BlueprintType)
struct FSarembokEmotionState
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Sarembok|Avatar")
    FString Name = TEXT("neutral");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Sarembok|Avatar")
    float Intensity = 0.0f;
};

UCLASS(Blueprintable)
class SAREMBOKAVATAR_API USarembokAvatarManager : public UObject
{
    GENERATED_BODY()

public:
    USarembokAvatarManager();

    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void InitializeAvatar();

    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void ShutdownAvatar();

    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void SetAvatarState(ESarembokAvatarState NewState);

    UFUNCTION(BlueprintPure, Category="Sarembok|Avatar")
    ESarembokAvatarState GetAvatarState() const;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void TriggerExpression(const FString& ExpressionName);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void SetEmotion(const FString& Emotion, float Intensity = 1.0f);

    UFUNCTION(BlueprintPure, Category="Sarembok|Avatar")
    FSarembokEmotionState GetEmotion() const;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void SynchronizeVoice(const FString& AudioReference);

private:
    UPROPERTY()
    ESarembokAvatarState CurrentState;

    UPROPERTY()
    FSarembokEmotionState CurrentEmotion;
};
