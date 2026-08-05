using UnrealBuildTool;

public class SarembokVoice : ModuleRules
{
    public SarembokVoice(ReadOnlyTargetRules Target)
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
