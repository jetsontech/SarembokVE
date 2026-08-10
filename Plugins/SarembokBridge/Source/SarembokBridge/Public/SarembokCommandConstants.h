// ============================================================
// SarembokCommandConstants.h
// Authoritative JSON Command Protocol & Constants
// ============================================================

#pragma once

#include "CoreMinimal.h"

namespace SarembokCommandConstants
{
    // Recognized Commands
    static const FString Emotion = TEXT("Emotion");
    static const FString Speak   = TEXT("Speak");
    static const FString Chat    = TEXT("Chat");
    static const FString Facial  = TEXT("Facial");
    static const FString Gesture = TEXT("Gesture");

    // Command Targets
    static const FString TargetAvatar = TEXT("Avatar");
    static const FString TargetVoice  = TEXT("Voice");
    static const FString TargetSystem = TEXT("System");

    // JSON Protocol Field Keys
    static const FString KeyCommand = TEXT("command");
    static const FString KeyTarget  = TEXT("target");
    static const FString KeyPayload = TEXT("payload");
    static const FString KeyState   = TEXT("state");
    static const FString KeyText    = TEXT("text");
    static const FString KeyEmotion = TEXT("emotion");

    // Default Connection Parameters
    static const FString DefaultWebSocketURL = TEXT("ws://127.0.0.1:9000");
}
