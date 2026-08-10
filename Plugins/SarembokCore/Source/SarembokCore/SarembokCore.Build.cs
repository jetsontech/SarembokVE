using UnrealBuildTool;

public class SarembokCore : ModuleRules
{
    public SarembokCore(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(new string[]
        {
            "Core",
            "CoreUObject",
            "Engine",
            "Json",
            "JsonUtilities",
            "SarembokAgent",
            "SarembokBridge",
            "SarembokMemory",
            "SarembokVision",
            "SarembokVoice"
        });
    }
}
