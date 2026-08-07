#include "SarembokRuntimeConnector.h"

void USarembokRuntimeConnector::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    RuntimeAddress = TEXT("ws://127.0.0.1:8765");
}

void USarembokRuntimeConnector::Deinitialize()
{
    bConnected = false;
    Super::Deinitialize();
}

void USarembokRuntimeConnector::ConnectRuntime()
{
    // WebSocket transport binding is connected in the next integration pass.
    bConnected = true;
}

void USarembokRuntimeConnector::SendCommand(const FString& CommandJson)
{
    if (!bConnected)
    {
        return;
    }

    // Command dispatch hook for SarembokBridge WebSocket client.
}
