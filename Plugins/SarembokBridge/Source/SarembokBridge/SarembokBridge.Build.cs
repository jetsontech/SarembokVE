using UnrealBuildTool;

public class SarembokBridge : ModuleRules
{
    public SarembokBridge(ReadOnlyTargetRules Target)
        : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(
            new string[]
            {
                "Core",
                "CoreUObject",
                "Engine",
                
                "WebSockets",
                "Projects",
                "Sockets",
                "Networking",
                "WebSockets",
                "Json",
                "JsonUtilities"
            }
        );
    }
}



