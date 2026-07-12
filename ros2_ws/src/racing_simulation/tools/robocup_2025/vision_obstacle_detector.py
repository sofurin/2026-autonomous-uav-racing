#!/usr/bin/env python3
"""Detect simple colored course features from a Gazebo camera image topic.

This is a first vision smoke test for simulation: it subscribes to the x500
monocular camera image, detects blue obstacle structures and yellow route
markers, then prints bounding boxes.  It does not control PX4 yet.
"""

from __future__ import annotations

import argparse
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image as PilImage
from PIL import ImageDraw
from gz.msgs10 import image_pb2
from gz.msgs10.image_pb2 import Image
from gz.transport13 import Node


@dataclass(frozen=True)
class Detection:
    label: str
    cx: int
    cy: int
    area: float
    bbox: tuple[int, int, int, int]


def list_image_topics() -> list[str]:
    try:
        output = subprocess.check_output(["gz", "topic", "-l"], text=True, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return []

    topics = []
    for line in output.splitlines():
        topic = line.strip()
        if not topic:
            continue
        lower = topic.lower()
        if "/image" in lower and "depth" not in lower and "camera_info" not in lower:
            topics.append(topic)
    return sorted(topics)


def wait_for_image_topic(topic: str | None, timeout_s: float) -> str:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        topics = list_image_topics()
        if topic:
            if topic in topics:
                return topic
        elif topics:
            return topics[0]
        time.sleep(0.5)

    available = ", ".join(list_image_topics()) or "none"
    if topic:
        raise TimeoutError(f"Image topic not found: {topic}. Available image topics: {available}")
    raise TimeoutError(f"No Gazebo image topics found. Available image topics: {available}")


def image_to_rgb(msg: Image) -> np.ndarray:
    width = int(msg.width)
    height = int(msg.height)
    step = int(msg.step)
    fmt = int(msg.pixel_format_type)
    data = np.frombuffer(msg.data, dtype=np.uint8)

    channels_by_format = {
        image_pb2.RGB_INT8: 3,
        image_pb2.BGR_INT8: 3,
        image_pb2.RGBA_INT8: 4,
        image_pb2.BGRA_INT8: 4,
        image_pb2.L_INT8: 1,
    }
    if fmt not in channels_by_format:
        raise ValueError(f"unsupported pixel format {fmt}")

    channels = channels_by_format[fmt]
    if step <= 0:
        step = width * channels
    expected = height * step
    if data.size < expected:
        raise ValueError(f"image data too small: got {data.size}, expected {expected}")

    rows = data[:expected].reshape(height, step)
    pixels = rows[:, : width * channels].reshape(height, width, channels)

    if fmt == image_pb2.RGB_INT8:
        return pixels.copy()
    if fmt == image_pb2.BGR_INT8:
        return pixels[:, :, ::-1].copy()
    if fmt == image_pb2.RGBA_INT8:
        return pixels[:, :, :3].copy()
    if fmt == image_pb2.BGRA_INT8:
        return pixels[:, :, 2::-1].copy()
    return np.repeat(pixels, 3, axis=2)


def component_detections(mask: np.ndarray, label: str, min_area: float) -> list[Detection]:
    visited = np.zeros(mask.shape, dtype=bool)
    height, width = mask.shape
    detections: list[Detection] = []

    ys, xs = np.nonzero(mask)
    for start_y, start_x in zip(ys.tolist(), xs.tolist()):
        if visited[start_y, start_x] or not mask[start_y, start_x]:
            continue

        stack = [(start_y, start_x)]
        visited[start_y, start_x] = True
        count = 0
        sum_x = 0
        sum_y = 0
        min_x = max_x = start_x
        min_y = max_y = start_y

        while stack:
            y, x = stack.pop()
            count += 1
            sum_x += x
            sum_y += y
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)

            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not visited[ny, nx]:
                    visited[ny, nx] = True
                    stack.append((ny, nx))

        if count >= min_area:
            detections.append(
                Detection(
                    label=label,
                    cx=int(sum_x / count),
                    cy=int(sum_y / count),
                    area=float(count),
                    bbox=(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1),
                )
            )

    detections.sort(key=lambda detection: detection.area, reverse=True)
    return detections


