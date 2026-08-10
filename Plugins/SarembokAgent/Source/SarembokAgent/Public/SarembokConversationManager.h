// ============================================================
// SarembokConversationManager.h
// Multi-Turn Conversational State & Dialog Manager Subsystem
// ============================================================

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokConversationManager.generated.h"

USTRUCT(BlueprintType)
struct FSarembokUserState
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Conversation")
    bool bPresent = false;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Conversation")
    float Distance = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Conversation")
    FString UserId = TEXT("User_01");
};

USTRUCT(BlueprintType)
struct FSarembokConversationalState
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Conversation")
    FString ConversationId = TEXT("conv-000001");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Conversation")
    int32 TurnId = 0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Conversation")
    FSarembokUserState UserState;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Conversation")
    FString IntentType = TEXT("general");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Conversation")
    float IntentConfidence = 1.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Conversation")
    FString ActiveGoalDescription;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Conversation")
    TArray<FString> RecentTopics;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FOnSarembokConversationTurnSignature, int32, TurnId, const FString&, UserSpeech);

UCLASS()
class SAREMBOKAGENT_API USarembokConversationManager : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:

    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    UFUNCTION(BlueprintCallable, Category="Sarembok Conversation")
    void ProcessUserTurn(const FString& UserSpeech);

    UFUNCTION(BlueprintCallable, Category="Sarembok Conversation")
    void UpdateUserPresence(bool bPresent, float Distance);

    UFUNCTION(BlueprintPure, Category="Sarembok Conversation")
    const FSarembokConversationalState& GetConversationalState() const;

    UFUNCTION(BlueprintCallable, Category="Sarembok Conversation")
    void ResetConversation();

    UPROPERTY(BlueprintAssignable, Category="Sarembok|Events")
    FOnSarembokConversationTurnSignature OnConversationTurn;

private:

    FSarembokConversationalState State;
};
