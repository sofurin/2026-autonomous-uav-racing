from glob import glob
from setuptools import find_packages, setup

package_name = "racing_bringup"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ZJUT UAV Racing Team",
    maintainer_email="486rem22@users.noreply.github.com",
    description="Unified hardware and simulation launch entry points.",
    license="Apache-2.0",
)
