#!/usr/bin/env python3

import math
import unittest
from pathlib import Path

from score_checker import (
    Sample,
    completed_orbit,
    crossed_gate,
    load_course,
    samples_from_route,
    score_trace,
    time_score,
)


COURSE = load_course(Path(__file__).with_name("course.yaml"))


class ScoreCheckerTest(unittest.TestCase):
    def test_time_score_requires_three_obstacles_and_landing(self):
        self.assertEqual(time_score(55.0, obstacle_count=2, landed=True), 0)
        self.assertEqual(time_score(55.0, obstacle_count=3, landed=False), 0)
        self.assertEqual(time_score(55.0, obstacle_count=3, landed=True), 960)
        self.assertEqual(time_score(100.0, obstacle_count=3, landed=True), 800)
        self.assertEqual(time_score(301.0, obstacle_count=3, landed=True), 0)

    def test_gate_crossing_interpolates_at_gate_plane(self):
        gate = COURSE["gates"]["obs1_01"]
        cx, cy, cz = gate["center"]
        yaw = math.radians(gate["yaw_deg"])
        fx = math.cos(yaw)
        fy = math.sin(yaw)
        samples = [
            Sample(0.0, cx - fx, cy - fy, cz),
            Sample(1.0, cx + fx, cy + fy, cz),
        ]
        self.assertTrue(crossed_gate(samples, gate))

    def test_gate_crossing_rejects_wrong_height(self):
        gate = COURSE["gates"]["obs1_01"]
        cx, cy, _ = gate["center"]
        yaw = math.radians(gate["yaw_deg"])
        fx = math.cos(yaw)
        fy = math.sin(yaw)
        samples = [
            Sample(0.0, cx - fx, cy - fy, 3.5),
            Sample(1.0, cx + fx, cy + fy, 3.5),
        ]
        self.assertFalse(crossed_gate(samples, gate))

    def test_orbit_requires_about_one_full_turn(self):
        flag = COURSE["flags"]["obs5_08"]
        cx, cy, cz = flag["center"]
        radius = flag["radius"]
        samples = [
            Sample(i, cx + radius * math.cos(i * math.pi / 8), cy + radius * math.sin(i * math.pi / 8), cz)
            for i in range(17)
        ]
        self.assertTrue(completed_orbit(samples, flag))

    def test_configured_route_scores_baseline(self):
        result = score_trace(samples_from_route(COURSE), COURSE)
        self.assertTrue(result["takeoff"])
        self.assertTrue(result["landing"])
        self.assertEqual(result["completed_obstacles"], 9)
        self.assertGreaterEqual(result["obstacle_score"], 1200)
        self.assertGreater(result["total_score"], result["obstacle_score"])


if __name__ == "__main__":
    unittest.main()
