using UnrealBuildTool;

public class SarembokAgent : ModuleRules
{
    public SarembokAgent(ReadOnlyTargetRules Target)
        : base(Target)
    {
        PCHUsage =
        PCHUsageMode.UseExplicitOrSharedPCHs;


        PublicDependencyModuleNames.AddRange(
        new string[]
        {
            "Core",
            "CoreUObject",
            "Engine",
            "Json",
            "JsonUtilities",
            "SarembokVision",
            "SarembokMemory",
            "SarembokBridge",
            "SarembokVoice"
        });
    }
}
