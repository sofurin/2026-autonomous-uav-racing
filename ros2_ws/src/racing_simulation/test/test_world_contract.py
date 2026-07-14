from pathlib import Path
import xml.etree.ElementTree as ET


PACKAGE_DIR = Path(__file__).resolve().parents[1]
WORLD = PACKAGE_DIR / "worlds" / "racing_empty.sdf"


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
