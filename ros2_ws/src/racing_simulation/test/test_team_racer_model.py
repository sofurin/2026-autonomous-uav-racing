from pathlib import Path
import math
import xml.etree.ElementTree as ET

import yaml


PACKAGE_DIR = Path(__file__).resolve().parents[1]
MODEL_DIR = PACKAGE_DIR / "models" / "team_racer"


def _model_root():
    sdf = ET.parse(MODEL_DIR / "model.sdf").getroot()
    model = sdf.find("model")
    assert model is not None
    return model


def _plugin_value(plugin, name):
    value = plugin.findtext(name)
    assert value is not None
    return value.strip()


def test_team_racer_has_a_self_contained_gazebo_model():
    assert (MODEL_DIR / "model.config").is_file()
    assert (MODEL_DIR / "model.sdf").is_file()
    assert (MODEL_DIR / "meshes" / "base_link.stl").is_file()
    assert (MODEL_DIR / "config" / "geometry.yaml").is_file()
    assert (MODEL_DIR / "config" / "px4_airframe.params").is_file()

    model = _model_root()
    assert model.attrib["name"] == "team_racer"
    links = {link.attrib["name"] for link in model.findall("link")}
    assert {
        "base_link",
        "flight_controller_link",
        "imu_link",
        "rotor_0",
        "rotor_1",
        "rotor_2",
        "rotor_3",
    } <= links


def test_visual_uses_team_cad_but_collisions_are_primitives():
    model = _model_root()
    uri = model.findtext("./link[@name='base_link']/visual/geometry/mesh/uri")
    assert uri == "model://team_racer/meshes/base_link.stl"

    collisions = model.findall(".//collision")
    assert collisions
    assert not model.findall(".//collision/geometry/mesh")
    assert model.findall(".//collision/geometry/box")
    assert model.findall(".//collision/geometry/cylinder")


def test_quad_x_motor_numbering_and_directions_are_explicit():
    model = _model_root()
    plugins = [
        plugin
        for plugin in model.findall("plugin")
        if plugin.attrib.get("filename")
        == "gz-sim-multicopter-motor-model-system"
    ]
    assert len(plugins) == 4
    by_number = {int(_plugin_value(plugin, "motorNumber")): plugin for plugin in plugins}
    assert set(by_number) == {0, 1, 2, 3}
    assert [_plugin_value(by_number[i], "turningDirection") for i in range(4)] == [
        "ccw",
        "ccw",
        "cw",
        "cw",
    ]
    assert [_plugin_value(by_number[i], "jointName") for i in range(4)] == [
        f"rotor_{i}_joint" for i in range(4)
    ]


def test_px4_gz_bridge_sensor_names_match_the_x500_contract():
    model = _model_root()
    base_link = model.find("./link[@name='base_link']")
    assert base_link is not None

    sensors = {
        sensor.attrib["name"]: sensor.attrib["type"]
        for sensor in base_link.findall("sensor")
    }
    assert sensors["imu_sensor"] == "imu"
    assert sensors["air_pressure_sensor"] == "air_pressure"
    assert sensors["magnetometer_sensor"] == "magnetometer"
    assert sensors["navsat_sensor"] == "navsat"

    assert not model.findall("./link[@name='imu_link']/sensor")


def test_px4_health_sensors_have_nonzero_noise_to_avoid_stale_data():
    model = _model_root()
    noise_paths = [
        "./link[@name='base_link']/sensor[@name='air_pressure_sensor']/air_pressure/pressure/noise/stddev",
        "./link[@name='base_link']/sensor[@name='magnetometer_sensor']/magnetometer/x/noise/stddev",
        "./link[@name='base_link']/sensor[@name='magnetometer_sensor']/magnetometer/y/noise/stddev",
        "./link[@name='base_link']/sensor[@name='magnetometer_sensor']/magnetometer/z/noise/stddev",
        "./link[@name='base_link']/sensor[@name='imu_sensor']/imu/angular_velocity/x/noise/stddev",
        "./link[@name='base_link']/sensor[@name='imu_sensor']/imu/angular_velocity/y/noise/stddev",
        "./link[@name='base_link']/sensor[@name='imu_sensor']/imu/angular_velocity/z/noise/stddev",
        "./link[@name='base_link']/sensor[@name='imu_sensor']/imu/linear_acceleration/x/noise/stddev",
        "./link[@name='base_link']/sensor[@name='imu_sensor']/imu/linear_acceleration/y/noise/stddev",
        "./link[@name='base_link']/sensor[@name='imu_sensor']/imu/linear_acceleration/z/noise/stddev",
    ]

    for path in noise_paths:
        value = model.findtext(path)
        assert value is not None, path
        assert float(value) > 0.0, path


