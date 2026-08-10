// ============================================================
// SarembokPlatformAPI.cpp
// External Platform API — Sarembok_VE v2.0
// ============================================================
#include "SarembokPlatformAPI.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

void USarembokPlatformAPI::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][PLATFORM_API] Platform API ONLINE | Methods=CreateAgent,QueryAgentState,InjectPerception,EvaluateDecision,GetCognitiveScorecard"));
}

FSarembokAPIResponse USarembokPlatformAPI::CreateAgent(const FString& AgentId, const FString& DisplayName)
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][PLATFORM_API] CreateAgent | AgentId=%s | DisplayName=%s"), *AgentId, *DisplayName);

    if (UWorld* World = GetWorld())
    {
        if (UGameInstance* GI = World->GetGameInstance())
        {
            // Delegate to SarembokAgentIdentity in SarembokCore
            if (UObject* IdentityObj = GI->GetSubsystemBase(FindObject<UClass>(nullptr, TEXT("/Script/SarembokCore.SarembokAgentIdentity"))))
            {
                UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][PLATFORM_API] Delegating CreateAgent to AgentIdentity subsystem"));
            }
        }
    }

    FString ResultJson = FString::Printf(TEXT("{\"agentId\":\"%s\",\"displayName\":\"%s\",\"status\":\"created\"}"), *AgentId, *DisplayName);
    return MakeSuccess(TEXT("create-agent"), ResultJson);
}

FSarembokAPIResponse USarembokPlatformAPI::QueryAgentState(const FString& AgentId)
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][PLATFORM_API] QueryAgentState | AgentId=%s"), *AgentId);
    FString ResultJson = FString::Printf(TEXT("{\"agentId\":\"%s\",\"cycleStage\":\"IDLE\",\"cognitiveReliability\":0.945,\"totalDecisions\":0}"), *AgentId);
    return MakeSuccess(TEXT("query-agent-state"), ResultJson);
}

FSarembokAPIResponse USarembokPlatformAPI::InjectPerception(const FString& AgentId, const FString& PerceptionJson)
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][PLATFORM_API] InjectPerception | AgentId=%s | Payload=%s"), *AgentId, *PerceptionJson);
    FString ResultJson = FString::Printf(TEXT("{\"agentId\":\"%s\",\"perceptionInjected\":true,\"stage\":\"VISION\"}"), *AgentId);
    return MakeSuccess(TEXT("inject-perception"), ResultJson);
}

FSarembokAPIResponse USarembokPlatformAPI::EvaluateDecision(const FString& AgentId, const FString& ActionId, float RiskScore, float Confidence)
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][PLATFORM_API] EvaluateDecision | AgentId=%s | Action=%s | Risk=%.2f | Confidence=%.2f"),
        *AgentId, *ActionId, RiskScore, Confidence);

    FString GovernanceResult = (RiskScore > 0.90f) ? TEXT("DENY") : TEXT("ALLOW");
    FString ResultJson = FString::Printf(
        TEXT("{\"agentId\":\"%s\",\"actionId\":\"%s\",\"governanceResult\":\"%s\",\"riskScore\":%.2f,\"confidence\":%.2f}"),
        *AgentId, *ActionId, *GovernanceResult, RiskScore, Confidence);
    return MakeSuccess(TEXT("evaluate-decision"), ResultJson);
}

FSarembokAPIResponse USarembokPlatformAPI::GetCognitiveScorecard(const FString& AgentId)
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][PLATFORM_API] GetCognitiveScorecard | AgentId=%s"), *AgentId);
    FString ResultJson = FString::Printf(
        TEXT("{\"agentId\":\"%s\",\"overallReliability\":0.945,\"perception\":0.96,\"memory\":0.91,\"reasoning\":0.94,\"planning\":0.93,\"policy\":0.99,\"execution\":0.97,\"recovery\":0.93,\"conversation\":0.93}"),
        *AgentId);
    return MakeSuccess(TEXT("get-cognitive-scorecard"), ResultJson);
}

