#!/usr/bin/env python3
"""Fly the RoboCup 2025 known-map baseline route with MAVLink position setpoints.

This is a first engineering baseline, not the final contest solution.  Vision
will later replace the configured obstacle coordinates; the flight state machine
can stay mostly the same.
"""

from __future__ import annotations

import argparse
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from pymavlink import mavutil

from score_checker import load_course, samples_from_route, score_trace


@dataclass(frozen=True)
class LocalSetpoint:
    name: str
    north: float
    east: float
    down: float
    yaw_rad: float | None = None


@dataclass
class GcsHeartbeat:
    enabled: bool = True
    period_s: float = 1.0
    next_send_s: float = 0.0

    def maybe_send(self, vehicle) -> None:
        if not self.enabled:
            return

        now = time.monotonic()
        if now < self.next_send_s:
            return

        vehicle.mav.heartbeat_send(
            mavutil.mavlink.MAV_TYPE_GCS,
            mavutil.mavlink.MAV_AUTOPILOT_INVALID,
            0,
            0,
            mavutil.mavlink.MAV_STATE_ACTIVE,
        )
        self.next_send_s = now + self.period_s


SITL_PARAM_OVERRIDES = {
    # Keep no-QGroundControl SITL runs from blocking autonomous tests.
    "NAV_DLL_ACT": 0,
    # Ignore datalink / RC loss only while the vehicle is in Offboard.
    "COM_DLL_EXCEPT": 4,
    "COM_RCL_EXCEPT": 4,
}


def enu_to_local_ned(position_enu: list[float], home_enu: list[float]) -> tuple[float, float, float]:
    """Convert Gazebo ENU coordinates into PX4 local NED coordinates.

    Gazebo world: x=east, y=north, z=up.
    PX4 local NED: x=north, y=east, z=down, with origin at the spawn/home pose.
    """

    east = float(position_enu[0]) - float(home_enu[0])
    north = float(position_enu[1]) - float(home_enu[1])
    up = float(position_enu[2]) - float(home_enu[2])
    return north, east, -up


def _path_yaw_rad(points: list[tuple[float, float, float]], index: int) -> float | None:
    if len(points) < 2:
        return None

    if index < len(points) - 1:
        start = points[index]
        end = points[index + 1]
    else:
        start = points[index - 1]
        end = points[index]

    north_delta = end[0] - start[0]
    east_delta = end[1] - start[1]
    if abs(north_delta) < 1e-6 and abs(east_delta) < 1e-6:
        return None
    return math.atan2(east_delta, north_delta)


def route_to_local_setpoints(
    course: dict,
    yaw_rad: float | None = None,
    yaw_mode: str = "path",
) -> list[LocalSetpoint]:
    home = [
        course["start_zone"]["center"][0],
        course["start_zone"]["center"][1],
        0.0,
    ]
    local_positions: list[tuple[float, float, float]] = []
    for waypoint in course["route"]:
        local_positions.append(enu_to_local_ned(waypoint["position"], home))

    setpoints: list[LocalSetpoint] = []
    previous_yaw = yaw_rad
    for index, waypoint in enumerate(course["route"]):
        north, east, down = local_positions[index]
        if yaw_mode == "fixed":
            waypoint_yaw = yaw_rad
        elif yaw_mode == "path":
            waypoint_yaw = _path_yaw_rad(local_positions, index)
            if waypoint_yaw is None:
                waypoint_yaw = previous_yaw
        else:
            waypoint_yaw = None
        previous_yaw = waypoint_yaw
        setpoints.append(LocalSetpoint(waypoint["name"], north, east, down, waypoint_yaw))
    return setpoints


def distance_to_setpoint(position_msg, setpoint: LocalSetpoint) -> float:
    return math.sqrt(
        (position_msg.x - setpoint.north) ** 2
        + (position_msg.y - setpoint.east) ** 2
        + (position_msg.z - setpoint.down) ** 2
    )


def connect(connection: str):
    vehicle = mavutil.mavlink_connection(connection)
    print(f"Waiting for MAVLink heartbeat on {connection} ...")
    vehicle.wait_heartbeat(timeout=30)
    print(f"Heartbeat from system={vehicle.target_system} component={vehicle.target_component}")
    vehicle.mav.request_data_stream_send(
        vehicle.target_system,
        vehicle.target_component,
        mavutil.mavlink.MAV_DATA_STREAM_POSITION,
        20,
        1,
    )
    return vehicle


