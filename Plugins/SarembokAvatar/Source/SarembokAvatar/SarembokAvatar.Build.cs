using UnrealBuildTool;

public class SarembokAvatar : ModuleRules
{
    public SarembokAvatar(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(
            new string[]
            {
                "Core",
                "CoreUObject",
                "Engine",
                "SarembokBridge",
                "Json",
                "JsonUtilities",
                "TextToSpeech"
            }
        );
    }
}
