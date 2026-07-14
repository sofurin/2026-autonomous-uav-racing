from pathlib import Path
import subprocess


PACKAGE_DIR = Path(__file__).resolve().parents[1]
AIRFRAME = (
    PACKAGE_DIR
    / "models"
    / "team_racer"
    / "config"
    / "4022_gz_team_racer"
)
INSTALLER = PACKAGE_DIR / "scripts" / "install_team_racer_px4.sh"


def _fake_px4_tree(tmp_path: Path) -> Path:
    px4_dir = tmp_path / "PX4-Autopilot"
    airframes_dir = px4_dir / "ROMFS" / "px4fmu_common" / "init.d-posix" / "airframes"
    airframes_dir.mkdir(parents=True)
    (airframes_dir / "CMakeLists.txt").write_text(
        "px4_add_romfs_files(\n"
        "\t4001_gz_x500\n"
        "\t4021_gz_x500_flow\n"
        ")\n",
        encoding="utf-8",
    )
    return px4_dir


def test_project_owns_a_complete_team_racer_airframe() -> None:
    source = AIRFRAME.read_text(encoding="utf-8")

    assert "PX4_SIM_MODEL=${PX4_SIM_MODEL:=team_racer}" in source
    assert "param set-default CA_ROTOR_COUNT 4" in source
    for motor in range(4):
        assert f"param set-default CA_ROTOR{motor}_PX" in source
        assert f"param set-default CA_ROTOR{motor}_PY" in source
        assert f"param set-default CA_ROTOR{motor}_PZ" in source
        assert f"param set-default CA_ROTOR{motor}_KM" in source
        assert f"param set-default SIM_GZ_EC_FUNC{motor + 1} {101 + motor}" in source


def test_installer_registers_the_airframe_idempotently(tmp_path: Path) -> None:
    px4_dir = _fake_px4_tree(tmp_path)

    for _ in range(2):
        result = subprocess.run(
            ["bash", str(INSTALLER), "--px4-dir", str(px4_dir)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

    installed = (
        px4_dir
        / "ROMFS"
        / "px4fmu_common"
        / "init.d-posix"
        / "airframes"
        / AIRFRAME.name
    )
    assert installed.read_text(encoding="utf-8") == AIRFRAME.read_text(encoding="utf-8")

    cmake = installed.parent / "CMakeLists.txt"
    assert cmake.read_text(encoding="utf-8").count("\t4022_gz_team_racer\n") == 1
