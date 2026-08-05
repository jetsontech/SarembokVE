#include "SarembokWebSocket.h"
#include "WebSocketsModule.h"


void FSarembokWebSocket::Connect()
{

    FModuleManager::LoadModuleChecked<FWebSocketsModule>("WebSockets");


    Socket =
        FWebSocketsModule::Get()
        .CreateWebSocket(
            TEXT("ws://127.0.0.1:9000")
        );


    Socket->OnConnected().AddLambda([]()
    {
        UE_LOG(
            LogTemp,
            Warning,
            TEXT("Sarembok WebSocket Connected")
        );
    });


    Socket->OnConnectionError().AddLambda([](const FString& Error)
    {
        UE_LOG(
            LogTemp,
            Error,
            TEXT("Sarembok WebSocket Error: %s"),
            *Error
        );
    });


    Socket->Connect();

}



void FSarembokWebSocket::Send(
    FString Event,
    FString Data
)
{

    if(Socket.IsValid() && Socket->IsConnected())
    {

        FString Message =
        FString::Printf(
            TEXT("{\"event\":\"%s\",\"data\":\"%s\"}"),
            *Event,
            *Data
        );


        Socket->Send(Message);

    }

}