using UnrealBuildTool;

public class SarembokMemory : ModuleRules
{
    public SarembokMemory(ReadOnlyTargetRules Target)
        : base(Target)
    {
        PCHUsage =
        PCHUsageMode.UseExplicitOrSharedPCHs;


        PublicDependencyModuleNames.AddRange(
        new string[]
        {
            "Core",
            "CoreUObject",
            "Engine"
        });
    }
}
