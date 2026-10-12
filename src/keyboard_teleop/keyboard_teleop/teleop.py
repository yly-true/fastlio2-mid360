"""Publish short-lived keyboard velocity commands from an interactive terminal."""

import select
import sys
import termios
import time
import tty

import rclpy
from geometry_msgs.msg import Twist


LINEAR_SPEED = 0.2  # m/s; adjust only after checking the real Scout model.
ANGULAR_SPEED = 0.5  # rad/s
COMMAND_TIMEOUT = 0.25  # Stop when keys stop arriving.


def command_for(key):
    command = Twist()
    if key == "w":
        command.linear.x = LINEAR_SPEED
    elif key == "s":
        command.linear.x = -LINEAR_SPEED
    elif key == "q":
        command.linear.y = LINEAR_SPEED
    elif key == "e":
        command.linear.y = -LINEAR_SPEED
    elif key == "a":
        command.angular.z = ANGULAR_SPEED
    elif key == "d":
        command.angular.z = -ANGULAR_SPEED
    return command


def main():
    if not sys.stdin.isatty():
        raise SystemExit("请在交互式终端运行键盘控制节点")

    rclpy.init()
    node = rclpy.create_node("keyboard_teleop")
    publisher = node.create_publisher(Twist, "/cmd_vel", 10)
    input_fd = sys.stdin.fileno()
    original = termios.tcgetattr(input_fd)
    command = Twist()
    last_key_time = 0.0

    print("W/S 前后，A/D 左右转，Q/E 横移，空格停止，X 退出；松键约 0.25 秒自动停。", flush=True)
    try:
        tty.setcbreak(input_fd)
        while rclpy.ok():
            if select.select([sys.stdin], [], [], 0.1)[0]:
                key = sys.stdin.read(1).lower()
                if key == "x":
                    break
                command = command_for(key)
                last_key_time = time.monotonic()
            if time.monotonic() - last_key_time > COMMAND_TIMEOUT:
                command = Twist()
            publisher.publish(command)
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(input_fd, termios.TCSADRAIN, original)
        publisher.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
