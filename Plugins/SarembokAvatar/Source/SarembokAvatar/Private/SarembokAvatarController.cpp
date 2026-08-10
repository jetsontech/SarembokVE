#include "SarembokAvatarController.h"
#include "GameFramework/Actor.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "UObject/UnrealType.h"

USarembokAvatarController::USarembokAvatarController()
{
    PrimaryComponentTick.bCanEverTick = true;
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

    if (UWorld* World = GetWorld())
    {
        if (UGameInstance* GI = World->GetGameInstance())
        {
            UClass* SubClass = UClass::TryFindTypeSlow<UClass>(TEXT("SarembokRuntimeSubsystem"));
            if (SubClass)
            {
                if (USubsystem* Sub = GI->GetSubsystemBase(SubClass))
                {
                    if (FMulticastDelegateProperty* Prop = CastField<FMulticastDelegateProperty>(SubClass->FindPropertyByName(FName(TEXT("OnEmotionSet")))))
                    {
                        const FMulticastScriptDelegate* EventDel = Prop->GetMulticastDelegate(Prop->ContainerPtrToValuePtr<void>(Sub));
                        if (EventDel)
                        {
                            FScriptDelegate Delegate;
                            Delegate.BindUFunction(this, FName(TEXT("SetEmotion")));
                            const_cast<FMulticastScriptDelegate*>(EventDel)->AddUnique(Delegate);
                        }
                    }
                }
            }
        }
    }
}

void USarembokAvatarController::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

    const float InterpSpeed = 8.0f;
    CurrentPose.BrowInnerUp   = FMath::FInterpTo(CurrentPose.BrowInnerUp,   TargetPose.BrowInnerUp,   DeltaTime, InterpSpeed);
    CurrentPose.BrowDownLeft  = FMath::FInterpTo(CurrentPose.BrowDownLeft,  TargetPose.BrowDownLeft,  DeltaTime, InterpSpeed);
    CurrentPose.BrowDownRight = FMath::FInterpTo(CurrentPose.BrowDownRight, TargetPose.BrowDownRight, DeltaTime, InterpSpeed);
    CurrentPose.EyeWideLeft   = FMath::FInterpTo(CurrentPose.EyeWideLeft,   TargetPose.EyeWideLeft,   DeltaTime, InterpSpeed);
    CurrentPose.EyeWideRight  = FMath::FInterpTo(CurrentPose.EyeWideRight,  TargetPose.EyeWideRight,  DeltaTime, InterpSpeed);
    CurrentPose.EyeSquintLeft = FMath::FInterpTo(CurrentPose.EyeSquintLeft, TargetPose.EyeSquintLeft, DeltaTime, InterpSpeed);
    CurrentPose.EyeSquintRight= FMath::FInterpTo(CurrentPose.EyeSquintRight,TargetPose.EyeSquintRight,DeltaTime, InterpSpeed);
    CurrentPose.MouthSmileLeft= FMath::FInterpTo(CurrentPose.MouthSmileLeft,TargetPose.MouthSmileLeft,DeltaTime, InterpSpeed);
    CurrentPose.MouthSmileRight=FMath::FInterpTo(CurrentPose.MouthSmileRight,TargetPose.MouthSmileRight,DeltaTime,InterpSpeed);
    CurrentPose.MouthFrownLeft= FMath::FInterpTo(CurrentPose.MouthFrownLeft,TargetPose.MouthFrownLeft,DeltaTime, InterpSpeed);
    CurrentPose.MouthFrownRight=FMath::FInterpTo(CurrentPose.MouthFrownRight,TargetPose.MouthFrownRight,DeltaTime,InterpSpeed);
    CurrentPose.JawOpen       = FMath::FInterpTo(CurrentPose.JawOpen,       TargetPose.JawOpen,       DeltaTime, InterpSpeed);

    ApplyFacialPose(CurrentPose);
}

void USarembokAvatarController::SetEmotion(const FString& Emotion)
{
    CurrentEmotion = Emotion;
    TargetPose = GetPoseForEmotion(Emotion);

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
    return CurrentPose;
}
