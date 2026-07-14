# team_racer

This is the project-owned Gazebo model for the team aircraft. It separates
three kinds of data that have different maturity:

- `meshes/base_link.stl`: CAD appearance, in SolidWorks Y-up coordinates.
- `config/geometry.yaml`: CAD-derived geometry in ROS FLU coordinates.
- `model.sdf`: Gazebo links, primitive collisions, sensors and a temporary
  PX4 x500 dynamics baseline.

The model is intentionally not registered as a PX4 `gz_team_racer` airframe
yet. `config/px4_airframe.params` is the measured geometry input for that
later integration; it is not automatically loaded by PX4.

Do not replace primitive collision geometry with the high-resolution STL.
Update the CAD mesh and `geometry.yaml` together, then run
`pytest -q test/test_team_racer_model.py` from the `racing_simulation` package.
