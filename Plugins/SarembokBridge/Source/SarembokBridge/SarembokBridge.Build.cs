using UnrealBuildTool;

public class SarembokBridge : ModuleRules
{
	public SarembokBridge(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(
			new string[]
			{
				"Core",
				"CoreUObject",
				"Engine",
				"WebSockets",
				"Json",
				"JsonUtilities"
			}
		);

		PrivateDependencyModuleNames.AddRange(
			new string[]
			{
				"Projects",
				"SarembokAvatar"
			}
		);

		CppStandard = CppStandardVersion.Cpp20;
	}
}
