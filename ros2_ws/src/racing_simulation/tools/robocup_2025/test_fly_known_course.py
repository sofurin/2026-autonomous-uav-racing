#!/usr/bin/env python3

import unittest
from pathlib import Path

from fly_known_course import (
    enu_to_local_ned,
    request_message_interval,
    route_to_local_setpoints,
    set_offboard_mode,
)
from score_checker import load_course


COURSE = load_course(Path(__file__).with_name("course.yaml"))


class FlyKnownCourseTest(unittest.TestCase):
    def test_enu_to_local_ned_uses_start_zone_as_home(self):
        self.assertEqual(enu_to_local_ned([-4.0, -4.0, 1.6], [-4.0, -4.0, 0.0]), (0.0, 0.0, -1.6))
        self.assertEqual(enu_to_local_ned([-3.0, -2.0, 1.0], [-4.0, -4.0, 0.0]), (2.0, 1.0, -1.0))

    def test_route_to_local_setpoints_starts_at_takeoff_above_home(self):
        setpoints = route_to_local_setpoints(COURSE)
        self.assertEqual(setpoints[0].name, "takeoff")
        self.assertAlmostEqual(setpoints[0].north, 0.0)
        self.assertAlmostEqual(setpoints[0].east, 0.0)
        self.assertAlmostEqual(setpoints[0].down, -1.6)
        self.assertIsNotNone(setpoints[0].yaw_rad)
        self.assertEqual(setpoints[-1].name, "landing")

    def test_set_offboard_mode_waits_for_ack(self):
        calls = []

        class Ack:
            command = 176
            result = 0

        class FakeVehicle:
            def set_mode(self, mode):
                calls.append(mode)

            def recv_match(self, **_kwargs):
                return Ack()

        set_offboard_mode(FakeVehicle())
        self.assertEqual(calls, ["OFFBOARD"])

    def test_requests_local_position_with_set_message_interval(self):
        calls = []

        class Ack:
            command = 511
            result = 0

        class FakeMav:
            def command_long_send(self, *args):
                calls.append(args)

        class FakeVehicle:
            target_system = 1
            target_component = 0
            mav = FakeMav()

            def recv_match(self, **_kwargs):
                return Ack()

        request_message_interval(FakeVehicle(), message_id=32, frequency_hz=20.0)

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][2], 511)
        self.assertEqual(calls[0][4], 32)
        self.assertEqual(calls[0][5], 50_000)


if __name__ == "__main__":
    unittest.main()
