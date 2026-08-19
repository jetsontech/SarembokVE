"""Create the canonical Sarembok startup world in the UE Editor.

Run inside Unreal Editor Python, or with UnrealEditor-Cmd.exe using
-ExecutePythonScript. The script intentionally creates only a blank,
Sarembok-owned level. Avatar/MetaHuman assets are resolved separately so
missing MetaHuman content cannot prevent the project from opening.

UE 5.8 uses LevelEditorSubsystem.new_level() to create and save a level.
"""

import unreal

STARTUP_MAP = "/Game/Sarembok/Maps/SarembokStartup"


def main():
    subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not subsystem.new_level(STARTUP_MAP, False):
        raise RuntimeError("Unable to create Sarembok startup level: %s" % STARTUP_MAP)

    if not subsystem.save_current_level():
        raise RuntimeError("Unable to save Sarembok startup level: %s" % STARTUP_MAP)

    unreal.log("Sarembok startup world created: %s" % STARTUP_MAP)
    unreal.log("Next stage: add the Sarembok avatar spawn contract and resolve a MetaHuman asset when available.")


if __name__ == "__main__":
    main()
