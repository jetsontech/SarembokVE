#include "SarembokLipSyncComponent.h"

void USarembokLipSyncComponent::ProcessSpeech(const FString& Text)
{
    UE_LOG(LogTemp, Log,
        TEXT("Sarembok Lip Sync Processing: %s"),
        *Text);
}
