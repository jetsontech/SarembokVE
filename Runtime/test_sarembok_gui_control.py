import unittest

from sarembok_gui_control import (
    GUIControlPolicy,
    SarembokGUIController,
    UIAction,
    UIActionType,
    UIElement,
    UIObservation,
)


class FakeBackend:
    def observe(self):
        return UIObservation(
            application="ExampleApp",
            window_title="Example",
            elements=[UIElement("button-1", "button", "Continue")],
        )

    def execute(self, action):
        return {"ok": True, "action": action.action_type.value}


class GUIControlTests(unittest.TestCase):
    def test_observation_is_available_without_action_permission(self):
        controller = SarembokGUIController(FakeBackend())
        observation = controller.observe()
        self.assertEqual(observation.application, "ExampleApp")
        self.assertEqual(observation.elements[0].name, "Continue")

    def test_actions_are_denied_by_default(self):
        controller = SarembokGUIController(FakeBackend())
        with self.assertRaises(PermissionError):
            controller.execute(UIAction(UIActionType.CLICK, target_id="button-1"))

    def test_explicit_permission_reaches_backend(self):
        controller = SarembokGUIController(
            FakeBackend(), GUIControlPolicy(allow_click=True)
        )
        result = controller.execute(UIAction(UIActionType.CLICK, target_id="button-1"))
        self.assertTrue(result["ok"])


if __name__ == "__main__":
    unittest.main()
