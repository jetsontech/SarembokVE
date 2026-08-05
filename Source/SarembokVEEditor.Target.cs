using UnrealBuildTool;
using System.Collections.Generic;

public class SarembokVEEditorTarget : TargetRules
{
	public SarembokVEEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("SarembokVE");
	}
}
