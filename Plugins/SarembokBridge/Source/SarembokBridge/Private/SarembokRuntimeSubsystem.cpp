#include "SarembokRuntimeSubsystem.h"

void USarembokRuntimeSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);

    bInitialized = true;

    UE_LOG(LogTemp, Log, TEXT("Sarembok Runtime Subsystem Initialized"));
}

void USarembokRuntimeSubsystem::Deinitialize()
{
    bInitialized = false;

    UE_LOG(LogTemp, Log, TEXT("Sarembok Runtime Subsystem Shutdown"));

    Super::Deinitialize();
}

void USarembokRuntimeSubsystem::Speak(const FString& Message)
{
    UE_LOG(LogTemp, Log, TEXT("Sarembok Speak: %s"), *Message);
}

void USarembokRuntimeSubsystem::SetEmotion(const FString& Emotion)
{
    UE_LOG(LogTemp, Log, TEXT("Sarembok Emotion: %s"), *Emotion);
}

void USarembokRuntimeSubsystem::Observe(const FString& Target)
{
    UE_LOG(LogTemp, Log, TEXT("Sarembok Observe: %s"), *Target);
}
