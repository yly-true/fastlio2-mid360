import unittest

from keyboard_teleop.teleop import ANGULAR_SPEED, LINEAR_SPEED, command_for


class KeyboardCommandsTest(unittest.TestCase):
    def test_movement_and_stop(self):
        self.assertEqual(command_for("w").linear.x, LINEAR_SPEED)
        self.assertEqual(command_for("s").linear.x, -LINEAR_SPEED)
        self.assertEqual(command_for("q").linear.y, LINEAR_SPEED)
        self.assertEqual(command_for("e").linear.y, -LINEAR_SPEED)
        self.assertEqual(command_for("a").angular.z, ANGULAR_SPEED)
        self.assertEqual(command_for("d").angular.z, -ANGULAR_SPEED)
        self.assertEqual(command_for(" ").linear.x, 0.0)
        self.assertEqual(command_for(" ").angular.z, 0.0)
