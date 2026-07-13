# Team racer visual mesh

`base_link.stl` was exported from the team SolidWorks assembly with the
SW2URDF exporter and the assembly coordinate system `UAV_SIM_ORIGIN`.

- Source package: `outputs/uav_description_centered`
- Exported rigid body: `base_link`
- Mesh triangles: 222,362
- Reported bounds: 0.286769 x 0.135000 x 0.304037 m
- Reported mesh center: (0.013797, -0.000064, -0.007073) m

The SolidWorks export uses Y as the model height axis. The visual origin in
`racing_uav.urdf.xacro` rotates the mesh so ROS uses X forward, Y left and Z up;
the STL itself remains unchanged.

The mesh is used for ROS visualization only. Do not reuse it as detailed
collision geometry. The CAD mass, center of mass and inertia are provisional
and are intentionally not copied into `racing_uav.urdf.xacro`; PX4 owns the
current simulation dynamics until measured aircraft parameters are available.
