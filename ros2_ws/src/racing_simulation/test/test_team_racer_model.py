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


def test_unmeasured_dynamics_are_labelled_as_a_temporary_baseline():
    geometry = yaml.safe_load((MODEL_DIR / "config" / "geometry.yaml").read_text())
    dynamics = geometry["dynamics"]
    assert dynamics["status"] == "temporary_baseline"
    assert dynamics["source"] == "PX4 gz_x500"
    assert dynamics["flight_truth"] is False
