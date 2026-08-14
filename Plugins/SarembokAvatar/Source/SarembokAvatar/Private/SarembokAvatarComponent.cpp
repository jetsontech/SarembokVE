#include "SarembokAvatarComponent.h"
#include "SarembokAvatarManager.h"
#include "SarembokCommandBus.h"

#include "Components/SkeletalMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "TextToSpeechEngineSubsystem.h"

USarembokAvatarComponent::USarembokAvatarComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
    AvatarManager = nullptr;
    SpeechSubsystem = nullptr;
}

void USarembokAvatarComponent::BeginPlay()
{
    Super::BeginPlay();

    AvatarManager = NewObject<USarembokAvatarManager>(this);
    InitializeAvatar();

    if (!FaceMesh && GetOwner())
    {
        TArray<USkeletalMeshComponent*> Meshes;
        GetOwner()->GetComponents<USkeletalMeshComponent>(Meshes);

        for (USkeletalMeshComponent* Mesh : Meshes)
        {
            if (Mesh && Mesh->GetName().Contains(TEXT("Face"), ESearchCase::IgnoreCase))
            {
                FaceMesh = Mesh;
                break;
            }
        }
    }

    CommandHandle = FSarembokCommandBus::Get().OnCommand.AddUObject(
        this,
        &USarembokAvatarComponent::HandleCommand
    );

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] Avatar command listener active: %s"), *Identity);
}

void USarembokAvatarComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    FSarembokCommandBus::Get().OnCommand.Remove(CommandHandle);
    StopSpeaking();

    if (AvatarManager)
    {
        AvatarManager->ShutdownAvatar();
    }

    Super::EndPlay(EndPlayReason);
}

void USarembokAvatarComponent::InitializeAvatar()
{
    if (AvatarManager)
    {
        AvatarManager->InitializeAvatar();
        UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] Avatar initialized: %s"), *Identity);
    }
}

void USarembokAvatarComponent::SetIdentity(FString AvatarID)
{
    Identity = MoveTemp(AvatarID);
}

void USarembokAvatarComponent::HandleCommand(const FSarembokCommand& Command)
{
    if (!Command.Target.IsEmpty() && !Command.Target.Equals(TEXT("Avatar"), ESearchCase::IgnoreCase))
    {
        return;
    }

    if (Command.Command.Equals(TEXT("Emotion"), ESearchCase::IgnoreCase))
    {
        FString State;
        TSharedPtr<FJsonObject> Payload;
        TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Command.Payload);

        if (FJsonSerializer::Deserialize(Reader, Payload) && Payload.IsValid())
        {
            Payload->TryGetStringField(TEXT("state"), State);
        }

        if (!State.IsEmpty())
        {
            ApplyEmotion(State);
        }
        return;
    }

    if (Command.Command.Equals(TEXT("Speak"), ESearchCase::IgnoreCase))
    {
        FString Text;
        FString Emotion;
        TSharedPtr<FJsonObject> Payload;
        TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Command.Payload);

        if (FJsonSerializer::Deserialize(Reader, Payload) && Payload.IsValid())
        {
            Payload->TryGetStringField(TEXT("text"), Text);
            Payload->TryGetStringField(TEXT("emotion"), Emotion);
        }

        if (!Text.IsEmpty())
        {
            Speak(Text, Emotion);
        }
    }
}

void USarembokAvatarComponent::SetMorph(FName Name, float Value)
{
    if (!FaceMesh || Name.IsNone())
    {
        return;
    }

    if (FaceMesh->FindMorphTarget(Name))
    {
        FaceMesh->SetMorphTarget(Name, FMath::Clamp(Value, 0.0f, 1.0f));
    }
}

void USarembokAvatarComponent::ResetEmotionMorphs()
{
    SetMorph(SmileLeftMorph, 0.0f);
    SetMorph(SmileRightMorph, 0.0f);
    SetMorph(BrowUpMorph, 0.0f);
    SetMorph(BrowDownMorph, 0.0f);
}