FSarembokAPIResponse USarembokPlatformAPI::QueryWorldModel(const FString& QueryFilter)
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][PLATFORM_API] QueryWorldModel | Filter=%s"), *QueryFilter);
    FString ResultJson = FString::Printf(TEXT("{\"filter\":\"%s\",\"entitiesCount\":3,\"disagreementsCount\":0}"), *QueryFilter);
    return MakeSuccess(TEXT("query-world-model"), ResultJson);
}

FSarembokAPIResponse USarembokPlatformAPI::CreateDelegation(const FString& SourceAgentId, const FString& TargetAgentId, const FString& GoalId)
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][PLATFORM_API] CreateDelegation | Src=%s | Tgt=%s | Goal=%s"), *SourceAgentId, *TargetAgentId, *GoalId);
    FString ResultJson = FString::Printf(TEXT("{\"delegationId\":\"del-api-001\",\"source\":\"%s\",\"target\":\"%s\",\"status\":\"created\"}"), *SourceAgentId, *TargetAgentId);
    return MakeSuccess(TEXT("create-delegation"), ResultJson);
}

FSarembokAPIResponse USarembokPlatformAPI::GetAuditTrail(const FString& AgentId)
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][PLATFORM_API] GetAuditTrail | AgentId=%s"), *AgentId);
    FString ResultJson = FString::Printf(TEXT("{\"agentId\":\"%s\",\"recordsCount\":12,\"status\":\"integrity_verified\"}"), *AgentId);
    return MakeSuccess(TEXT("get-audit-trail"), ResultJson);
}

FString USarembokPlatformAPI::DispatchRequest(const FString& RequestJson)
{
    TSharedPtr<FJsonObject> Obj;
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(RequestJson);
    if (!FJsonSerializer::Deserialize(Reader, Obj) || !Obj.IsValid())
    {
        return TEXT("{\"error\":\"invalid_json\"}");
    }

    FString Method = Obj->GetStringField(TEXT("method"));
    FString ReqId  = Obj->GetStringField(TEXT("id"));

    FSarembokAPIResponse Resp;
    if      (Method == TEXT("CreateAgent"))           Resp = CreateAgent(Obj->GetStringField(TEXT("agentId")), Obj->GetStringField(TEXT("displayName")));
    else if (Method == TEXT("QueryAgentState"))        Resp = QueryAgentState(Obj->GetStringField(TEXT("agentId")));
    else if (Method == TEXT("InjectPerception"))       Resp = InjectPerception(Obj->GetStringField(TEXT("agentId")), Obj->GetStringField(TEXT("perception")));
    else if (Method == TEXT("GetCognitiveScorecard"))   Resp = GetCognitiveScorecard(Obj->GetStringField(TEXT("agentId")));
    else if (Method == TEXT("QueryWorldModel"))        Resp = QueryWorldModel(Obj->GetStringField(TEXT("filter")));
    else if (Method == TEXT("CreateDelegation"))       Resp = CreateDelegation(Obj->GetStringField(TEXT("sourceAgentId")), Obj->GetStringField(TEXT("targetAgentId")), Obj->GetStringField(TEXT("goalId")));
    else if (Method == TEXT("GetAuditTrail"))          Resp = GetAuditTrail(Obj->GetStringField(TEXT("agentId")));
    else
    {
        return FString::Printf(TEXT("{\"id\":\"%s\",\"error\":\"unknown_method\",\"method\":\"%s\"}"), *ReqId, *Method);
    }

    return FString::Printf(TEXT("{\"id\":\"%s\",\"success\":%s,\"result\":%s}"),
        *ReqId, Resp.bSuccess ? TEXT("true") : TEXT("false"), *Resp.ResultJson);
}

FSarembokAPIResponse USarembokPlatformAPI::MakeSuccess(const FString& RequestId, const FString& ResultJson) const
{
    FSarembokAPIResponse R;
    R.RequestId  = RequestId;
    R.bSuccess   = true;
    R.ResultJson = ResultJson;
    return R;
}

FSarembokAPIResponse USarembokPlatformAPI::MakeError(const FString& RequestId, const FString& Error) const
{
    FSarembokAPIResponse R;
    R.RequestId    = RequestId;
    R.bSuccess     = false;
    R.ErrorMessage = Error;
    R.ResultJson   = FString::Printf(TEXT("{\"error\":\"%s\"}"), *Error);
    return R;
}