def send_position_setpoint(vehicle, setpoint: LocalSetpoint) -> None:
    type_mask = (
        mavutil.mavlink.POSITION_TARGET_TYPEMASK_VX_IGNORE
        | mavutil.mavlink.POSITION_TARGET_TYPEMASK_VY_IGNORE
        | mavutil.mavlink.POSITION_TARGET_TYPEMASK_VZ_IGNORE
        | mavutil.mavlink.POSITION_TARGET_TYPEMASK_AX_IGNORE
        | mavutil.mavlink.POSITION_TARGET_TYPEMASK_AY_IGNORE
        | mavutil.mavlink.POSITION_TARGET_TYPEMASK_AZ_IGNORE
        | mavutil.mavlink.POSITION_TARGET_TYPEMASK_YAW_RATE_IGNORE
    )
    yaw = 0.0 if setpoint.yaw_rad is None else setpoint.yaw_rad
    vehicle.mav.set_position_target_local_ned_send(
        int(time.time() * 1000) & 0xFFFFFFFF,
        vehicle.target_system,
        vehicle.target_component,
        mavutil.mavlink.MAV_FRAME_LOCAL_NED,
        type_mask,
        setpoint.north,
        setpoint.east,
        setpoint.down,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        yaw,
        0.0,
    )


def command_long(vehicle, command: int, *params: float) -> None:
    padded = list(params) + [0.0] * (7 - len(params))
    vehicle.mav.command_long_send(
        vehicle.target_system,
        vehicle.target_component,
        command,
        0,
        *padded[:7],
    )


