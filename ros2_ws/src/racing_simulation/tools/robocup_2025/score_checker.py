#!/usr/bin/env python3
"""Known-map scoring helpers for the RoboCup 2025 UAV racing baseline.

This is intentionally independent from Gazebo and MAVLink.  Vision, simulation
logs, or hand-written traces can all feed the same checker.
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml


@dataclass(frozen=True)
class Sample:
    t: float
    x: float
    y: float
    z: float


def load_course(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def load_trace_csv(path: Path) -> list[Sample]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        rows = csv.DictReader(stream)
        return [
            Sample(
                t=float(row["t"]),
                x=float(row["x"]),
                y=float(row["y"]),
                z=float(row["z"]),
            )
            for row in rows
        ]


def _gate_coordinates(sample: Sample, gate: dict[str, Any]) -> tuple[float, float, float]:
    cx, cy, cz = gate["center"]
    yaw = math.radians(float(gate.get("yaw_deg", 0.0)))
    dx = sample.x - cx
    dy = sample.y - cy
    forward_x = math.cos(yaw)
    forward_y = math.sin(yaw)
    right_x = -math.sin(yaw)
    right_y = math.cos(yaw)
    signed_forward = dx * forward_x + dy * forward_y
    horizontal = dx * right_x + dy * right_y
    vertical = sample.z - cz
    return signed_forward, horizontal, vertical


def _first_gate_crossing_index(samples: list[Sample], gate: dict[str, Any], tolerance_m: float) -> int | None:
    if len(samples) < 2:
        return None

    half_width = float(gate["width"]) / 2.0 + tolerance_m
    half_height = float(gate["height"]) / 2.0 + tolerance_m

    previous = samples[0]
    previous_s, _, _ = _gate_coordinates(previous, gate)

    for index, current in enumerate(samples[1:], start=1):
        current_s, _, _ = _gate_coordinates(current, gate)
        crossed = previous_s == 0.0 or current_s == 0.0 or previous_s * current_s < 0.0
        if crossed:
            denom = abs(previous_s) + abs(current_s)
            ratio = 0.0 if denom == 0.0 else abs(previous_s) / denom
            interp = Sample(
                t=previous.t + (current.t - previous.t) * ratio,
                x=previous.x + (current.x - previous.x) * ratio,
                y=previous.y + (current.y - previous.y) * ratio,
                z=previous.z + (current.z - previous.z) * ratio,
            )
            _, horizontal, vertical = _gate_coordinates(interp, gate)
            if abs(horizontal) <= half_width and abs(vertical) <= half_height:
                return index
        previous = current
        previous_s = current_s

    return None


def crossed_gate(samples: list[Sample], gate: dict[str, Any], tolerance_m: float = 0.15) -> bool:
    return _first_gate_crossing_index(samples, gate, tolerance_m) is not None


def completed_gate_sequence(samples: list[Sample], gates: list[dict[str, Any]], tolerance_m: float = 0.15) -> bool:
    search_start = 0
    for gate in gates:
        crossing_index = _first_gate_crossing_index(samples[search_start:], gate, tolerance_m)
        if crossing_index is None:
            return False
        search_start += max(1, crossing_index)
        if search_start >= len(samples):
            return False
    return True


def completed_orbit(samples: list[Sample], flag: dict[str, Any], tolerance_rad: float = 0.35) -> bool:
    if len(samples) < 3:
        return False

    cx, cy, _ = flag["center"]
    min_z = float(flag["min_z"])
    max_z = float(flag["max_z"])
    radius = float(flag.get("radius", 0.0))
    radius_tolerance = float(flag.get("radius_tolerance_m", max(0.5, radius * 0.6)))
    usable = []
    for sample in samples:
        distance = math.hypot(sample.x - cx, sample.y - cy)
        near_orbit_radius = radius <= 0.0 or abs(distance - radius) <= radius_tolerance
        if min_z <= sample.z <= max_z and near_orbit_radius:
            usable.append(sample)
    if len(usable) < 3:
        return False

    angles = [math.atan2(sample.y - cy, sample.x - cx) for sample in usable]
    cumulative = 0.0
    min_cumulative = 0.0
    max_cumulative = 0.0
    previous = angles[0]
    for angle in angles[1:]:
        delta = angle - previous
        while delta > math.pi:
            delta -= 2.0 * math.pi
        while delta < -math.pi:
            delta += 2.0 * math.pi
        cumulative += delta
        min_cumulative = min(min_cumulative, cumulative)
        max_cumulative = max(max_cumulative, cumulative)
        previous = angle

    return (max_cumulative - min_cumulative) >= (2.0 * math.pi - tolerance_rad)


def in_landing_zone(sample: Sample, course: dict[str, Any]) -> bool:
    cx, cy = course["landing_zone"]["center"]
    sx, sy = course["landing_zone"]["size"]
    return abs(sample.x - cx) <= sx / 2.0 and abs(sample.y - cy) <= sy / 2.0 and sample.z <= 0.35


def time_score(duration_s: float, obstacle_count: int, landed: bool) -> int:
    if obstacle_count < 3 or not landed:
        return 0
    if duration_s <= 60.0:
        return 960
    if duration_s <= 300.0:
        return max(0, int(round(-4.0 * duration_s + 1200.0)))
    return 0


def score_trace(samples: list[Sample], course: dict[str, Any]) -> dict[str, Any]:
    if not samples:
        raise ValueError("trace has no samples")

    tolerance = float(course["flight"].get("gate_tolerance_m", 0.15))
    orbit_tolerance = float(course["flight"].get("orbit_tolerance_rad", 0.35))

    results: dict[str, Any] = {
        "takeoff": samples[0].z > 0.5,
        "landing": in_landing_zone(samples[-1], course),
        "obstacles": {},
    }

    obstacle_score = course["scoring"]["takeoff"] if results["takeoff"] else 0
    completed_obstacles = 0

    for obstacle in course["scoring"]["obstacles"]:
        kind = obstacle["type"]
        if kind == "gate":
            ok = crossed_gate(samples, course["gates"][obstacle["gate"]], tolerance)
        elif kind == "sequence":
            gates = [course["gates"][gate_name] for gate_name in obstacle["gates"]]
            ok = completed_gate_sequence(samples, gates, tolerance)
        elif kind == "orbit":
            ok = completed_orbit(samples, course["flags"][obstacle["flag"]], orbit_tolerance)
        else:
            raise ValueError(f"unknown obstacle type: {kind}")

        results["obstacles"][obstacle["name"]] = ok
        if ok:
            completed_obstacles += int(obstacle.get("count", 1))
            obstacle_score += int(obstacle["score"])

    if results["landing"]:
        obstacle_score += int(course["scoring"]["landing"])

    duration = samples[-1].t - samples[0].t
    results["obstacle_score"] = obstacle_score
    results["time_score"] = time_score(duration, completed_obstacles, results["landing"])
    results["total_score"] = results["obstacle_score"] + results["time_score"]
    results["duration_s"] = duration
    results["completed_obstacles"] = completed_obstacles
    return results


def samples_from_route(course: dict[str, Any], step_s: float = 5.0) -> list[Sample]:
    samples: list[Sample] = []
    for index, waypoint in enumerate(course["route"]):
        x, y, z = waypoint["position"]
        samples.append(Sample(t=index * step_s, x=float(x), y=float(y), z=float(z)))
    return samples


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--course", type=Path, default=Path(__file__).with_name("course.yaml"))
    parser.add_argument("--trace-csv", type=Path, help="CSV with columns: t,x,y,z")
    parser.add_argument("--use-route", action="store_true", help="score the configured baseline route")
    args = parser.parse_args(list(argv) if argv is not None else None)

    course = load_course(args.course)
    if args.trace_csv:
        samples = load_trace_csv(args.trace_csv)
    elif args.use_route:
        samples = samples_from_route(course)
    else:
        parser.error("provide --trace-csv or --use-route")

    result = score_trace(samples, course)
    for key, value in result.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
