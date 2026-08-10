#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "SarembokAvatarController.generated.h"

USTRUCT(BlueprintType)
struct FSarembokFacialPose
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Avatar")
    float BrowInnerUp = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Avatar")
    float BrowDownLeft = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Avatar")
    float BrowDownRight = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Avatar")
    float EyeWideLeft = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Avatar")
    float EyeWideRight = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Avatar")
    float EyeSquintLeft = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Avatar")
    float EyeSquintRight = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Avatar")
    float MouthSmileLeft = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Avatar")
    float MouthSmileRight = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Avatar")
    float MouthFrownLeft = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Avatar")
    float MouthFrownRight = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Avatar")
    float JawOpen = 0.0f;
};

UCLASS(ClassGroup=(Sarembok), meta=(BlueprintSpawnableComponent))
class SAREMBOKAVATAR_API USarembokAvatarController : public UActorComponent
{
    GENERATED_BODY()

public:

    USarembokAvatarController();

    virtual void BeginPlay() override;

    UFUNCTION(BlueprintCallable, Category="Sarembok Avatar")
    void SetEmotion(const FString& Emotion);

    UFUNCTION(BlueprintCallable, Category="Sarembok Avatar")
    void LookAtTarget(AActor* Target);

    UFUNCTION(BlueprintPure, Category="Sarembok Avatar")
    FString GetCurrentEmotion() const;

    UFUNCTION(BlueprintPure, Category="Sarembok Avatar")
    FSarembokFacialPose GetCurrentFacialPose() const;

    UFUNCTION(BlueprintCallable, Category="Sarembok Avatar")
    static FSarembokFacialPose GetPoseForEmotion(const FString& Emotion);

private:

    void ApplyFacialPose(const FSarembokFacialPose& Pose);

    FString CurrentEmotion;

    UPROPERTY()
    TWeakObjectPtr<USkeletalMeshComponent> CachedFaceMesh;
};
