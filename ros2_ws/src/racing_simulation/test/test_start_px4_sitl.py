from pathlib import Path
import subprocess


SCRIPT = Path(__file__).parents[1] / "scripts" / "start_px4_sitl.sh"


def run_script(tmp_path: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    px4_dir = tmp_path / "PX4-Autopilot"
    models_dir = tmp_path / "models"
    worlds_dir = tmp_path / "worlds"
    px4_dir.mkdir()
    (px4_dir / "Tools/simulation/gz/models").mkdir(parents=True)
    models_dir.mkdir(exist_ok=True)
    worlds_dir.mkdir(exist_ok=True)

    return subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--dry-run",
            "--px4-dir",
            str(px4_dir),
            "--models-dir",
            str(models_dir),
            "--worlds-dir",
            str(worlds_dir),
            *arguments,
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def test_defaults_to_the_current_x500_depth_baseline(tmp_path: Path) -> None:
    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    assert "PX4_SIM_MODEL=gz_x500_depth" in result.stdout
    assert "PX4_GZ_WORLD=default" in result.stdout
    assert "make px4_sitl gz_x500_depth" in result.stdout


def test_accepts_a_future_team_model_without_changing_the_script(tmp_path: Path) -> None:
    result = run_script(
        tmp_path,
        "--model",
        "gz_team_racer",
        "--world",
        "team_course",
        "--pose=-4,-3.65,0,0,0,0",
    )

    assert result.returncode == 0, result.stderr
    assert "PX4_SIM_MODEL=gz_team_racer" in result.stdout
    assert "PX4_GZ_WORLD=team_course" in result.stdout
    assert "PX4_GZ_MODEL_POSE=-4,-3.65,0,0,0,0" in result.stdout
    assert "make px4_sitl gz_team_racer" in result.stdout


def test_starts_a_project_owned_world_before_px4_standalone(tmp_path: Path) -> None:
    worlds_dir = tmp_path / "worlds"
    worlds_dir.mkdir()
    (worlds_dir / "team_course.sdf").write_text("<sdf version='1.9'/>")

    result = run_script(tmp_path, "--world", "team_course")

    assert result.returncode == 0, result.stderr
    assert f"PROJECT_GZ_WORLD={worlds_dir / 'team_course.sdf'}" in result.stdout
    assert str(tmp_path / "PX4-Autopilot" / "Tools/simulation/gz/models") in result.stdout
    assert f"gz sim -r {worlds_dir / 'team_course.sdf'}" in result.stdout
    assert "PX4_GZ_STANDALONE=1" in result.stdout


def test_rejects_a_model_name_that_could_be_interpreted_as_shell_code(
    tmp_path: Path,
) -> None:
    result = run_script(tmp_path, "--model", "gz_x500_depth;rm")

    assert result.returncode == 2
    assert "Invalid PX4 model target" in result.stderr
