#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokRuntimeConnector.generated.h"

UCLASS()
class SAREMBOKBRIDGE_API USarembokRuntimeConnector : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    UFUNCTION(BlueprintCallable, Category="Sarembok")
    void ConnectRuntime();

    UFUNCTION(BlueprintCallable, Category="Sarembok")
    void SendCommand(const FString& CommandJson);

private:
    FString RuntimeAddress;
    bool bConnected = false;
};