void USarembokAvatarComponent::ApplyEmotion(const FString& State)
{
    ResetEmotionMorphs();

    const FString Normalized = State.ToLower();

    if (Normalized == TEXT("friendly") || Normalized == TEXT("happy") || Normalized == TEXT("joy"))
    {
        SetMorph(SmileLeftMorph, EmotionStrength);
        SetMorph(SmileRightMorph, EmotionStrength);
        SetMorph(BrowUpMorph, EmotionStrength * 0.35f);
    }
    else if (Normalized == TEXT("surprised") || Normalized == TEXT("surprise"))
    {
        SetMorph(BrowUpMorph, EmotionStrength);
        SetMorph(JawOpenMorph, EmotionStrength * 0.35f);
    }
    else if (Normalized == TEXT("angry") || Normalized == TEXT("anger"))
    {
        SetMorph(BrowDownMorph, EmotionStrength);
    }
    else if (Normalized == TEXT("sad"))
    {
        SetMorph(BrowUpMorph, EmotionStrength * 0.25f);
    }

    if (AvatarManager)
    {
        AvatarManager->TriggerExpression(State);
    }

    OnEmotion.Broadcast(State);
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] Avatar emotion: %s"), *State);
}

void USarembokAvatarComponent::EnsureSpeechChannel()
{
    if (!GEngine)
    {
        return;
    }

    SpeechSubsystem = GEngine->GetEngineSubsystem<UTextToSpeechEngineSubsystem>();

    if (!SpeechSubsystem)
    {
        UE_LOG(LogTemp, Warning, TEXT("[SAREMBOK] TextToSpeech subsystem unavailable"));
        return;
    }

    if (!SpeechSubsystem->DoesChannelExist(SpeechChannel))
    {
        SpeechSubsystem->AddDefaultChannel(SpeechChannel);
    }

    if (!SpeechSubsystem->IsChannelActive(SpeechChannel))
    {
        SpeechSubsystem->ActivateChannel(SpeechChannel);
    }

    SpeechSubsystem->SetRateOnChannel(SpeechChannel, SpeechRate);
    SpeechSubsystem->SetVolumeOnChannel(SpeechChannel, SpeechVolume);
}

void USarembokAvatarComponent::Speak(const FString& Text, const FString& Emotion)
{
    if (!Emotion.IsEmpty())
    {
        ApplyEmotion(Emotion);
    }

    EnsureSpeechChannel();

    if (SpeechSubsystem)
    {
        SpeechSubsystem->SpeakOnChannel(SpeechChannel, Text);
        PrimaryComponentTick.bCanEverTick = true;
        SetComponentTickEnabled(true);
        SpeechTime = 0.0f;
    }

    if (AvatarManager)
    {
        AvatarManager->SynchronizeVoice(Text);
    }

    OnSpeak.Broadcast(Text, Emotion);
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] Avatar speaking: %s"), *Text);
}

void USarembokAvatarComponent::StopSpeaking()
{
    if (SpeechSubsystem && SpeechSubsystem->DoesChannelExist(SpeechChannel))
    {
        SpeechSubsystem->StopSpeakingOnChannel(SpeechChannel);
    }

    SetMorph(JawOpenMorph, 0.0f);
    SetComponentTickEnabled(false);
}

void USarembokAvatarComponent::TickComponent(
    float DeltaTime,
    ELevelTick TickType,
    FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

    if (!SpeechSubsystem || !SpeechSubsystem->IsSpeakingOnChannel(SpeechChannel))
    {
        SetMorph(JawOpenMorph, 0.0f);
        SetComponentTickEnabled(false);
        return;
    }

    SpeechTime += DeltaTime;
    const float Mouth = 0.12f + 0.42f * (0.5f + 0.5f * FMath::Sin(SpeechTime * 15.0f));
    SetMorph(JawOpenMorph, Mouth);
}
