# team_racer

This is the project-owned Gazebo model for the team aircraft. It separates
three kinds of data that have different maturity:

- `meshes/base_link.stl`: CAD appearance, in SolidWorks Y-up coordinates.
- `config/geometry.yaml`: CAD-derived geometry in ROS FLU coordinates.
- `model.sdf`: Gazebo links, primitive collisions, sensors and a temporary
  PX4 x500 dynamics baseline.
- `model://realsense_d435_sensor`: a merged 72 g virtual D435 sensor suite
  fixed to `base_link`, without duplicate visual or collision geometry.

The exported team CAD mesh already contains the D435 body. Its SolidWorks
component frame was transformed from `UAV_SIM_ORIGIN` to ROS FLU as
`-0.0085553439 -0.0652616422 0.0549360600 m`. Keep the SDF, `geometry.yaml`
and `racing_description/urdf/racing_uav.urdf.xacro` values synchronized when
measured optical extrinsics replace this component-origin approximation.

The sensor-only model intentionally uses a real-time development profile:
color is 640x360 at 15 Hz, depth/point cloud is 424x240 at 15 Hz, and both
infrared streams are 424x240 at 10 Hz. All streams remain available; the lower
rates avoid the severe real-time-factor collapse caused by four
1280x720-at-30-Hz render sensors.

For the flight-plus-GUI demo, only the color bridge is enabled by default.
Depth/point-cloud and infrared sensors remain in the model and can be enabled
with `start_depth_bridge:=true` and `start_infrared_bridge:=true` when needed.

The project owns the PX4 `4022_gz_team_racer` airframe definition in
`config/4022_gz_team_racer`. Install it into an external PX4 checkout with:

```bash
bash scripts/install_team_racer_px4.sh --px4-dir ~/PX4-Autopilot
```

`config/px4_airframe.params` remains a compact geometry reference. The SDF
still uses temporary gz_x500 mass, inertia and propulsion coefficients.

Do not replace primitive collision geometry with the high-resolution STL.
Update the CAD mesh and `geometry.yaml` together, then run
`pytest -q test/test_team_racer_model.py` from the `racing_simulation` package.
