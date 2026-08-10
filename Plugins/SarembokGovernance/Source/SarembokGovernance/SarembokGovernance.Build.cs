using UnrealBuildTool;

public class SarembokGovernance : ModuleRules
{
    public SarembokGovernance(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(new string[]
        {
            "Core",
            "CoreUObject",
            "Engine",
            "Json",
            "JsonUtilities",
            "SarembokCore",
            "SarembokAgent"
        });
    }
}
