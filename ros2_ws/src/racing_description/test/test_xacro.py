from pathlib import Path

import xacro


def test_racing_uav_xacro_generates_expected_frame_tree():
    model = Path(__file__).parents[1] / "urdf" / "racing_uav.urdf.xacro"

    document = xacro.process_file(str(model))
    generated_xml = document.toxml()

    assert 'link name="base_link"' in generated_xml
    assert 'link name="camera_link"' in generated_xml
    assert 'link name="camera_optical_frame"' in generated_xml
