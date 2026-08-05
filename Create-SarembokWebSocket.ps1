# ==========================================
# Sarembok VE - WebSocket Bridge Generator
# Unreal Engine 5.8
# ==========================================

$Root = "C:\Sarembok_VE\Plugins\SarembokBridge\Source\SarembokBridge"

$Public = Join-Path $Root "Public"
$Private = Join-Path $Root "Private"


# Update Build.cs

$BuildFile = Join-Path $Root "SarembokBridge.Build.cs"

@'
using UnrealBuildTool;

public class SarembokBridge : ModuleRules
{
	public SarembokBridge(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(
			new string[]
			{
				"Core",
				"CoreUObject",
				"Engine",
				"WebSockets",
				"Json",
				"JsonUtilities"
			}
		);

		PrivateDependencyModuleNames.AddRange(
			new string[]
			{
				"Projects"
			}
		);

		CppStandard = CppStandardVersion.Cpp20;
	}
}
'@ | Out-File $BuildFile -Encoding utf8


# Header

@'
#pragma once

#include "CoreMinimal.h"
#include "IWebSocket.h"

class FSarembokWebSocketClient
{
public:

	FSarembokWebSocketClient();

	~FSarembokWebSocketClient();

	void Connect();

	void Disconnect();

	void SendMessage(const FString& Message);


private:

	void OnConnected();

	void OnMessage(const FString& Message);

	void OnConnectionError(const FString& Error);

	void OnClosed(
		int32 StatusCode,
		const FString& Reason,
		bool bWasClean
	);


	TSharedPtr<IWebSocket> Socket;

	FString ServerURL;
};
'@ | Out-File `
"$Public\SarembokWebSocketClient.h" `
-Encoding utf8


# CPP

@'
#include "SarembokWebSocketClient.h"

#include "WebSocketsModule.h"


FSarembokWebSocketClient::FSarembokWebSocketClient()
{
	ServerURL = TEXT("ws://127.0.0.1:8765");
}


FSarembokWebSocketClient::~FSarembokWebSocketClient()
{
	Disconnect();
}


void FSarembokWebSocketClient::Connect()
{
	FWebSocketsModule& Module =
		FModuleManager::LoadModuleChecked<FWebSocketsModule>("WebSockets");


	Socket = Module.CreateWebSocket(ServerURL);


	Socket->OnConnected().AddRaw(
		this,
		&FSarembokWebSocketClient::OnConnected
	);


	Socket->OnMessage().AddRaw(
		this,
		&FSarembokWebSocketClient::OnMessage
	);


	Socket->OnConnectionError().AddRaw(
		this,
		&FSarembokWebSocketClient::OnConnectionError
	);


	Socket->OnClosed().AddRaw(
		this,
		&FSarembokWebSocketClient::OnClosed
	);


	Socket->Connect();
}


void FSarembokWebSocketClient::Disconnect()
{
	if(Socket.IsValid())
	{
		Socket->Close();
		Socket.Reset();
	}
}


void FSarembokWebSocketClient::SendMessage(
	const FString& Message
)
{
	if(Socket.IsValid() && Socket->IsConnected())
	{
		Socket->Send(Message);
	}
}


void FSarembokWebSocketClient::OnConnected()
{
	UE_LOG(
		LogTemp,
		Display,
		TEXT("Connected to Sarembok Core")
	);
}


void FSarembokWebSocketClient::OnMessage(
	const FString& Message
)
{
	UE_LOG(
		LogTemp,
		Display,
		TEXT("Sarembok Message: %s"),
		*Message
	);
}


void FSarembokWebSocketClient::OnConnectionError(
	const FString& Error
)
{
	UE_LOG(
		LogTemp,
		Error,
		TEXT("Sarembok Connection Error: %s"),
		*Error
	);
}


void FSarembokWebSocketClient::OnClosed(
	int32 StatusCode,
	const FString& Reason,
	bool bWasClean
)
{
	UE_LOG(
		LogTemp,
		Display,
		TEXT("Sarembok Connection Closed")
	);
}
'@ | Out-File `
"$Private\SarembokWebSocketClient.cpp" `
-Encoding utf8


Write-Host ""
Write-Host "================================="
Write-Host " Sarembok WebSocket Layer Added"
Write-Host "================================="