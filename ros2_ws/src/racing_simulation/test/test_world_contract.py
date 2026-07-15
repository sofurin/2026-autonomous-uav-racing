from pathlib import Path
import xml.etree.ElementTree as ET

import yaml


PACKAGE_DIR = Path(__file__).resolve().parents[1]
WORLD = PACKAGE_DIR / "worlds" / "racing_empty.sdf"
COMPETITION_WORLD = PACKAGE_DIR / "worlds" / "robocup_2025_baseline.sdf"


def test_empty_world_supports_px4_state_estimation_and_ground_contact():
    world = ET.parse(WORLD).getroot().find("world")
    assert world is not None

    assert world.find("gravity") is not None
    assert world.find("magnetic_field") is not None
    assert world.find("atmosphere") is not None

    spherical = world.find("spherical_coordinates")
    assert spherical is not None
    assert spherical.findtext("surface_model") == "EARTH_WGS84"
    assert spherical.findtext("world_frame_orientation") == "ENU"

    ground = world.find("./model[@name='ground_plane']")
    assert ground is not None
    assert ground.findtext("static") == "true"
    assert ground.find("./link/collision/geometry/plane") is not None


def test_competition_start_and_landing_zones_are_physical_pads() -> None:
    world = ET.parse(COMPETITION_WORLD).getroot().find("world")
    assert world is not None

    for model_name in ("start_zone", "landing_zone"):
        model = world.find(f"./model[@name='{model_name}']")
        assert model is not None
        collision_size = model.findtext("./link/collision/geometry/box/size")
        assert collision_size == "1.2 1.6 0.02"


def test_spawn_heights_clear_the_cad_bottom_and_competition_pad() -> None:
    geometry_path = (
        PACKAGE_DIR / "models" / "team_racer" / "config" / "geometry.yaml"
    )
    geometry = yaml.safe_load(geometry_path.read_text(encoding="utf-8"))
    spawn = geometry["spawn"]
    body_bottom = geometry["mesh_bounds_flu_m"]["min"][2]

    assert spawn["default_pose_z_m"] + body_bottom > 0.0
    assert (
        spawn["competition_pose_z_m"] + body_bottom
        > spawn["competition_pad_top_z_m"]
    )
