from setuptools import setup

package_name = "keyboard_teleop"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="yly",
    maintainer_email="yly@example.com",
    description="Terminal keyboard control for Scout via /cmd_vel.",
    license="MIT",
    entry_points={
        "console_scripts": ["keyboard_teleop = keyboard_teleop.teleop:main"],
    },
)