def test_sensor_only_d435_is_fixed_at_the_cad_component_pose():
    model = _model_root()
    camera_include = next(
        include
        for include in model.findall("include")
        if include.findtext("uri") == "model://realsense_d435_sensor"
    )
    assert camera_include.attrib.get("merge") == "true"
    expected_pose = "-0.0085553439 -0.0652616422 0.0549360600 0 0 0"
    assert camera_include.findtext("pose") == expected_pose

    camera_joint = model.find("./joint[@name='camera_joint']")
    assert camera_joint is not None
    assert camera_joint.attrib["type"] == "fixed"
    assert camera_joint.findtext("parent") == "base_link"
    assert camera_joint.findtext("child") == "camera_link"
    assert camera_joint.findtext("pose") == expected_pose

    sensor_sdf = MODEL_DIR.parent / "realsense_d435_sensor" / "model.sdf"
    sensor_model = ET.parse(sensor_sdf).getroot().find("model")
    assert sensor_model is not None
    assert sensor_model.find("./link[@name='camera_link']/visual") is None
    assert sensor_model.find("./link[@name='camera_link']/collision") is None
    assert math.isclose(
        float(sensor_model.findtext("./link[@name='camera_link']/inertial/mass")),
        0.072,
    )
    inertia = sensor_model.find("./link[@name='camera_link']/inertial/inertia")
    assert inertia is not None
    assert {child.tag for child in inertia} == {
        "ixx",
        "iyy",
        "izz",
        "ixy",
        "ixz",
        "iyz",
    }
    diagonal = [float(inertia.findtext(axis)) for axis in ("ixx", "iyy", "izz")]
    assert all(value > 0.0 for value in diagonal)
    assert diagonal[0] + diagonal[1] >= diagonal[2]
    assert diagonal[0] + diagonal[2] >= diagonal[1]
    assert diagonal[1] + diagonal[2] >= diagonal[0]

    topics = {
        topic.text
        for topic in sensor_model.findall("./link[@name='camera_link']/sensor/topic")
    }
    assert "/camera/color/image_raw" in topics
    assert "/camera/depth/image_raw" in topics
    assert "/camera/infra1/image_raw" in topics
    assert "/camera/infra2/image_raw" in topics

    sensors = sensor_model.findall("./link[@name='camera_link']/sensor")
    assert len(sensors) == 4
    assert {sensor.findtext("gz_frame_id") for sensor in sensors} == {"camera_link"}

    by_name = {sensor.attrib["name"]: sensor for sensor in sensors}
    expected_profiles = {
        "color_rgb": (15.0, 640, 360),
        "depth_stereo": (15.0, 424, 240),
        "infra_left": (10.0, 424, 240),
        "infra_right": (10.0, 424, 240),
    }
    for name, (rate, width, height) in expected_profiles.items():
        sensor = by_name[name]
        assert float(sensor.findtext("update_rate")) == rate
        assert int(sensor.findtext("camera/image/width")) == width
        assert int(sensor.findtext("camera/image/height")) == height
        assert sensor.findtext("visualize") == "false"


def test_geometry_contract_matches_the_cad_measurements():
    geometry = yaml.safe_load((MODEL_DIR / "config" / "geometry.yaml").read_text())
    assert geometry["frame_convention"] == "ROS FLU"
    assert geometry["layout"] == "Quad-X"
    assert geometry["dimensions_m"] == {
        "length_x": 0.3040365875,
        "width_y": 0.2867687643,
        "height_z": 0.1350000054,
    }
    assert math.isclose(geometry["motor_geometry"]["diagonal_axis_distance_m"], 0.25)
    assert math.isclose(
        geometry["motor_geometry"]["adjacent_axis_distance_m"],
        0.1767766953,
    )
    assert math.isclose(geometry["propeller"]["diameter_m"], 0.1301513)
    assert math.isclose(
        geometry["propeller"]["adjacent_tip_clearance_m"],
        0.0466253953,
    )

    motors = geometry["motor_geometry"]["motors"]
    assert [motor["id"] for motor in motors] == [0, 1, 2, 3]
    assert [motor["direction"] for motor in motors] == ["ccw", "ccw", "cw", "cw"]

    camera_mount = geometry["camera_mount"]
    assert camera_mount["model"] == "realsense_d435_sensor"
    assert camera_mount["parent_frame"] == "base_link"
    assert camera_mount["xyz_flu_m"] == [
        -0.0085553439,
        -0.0652616422,
        0.05493606,
    ]
    assert camera_mount["rpy_rad"] == [0.0, 0.0, 0.0]
    assert camera_mount["status"] == "cad_component_frame"


def test_unmeasured_dynamics_are_labelled_as_a_temporary_baseline():
    geometry = yaml.safe_load((MODEL_DIR / "config" / "geometry.yaml").read_text())
    dynamics = geometry["dynamics"]
    assert dynamics["status"] == "temporary_baseline"
    assert dynamics["source"] == "PX4 gz_x500"
    assert dynamics["flight_truth"] is False