def find_colored_regions(rgb: np.ndarray, min_area: float) -> list[Detection]:
    rgb_i = rgb.astype(np.int16)
    r = rgb_i[:, :, 0]
    g = rgb_i[:, :, 1]
    b = rgb_i[:, :, 2]

    blue_mask = (b > 70) & (b > g + 25) & (b > r + 45)
    yellow_mask = (r > 130) & (g > 95) & (b < 130) & (r > b + 45) & (g > b + 35)

    detections = component_detections(blue_mask, "blue_obstacle", min_area)
    detections.extend(component_detections(yellow_mask, "yellow_route", min_area))
    detections.sort(key=lambda detection: detection.area, reverse=True)
    return detections


def annotate(rgb: np.ndarray, detections: list[Detection]) -> PilImage.Image:
    out = PilImage.fromarray(rgb)
    draw = ImageDraw.Draw(out)
    colors = {
        "blue_obstacle": (0, 120, 255),
        "yellow_route": (255, 210, 0),
    }
    for detection in detections:
        x, y, w, h = detection.bbox
        color = colors.get(detection.label, (255, 255, 255))
        draw.rectangle((x, y, x + w, y + h), outline=color, width=2)
        draw.ellipse((detection.cx - 4, detection.cy - 4, detection.cx + 4, detection.cy + 4), fill=color)
        draw.text((x, max(0, y - 12)), f"{detection.label}:{int(detection.area)}", fill=color)
    return out


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", help="Gazebo image topic. Defaults to the first non-depth image topic.")
    parser.add_argument("--topic-timeout", type=float, default=30.0)
    parser.add_argument("--duration", type=float, default=0.0, help="Seconds to run; 0 means until Ctrl+C.")
    parser.add_argument("--min-area", type=float, default=350.0)
    parser.add_argument("--print-rate", type=float, default=1.0)
    parser.add_argument("--save-debug", type=Path, help="Write the latest annotated frame to this path.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    topic = wait_for_image_topic(args.topic, args.topic_timeout)
    print(f"Subscribing to Gazebo image topic: {topic}")

    lock = threading.Lock()
    state = {
        "frames": 0,
        "last_rgb": None,
        "last_detections": [],
        "last_error": None,
    }

    def on_image(msg: Image) -> None:
        try:
            rgb = image_to_rgb(msg)
            with lock:
                state["frames"] += 1
                state["last_rgb"] = rgb
                state["last_error"] = None
        except Exception as exc:  # noqa: BLE001 - keep detector alive while experimenting.
            with lock:
                state["last_error"] = str(exc)

    node = Node()
    node.subscribe(Image, topic, on_image)

    start = time.monotonic()
    last_print = 0.0
    try:
        while args.duration <= 0.0 or time.monotonic() - start < args.duration:
            now = time.monotonic()
            if now - last_print >= max(0.1, 1.0 / args.print_rate):
                last_print = now
                with lock:
                    frames = int(state["frames"])
                    rgb = None if state["last_rgb"] is None else state["last_rgb"].copy()
                    error = state["last_error"]
                if error:
                    print(f"frames={frames} error={error}")
                else:
                    detections = [] if rgb is None else find_colored_regions(rgb, args.min_area)
                    with lock:
                        state["last_detections"] = detections
                    summary = ", ".join(
                        f"{d.label}@({d.cx},{d.cy}) area={int(d.area)}" for d in detections[:8]
                    )
                    print(f"frames={frames} detections={len(detections)} {summary}")
                    if args.save_debug and rgb is not None:
                        args.save_debug.parent.mkdir(parents=True, exist_ok=True)
                        annotate(rgb, detections).save(args.save_debug)
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("Stopping detector.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
