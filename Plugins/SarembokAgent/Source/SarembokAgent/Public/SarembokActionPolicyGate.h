// ============================================================
// SarembokActionPolicyGate.h
// Action Authorization & Policy Safety Gate Subsystem
// ============================================================

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokReasoningProvider.h"
#include "SarembokActionPolicyGate.generated.h"

UENUM(BlueprintType)
enum class EPolicyResult : uint8
{
    ALLOW,
    DENY,
    CONFIRMATION_REQUIRED
};

UCLASS()
class SAREMBOKAGENT_API USarembokActionPolicyGate : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:

    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    UFUNCTION(BlueprintCallable, Category = "Sarembok|PolicyGate")
    EPolicyResult EvaluateIntentPolicy(const FSarembokIntent& Intent);

    UFUNCTION(BlueprintCallable, Category = "Sarembok|PolicyGate")
    void SetStrictPolicyMode(bool bEnableStrict);

    UFUNCTION(BlueprintPure, Category = "Sarembok|PolicyGate")
    bool IsStrictPolicyMode() const;

private:

    bool bStrictPolicyMode = true;
};
