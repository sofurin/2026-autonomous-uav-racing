from pathlib import Path

import xacro


PACKAGE_ROOT = Path(__file__).parents[1]


def test_racing_uav_xacro_generates_expected_frame_tree():
    model = PACKAGE_ROOT / "urdf" / "racing_uav.urdf.xacro"

    document = xacro.process_file(str(model))
    generated_xml = document.toxml()

    assert 'link name="base_link"' in generated_xml
    assert 'link name="camera_link"' in generated_xml
    assert 'link name="camera_optical_frame"' in generated_xml

    camera_joint = next(
        joint
        for joint in document.getElementsByTagName("joint")
        if joint.getAttribute("name") == "base_to_camera"
    )
    camera_origin = camera_joint.getElementsByTagName("origin")[0]
    assert (
        camera_origin.getAttribute("xyz")
        == "-0.0085553439 -0.0652616422 0.0549360600"
    )
    assert camera_origin.getAttribute("rpy") == "0 0 0"


def test_team_airframe_visual_mesh_is_part_of_the_description():
    model = PACKAGE_ROOT / "urdf" / "racing_uav.urdf.xacro"

    document = xacro.process_file(str(model))
    generated_xml = document.toxml()

    mesh_uri = "package://racing_description/meshes/team_racer/base_link.stl"
    assert mesh_uri in generated_xml

    mesh = PACKAGE_ROOT / "meshes" / "team_racer" / "base_link.stl"
    assert mesh.is_file()
    assert mesh.stat().st_size > 1_000_000


def test_team_airframe_visual_maps_cad_axes_to_ros_axes():
    model = PACKAGE_ROOT / "urdf" / "racing_uav.urdf.xacro"

    document = xacro.process_file(str(model))
    visual_origin = document.getElementsByTagName("visual")[0].getElementsByTagName(
        "origin"
    )[0]

    # SolidWorks: Y is model height. ROS: X forward, Y left, Z up.
    assert visual_origin.getAttribute("rpy") == "1.57079632679 0 1.57079632679"


def test_description_package_installs_mesh_resources():
    cmake = (PACKAGE_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")

    assert "DIRECTORY launch urdf meshes config" in cmake
