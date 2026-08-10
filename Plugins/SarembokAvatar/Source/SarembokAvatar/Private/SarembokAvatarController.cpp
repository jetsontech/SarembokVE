#include "SarembokAvatarController.h"
#include "GameFramework/Actor.h"

USarembokAvatarController::USarembokAvatarController()
{
    PrimaryComponentTick.bCanEverTick = false;
    CurrentEmotion = TEXT("Neutral");
}

void USarembokAvatarController::BeginPlay()
{
    Super::BeginPlay();

    if (AActor* Owner = GetOwner())
    {
        USkeletalMeshComponent* MeshComp = Owner->FindComponentByClass<USkeletalMeshComponent>();
        if (MeshComp)
        {
            CachedFaceMesh = MeshComp;
        }
    }
}

void USarembokAvatarController::SetEmotion(const FString& Emotion)
{
    CurrentEmotion = Emotion;

    FSarembokFacialPose Pose = GetPoseForEmotion(Emotion);
    ApplyFacialPose(Pose);

    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK] AVATAR EMOTION EXECUTED | %s"),
        *Emotion
    );
}

FSarembokFacialPose USarembokAvatarController::GetPoseForEmotion(const FString& Emotion)
{
    FSarembokFacialPose Pose;

    if (Emotion.Equals(TEXT("Happy"), ESearchCase::IgnoreCase) ||
        Emotion.Equals(TEXT("Joyful"), ESearchCase::IgnoreCase))
    {
        Pose.MouthSmileLeft  = 0.8f;
        Pose.MouthSmileRight = 0.8f;
        Pose.BrowInnerUp     = 0.3f;
        Pose.JawOpen         = 0.1f;
    }
    else if (Emotion.Equals(TEXT("Sad"), ESearchCase::IgnoreCase))
    {
        Pose.MouthFrownLeft  = 0.7f;
        Pose.MouthFrownRight = 0.7f;
        Pose.EyeSquintLeft   = 0.3f;
        Pose.EyeSquintRight  = 0.3f;
    }
    else if (Emotion.Equals(TEXT("Angry"), ESearchCase::IgnoreCase))
    {
        Pose.BrowDownLeft   = 0.9f;
        Pose.BrowDownRight  = 0.9f;
        Pose.MouthFrownLeft = 0.4f;
        Pose.MouthFrownRight= 0.4f;
    }
    else if (Emotion.Equals(TEXT("Surprised"), ESearchCase::IgnoreCase))
    {
        Pose.BrowInnerUp   = 0.9f;
        Pose.EyeWideLeft   = 0.8f;
        Pose.EyeWideRight  = 0.8f;
        Pose.JawOpen       = 0.6f;
    }

    return Pose;
}

void USarembokAvatarController::ApplyFacialPose(const FSarembokFacialPose& Pose)
{
    if (USkeletalMeshComponent* Mesh = CachedFaceMesh.Get())
    {
        Mesh->SetMorphTarget(FName(TEXT("BrowInnerUp")),     Pose.BrowInnerUp);
        Mesh->SetMorphTarget(FName(TEXT("BrowDownLeft")),    Pose.BrowDownLeft);
        Mesh->SetMorphTarget(FName(TEXT("BrowDownRight")),   Pose.BrowDownRight);
        Mesh->SetMorphTarget(FName(TEXT("EyeWideLeft")),     Pose.EyeWideLeft);
        Mesh->SetMorphTarget(FName(TEXT("EyeWideRight")),    Pose.EyeWideRight);
        Mesh->SetMorphTarget(FName(TEXT("EyeSquintLeft")),   Pose.EyeSquintLeft);
        Mesh->SetMorphTarget(FName(TEXT("EyeSquintRight")),  Pose.EyeSquintRight);
        Mesh->SetMorphTarget(FName(TEXT("MouthSmileLeft")),  Pose.MouthSmileLeft);
        Mesh->SetMorphTarget(FName(TEXT("MouthSmileRight")), Pose.MouthSmileRight);
        Mesh->SetMorphTarget(FName(TEXT("MouthFrownLeft")),  Pose.MouthFrownLeft);
        Mesh->SetMorphTarget(FName(TEXT("MouthFrownRight")), Pose.MouthFrownRight);
        Mesh->SetMorphTarget(FName(TEXT("JawOpen")),         Pose.JawOpen);
    }
}

void USarembokAvatarController::LookAtTarget(AActor* Target)
{
    if (Target)
    {
        UE_LOG(
            LogTemp,
            Display,
            TEXT("[SAREMBOK] Avatar Looking At: %s"),
            *Target->GetName()
        );
    }
}

FString USarembokAvatarController::GetCurrentEmotion() const
{
    return CurrentEmotion;
}

FSarembokFacialPose USarembokAvatarController::GetCurrentFacialPose() const
{
    return GetPoseForEmotion(CurrentEmotion);
}