def wait_command_ack(vehicle, command: int, timeout_s: float = 5.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        ack = vehicle.recv_match(type="COMMAND_ACK", blocking=True, timeout=max(0.1, deadline - time.monotonic()))
        if ack is None or int(ack.command) != int(command):
            continue
        result = int(ack.result)
        result_name = mavutil.mavlink.enums["MAV_RESULT"].get(result)
        label = result_name.name if result_name is not None else str(result)
        print(f"COMMAND_ACK command={command} result={label}")
        if result != mavutil.mavlink.MAV_RESULT_ACCEPTED:
            raise RuntimeError(f"MAVLink command {command} was rejected: {label}")
        return ack
    raise TimeoutError(f"Timed out waiting for COMMAND_ACK command={command}")


def _message_param_id(message) -> str:
    param_id = message.param_id
    if isinstance(param_id, bytes):
        param_id = param_id.decode("ascii", errors="ignore")
    return str(param_id).split("\x00", 1)[0]


def set_param_int(vehicle, name: str, value: int, timeout_s: float = 4.0) -> None:
    encoded_name = name.encode("ascii")
    deadline = time.monotonic() + timeout_s

    while time.monotonic() < deadline:
        vehicle.mav.param_set_send(
            vehicle.target_system,
            vehicle.target_component,
            encoded_name,
            float(value),
            mavutil.mavlink.MAV_PARAM_TYPE_INT32,
        )

        wait_deadline = min(deadline, time.monotonic() + 0.5)
        while time.monotonic() < wait_deadline:
            msg = vehicle.recv_match(
                type="PARAM_VALUE",
                blocking=True,
                timeout=max(0.05, wait_deadline - time.monotonic()),
            )
            if msg is None or _message_param_id(msg) != name:
                continue

            actual = int(round(float(msg.param_value)))
            print(f"PARAM {name}={actual}")
            if actual == int(value):
                return

    raise TimeoutError(f"Timed out setting PX4 parameter {name}={value}")


def configure_sitl_params(vehicle) -> None:
    print("Configuring SITL Offboard parameters...")
    for name, value in SITL_PARAM_OVERRIDES.items():
        set_param_int(vehicle, name, value)


def set_offboard_mode(vehicle) -> None:
    vehicle.set_mode("OFFBOARD")
    wait_command_ack(vehicle, mavutil.mavlink.MAV_CMD_DO_SET_MODE)


def arm(vehicle) -> None:
    command_long(vehicle, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 1.0)
    wait_command_ack(vehicle, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM)


def land(vehicle) -> None:
    command_long(vehicle, mavutil.mavlink.MAV_CMD_NAV_LAND)


def latest_position(vehicle, timeout_s: float = 1.0):
    return vehicle.recv_match(type="LOCAL_POSITION_NED", blocking=True, timeout=timeout_s)


def wait_local_position(vehicle, heartbeat: GcsHeartbeat, timeout_s: float = 30.0):
    print("Waiting for local position estimate...")
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        heartbeat.maybe_send(vehicle)
        position = latest_position(vehicle, timeout_s=0.5)
        if position is not None and all(
            math.isfinite(float(value)) for value in (position.x, position.y, position.z)
        ):
            print(f"Local position ready: N={position.x:.2f} E={position.y:.2f} D={position.z:.2f}")
            return position
    raise TimeoutError("Timed out waiting for LOCAL_POSITION_NED")


def hold_setpoint(
    vehicle,
    setpoint: LocalSetpoint,
    duration_s: float,
    rate_hz: float,
    heartbeat: GcsHeartbeat | None = None,
) -> None:
    deadline = time.monotonic() + duration_s
    period = 1.0 / rate_hz
    while time.monotonic() < deadline:
        if heartbeat is not None:
            heartbeat.maybe_send(vehicle)
        send_position_setpoint(vehicle, setpoint)
        time.sleep(period)


def fly_to_setpoint(
    vehicle,
    setpoint: LocalSetpoint,
    acceptance_radius_m: float,
    timeout_s: float,
    rate_hz: float,
    heartbeat: GcsHeartbeat | None = None,
) -> None:
    print(
        f"Target {setpoint.name}: N={setpoint.north:.2f} E={setpoint.east:.2f} D={setpoint.down:.2f}"
    )
    deadline = time.monotonic() + timeout_s
    period = 1.0 / rate_hz
    last_distance = None
    while time.monotonic() < deadline:
        if heartbeat is not None:
            heartbeat.maybe_send(vehicle)
        send_position_setpoint(vehicle, setpoint)
        position = latest_position(vehicle, timeout_s=period)
        if position is not None:
            last_distance = distance_to_setpoint(position, setpoint)
            if last_distance <= acceptance_radius_m:
                print(f"Reached {setpoint.name}: distance={last_distance:.2f} m")
                hold_setpoint(vehicle, setpoint, duration_s=0.7, rate_hz=rate_hz, heartbeat=heartbeat)
                return
        time.sleep(period)

    raise TimeoutError(f"Timed out reaching {setpoint.name}; last distance={last_distance}")


def fly_known_course(
    course: dict,
    connection: str,
    dry_run: bool = False,
    yaw_mode: str = "path",
    yaw_deg: float = 0.0,
    configure_sitl: bool = True,
    gcs_heartbeat: bool = True,
) -> None:
    yaw_rad = math.radians(yaw_deg)
    setpoints = route_to_local_setpoints(course, yaw_rad=yaw_rad, yaw_mode=yaw_mode)
    route_score = score_trace(samples_from_route(course), course)

    if dry_run:
        print("Dry-run local NED setpoints:")
        for setpoint in setpoints:
            print(
                f"{setpoint.name:22s} N={setpoint.north:6.2f} E={setpoint.east:6.2f} "
                f"D={setpoint.down:6.2f} yaw={math.degrees(setpoint.yaw_rad or 0.0):7.1f}"
            )
        print(f"Configured route score: {route_score['total_score']} ({route_score})")
        return

    vehicle = connect(connection)
    heartbeat = GcsHeartbeat(enabled=gcs_heartbeat)
    heartbeat.maybe_send(vehicle)
    if configure_sitl:
        configure_sitl_params(vehicle)
    first = setpoints[0]

    wait_local_position(vehicle, heartbeat)
    print("Priming OFFBOARD setpoints...")
    hold_setpoint(vehicle, first, duration_s=2.0, rate_hz=20.0, heartbeat=heartbeat)
    print("Switching to OFFBOARD and arming...")
    set_offboard_mode(vehicle)
    arm(vehicle)
    time.sleep(1.0)

    for setpoint in setpoints:
        fly_to_setpoint(
            vehicle,
            setpoint,
            acceptance_radius_m=0.35,
            timeout_s=25.0,
            rate_hz=20.0,
            heartbeat=heartbeat,
        )

    print("Landing...")
    land(vehicle)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--course", type=Path, default=Path(__file__).with_name("course.yaml"))
    parser.add_argument("--connection", default="udpin:127.0.0.1:14540")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yaw-mode", choices=["path", "fixed", "none"], default="path")
    parser.add_argument("--yaw-deg", type=float, default=0.0)
    parser.add_argument(
        "--no-configure-sitl",
        action="store_true",
        help="Do not set the SITL Offboard failsafe parameters before flying.",
    )
    parser.add_argument(
        "--no-gcs-heartbeat",
        action="store_true",
        help="Do not send a MAVLink GCS heartbeat from this script.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    course = load_course(args.course)
    fly_known_course(
        course,
        connection=args.connection,
        dry_run=args.dry_run,
        yaw_mode=args.yaw_mode,
        yaw_deg=args.yaw_deg,
        configure_sitl=not args.no_configure_sitl,
        gcs_heartbeat=not args.no_gcs_heartbeat,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
