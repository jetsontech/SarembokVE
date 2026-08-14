#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "SarembokCommandRouter.h"
#include "SarembokAvatarComponent.generated.h"

class USarembokAvatarManager;
class USkeletalMeshComponent;
class UTextToSpeechEngineSubsystem;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FSarembokEmotionEvent, const FString&, State);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FSarembokSpeakEvent, const FString&, Text, const FString&, Emotion);

UCLASS(ClassGroup=(Sarembok), meta=(BlueprintSpawnableComponent))
class SAREMBOKAVATAR_API USarembokAvatarComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    USarembokAvatarComponent();

    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void InitializeAvatar();

    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void SetIdentity(FString AvatarID);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void ApplyEmotion(const FString& State);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void Speak(const FString& Text, const FString& Emotion = TEXT(""));

    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void StopSpeaking();

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Sarembok|Avatar")
    TObjectPtr<USkeletalMeshComponent> FaceMesh;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Sarembok|Avatar")
    FString Identity = TEXT("Sarembok");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Sarembok|Avatar|Morphs")
    FName SmileLeftMorph = TEXT("mouthSmileLeft");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Sarembok|Avatar|Morphs")
    FName SmileRightMorph = TEXT("mouthSmileRight");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Sarembok|Avatar|Morphs")
    FName BrowUpMorph = TEXT("browInnerUp");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Sarembok|Avatar|Morphs")
    FName BrowDownMorph = TEXT("browDownLeft");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Sarembok|Avatar|Morphs")
    FName JawOpenMorph = TEXT("jawOpen");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Sarembok|Avatar|Morphs")
    float EmotionStrength = 0.75f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Sarembok|Avatar|Speech")
    float SpeechRate = 0.55f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Sarembok|Avatar|Speech")
    float SpeechVolume = 1.0f;

    UPROPERTY(BlueprintAssignable, Category="Sarembok|Avatar")
    FSarembokEmotionEvent OnEmotion;

    UPROPERTY(BlueprintAssignable, Category="Sarembok|Avatar")
    FSarembokSpeakEvent OnSpeak;

protected:
    UPROPERTY()
    TObjectPtr<USarembokAvatarManager> AvatarManager;

private:
    void HandleCommand(const FSarembokCommand& Command);
    void SetMorph(FName Name, float Value);
    void ResetEmotionMorphs();
    void EnsureSpeechChannel();

    FDelegateHandle CommandHandle;
    FName SpeechChannel = TEXT("SarembokAvatar");
    float SpeechTime = 0.0f;
    TObjectPtr<UTextToSpeechEngineSubsystem> SpeechSubsystem;
};
