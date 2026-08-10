using UnrealBuildTool;

public class SarembokVision : ModuleRules
{
    public SarembokVision(ReadOnlyTargetRules Target)
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
            "SarembokAvatar"
        });
    }
}
