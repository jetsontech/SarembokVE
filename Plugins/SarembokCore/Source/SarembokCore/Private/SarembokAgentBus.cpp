// ============================================================
// SarembokAgentBus.cpp
// Inter-Agent Event Bus & Governed Messaging Envelope — Sarembok_VE v2.1
// ============================================================
#include "SarembokAgentBus.h"
#include "Misc/Guid.h"

void USarembokAgentBus::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][AGENT_BUS] SarembokAgentBus ONLINE | v2.1"));
}

FString USarembokAgentBus::SendMessage(const FAgentMessage& Message)
{
    FAgentMessage Msg = Message;
    if (Msg.MessageId.IsEmpty())
    {
        Msg.MessageId = FString::Printf(TEXT("msg-%s"), *FGuid::NewGuid().ToString(EGuidFormats::Short));
    }
    if (Msg.Timestamp.IsEmpty())
    {
        Msg.Timestamp = FDateTime::UtcNow().ToString();
    }
    if (Msg.TTLSeconds <= 0.0f)
    {
        Msg.TTLSeconds = 60.0f; // 60s default TTL
    }

    Msg.bCancelled = false;

    MessageStore.Add(Msg.MessageId, Msg);
    OutboxPerAgent.FindOrAdd(Msg.TargetAgentId).Add(Msg);
    TotalMessagesRouted++;

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][AGENT_BUS] Message routed | MsgId=%s | Src=%s | Tgt=%s | Type=%d"),
        *Msg.MessageId, *Msg.SourceAgentId, *Msg.TargetAgentId, (int32)Msg.MessageType);

    return Msg.MessageId;
}

void USarembokAgentBus::SubscribeTopic(const FString& AgentId, const FString& Topic)
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][AGENT_BUS] Agent '%s' subscribed to topic '%s'"), *AgentId, *Topic);
}

TArray<FAgentMessage> USarembokAgentBus::GetPendingMessages(const FString& AgentId)
{
    TArray<FAgentMessage> Result;
    if (TArray<FAgentMessage>* Found = OutboxPerAgent.Find(AgentId))
    {
        Result = *Found;
        Found->Empty();
    }
    return Result;
}

bool USarembokAgentBus::CancelMessage(const FString& MessageId)
{
    if (FAgentMessage* Found = MessageStore.Find(MessageId))
    {
        Found->bCancelled = true;
        UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][AGENT_BUS] Message cancelled | MsgId=%s"), *MessageId);
        return true;
    }
    return false;
}
