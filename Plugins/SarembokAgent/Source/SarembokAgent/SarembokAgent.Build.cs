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
            "SarembokVision",
            "SarembokMemory",
            "SarembokBridge"
        });
    }
}
