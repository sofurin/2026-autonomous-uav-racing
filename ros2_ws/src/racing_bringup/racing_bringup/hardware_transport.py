from pathlib import PurePosixPath


def serial_agent_command(device: str, baud: str) -> list[str]:
    normalized_device = str(PurePosixPath(device.strip()))
    if not normalized_device.startswith("/dev/serial/by-id/"):
        raise ValueError(
            "PX4 serial device must use a stable /dev/serial/by-id/... path"
        )

    try:
        normalized_baud = int(baud)
    except ValueError as error:
        raise ValueError("PX4 serial baud must be an integer") from error
    if normalized_baud < 9600 or normalized_baud > 3_000_000:
        raise ValueError("PX4 serial baud must be between 9600 and 3000000")

    return [
        "MicroXRCEAgent",
        "serial",
        "--dev",
        normalized_device,
        "-b",
        str(normalized_baud),
    ]
