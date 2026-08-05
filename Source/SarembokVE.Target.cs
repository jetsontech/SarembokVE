using UnrealBuildTool;
using System.Collections.Generic;

public class SarembokVETarget : TargetRules
{
	public SarembokVETarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("SarembokVE");
	}
}
