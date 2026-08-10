// ============================================================
// SarembokCapabilityRegistry.h
// Platform Capability Registry — Sarembok_VE v2.0
// ============================================================
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokCapabilityRegistry.generated.h"

UENUM(BlueprintType)
enum class ECapabilityCostClass : uint8
{
    Trivial    UMETA(DisplayName="Trivial"),
    Low        UMETA(DisplayName="Low"),
    Medium     UMETA(DisplayName="Medium"),
    High       UMETA(DisplayName="High"),
    Critical   UMETA(DisplayName="Critical")
};

UENUM(BlueprintType)
enum class ECapabilityRiskLevel : uint8
{
    Safe        UMETA(DisplayName="Safe"),
    Mild        UMETA(DisplayName="Mild"),
    Moderate    UMETA(DisplayName="Moderate"),
    Elevated    UMETA(DisplayName="Elevated"),
    Dangerous   UMETA(DisplayName="Dangerous")
};

USTRUCT(BlueprintType)
struct FSarembokCapabilityDescriptor
{
    GENERATED_BODY()

    UPROPERTY() FString            CapabilityId;
    UPROPERTY() FString            Schema;
    UPROPERTY() FString            PermissionRequired;
    UPROPERTY() ECapabilityCostClass  CostClass;
    UPROPERTY() ECapabilityRiskLevel  RiskLevel;
    UPROPERTY() TArray<FString>    Prerequisites;
    UPROPERTY() FString            ExecutionHandlerName;
    UPROPERTY() FString            Description;
};

UCLASS()
class SAREMBOKCORE_API USarembokCapabilityRegistry : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Platform")
    void RegisterCapability(const FSarembokCapabilityDescriptor& Descriptor);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Platform")
    bool HasCapability(const FString& CapabilityId) const;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Platform")
    FSarembokCapabilityDescriptor GetCapability(const FString& CapabilityId) const;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Platform")
    TArray<FString> GetAllCapabilityIds() const;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Platform")
    TArray<FSarembokCapabilityDescriptor> GetCapabilitiesByRiskLevel(ECapabilityRiskLevel MaxRisk) const;

private:
    TMap<FString, FSarembokCapabilityDescriptor> Registry;

    void RegisterBuiltinCapabilities();
};
