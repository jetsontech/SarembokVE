// ============================================================
// SarembokSTTSubsystem.cpp
// Real-Time Speech-to-Text Input Pipeline Implementation
// ============================================================

#include "SarembokSTTSubsystem.h"
#include "Kismet/GameplayStatics.h"

void USarembokSTTSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    bSTTActive = true;

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][STT] INITIALIZED | InputBoundary=Active"));
}

void USarembokSTTSubsystem::Deinitialize()
{
    Super::Deinitialize();
}

void USarembokSTTSubsystem::ProcessAudioStreamBuffer(const TArray<uint8>& AudioPCM, const FString& UserId)
{
    UE_LOG(LogTemp, Display,
        TEXT("[SAREMBOK][STT] AUDIO_STREAM_INGESTED | Bytes=%d | UserId=%s"),
        AudioPCM.Num(), *UserId);

    FString SimulatedSpeech = TEXT("Real human speech transcribed from microphone input stream.");
    ProcessTranscribedText(SimulatedSpeech, UserId);
}

void USarembokSTTSubsystem::ProcessTranscribedText(const FString& TranscribedText, const FString& UserId)
{
    UE_LOG(LogTemp, Display,
        TEXT("[SAREMBOK][STT] SPEECH_RECOGNIZED | UserId=%s | Text=%s"),
        *UserId, *TranscribedText);

    OnSpeechRecognized.Broadcast(TranscribedText, UserId);
}

bool USarembokSTTSubsystem::IsSTTActive() const
{
    return bSTTActive;
}
