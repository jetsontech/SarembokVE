#!/usr/bin/env python3
"""Small, dependency-isolated OpenCV proof-of-life adapter.

This tool intentionally emits Sarembok's normalized event shape instead of
coupling downstream agents to OpenCV APIs. It is suitable for CI smoke tests
and local image probes; production camera capture belongs in a platform adapter.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    args = parser.parse_args()

    try:
        import cv2
    except ImportError as exc:
        raise SystemExit(
            "OpenCV is not installed. Install the vision dependency set before running this probe."
        ) from exc

    frame = cv2.imread(str(args.image))
    if frame is None:
        raise SystemExit(f"Unable to decode image: {args.image}")

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(str(cascade_path))
    faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

    detections = [
        {
            "classId": "face",
            "confidence": None,
            "boundingBox": {
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h),
            },
        }
        for x, y, w, h in faces
    ]

    event = {
        "eventId": f"vision-{datetime.now(timezone.utc).timestamp():.6f}",
        "source": "opencv",
        "sensorId": "file-image",
        "eventType": "vision.detections",
        "timestampUtc": datetime.now(timezone.utc).isoformat(),
        "image": {"width": int(frame.shape[1]), "height": int(frame.shape[0])},
        "detections": detections,
    }
    print(json.dumps(event, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
