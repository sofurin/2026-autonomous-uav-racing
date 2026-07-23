from pathlib import PurePosixPath


def udp_agent_command(port: str) -> list[str]:
    try:
        normalized_port = int(port)
    except ValueError as error:
        raise ValueError("PX4 XRCE UDP port must be an integer") from error
    if normalized_port < 1 or normalized_port > 65_535:
        raise ValueError("PX4 XRCE UDP port must be between 1 and 65535")

    return [
        "MicroXRCEAgent",
        "udp4",
        "-p",
        str(normalized_port),
    ]


def serial_agent_command(device: str, baud: str) -> list[str]:
    device_path = PurePosixPath(device.strip())
    stable_device_directory = PurePosixPath("/dev/serial/by-id")
    if device_path.parent != stable_device_directory or device_path.name in {
        "",
        ".",
        "..",
    }:
        raise ValueError(
            "PX4 serial device must be a direct /dev/serial/by-id/... entry"
        )
    normalized_device = str(device_path)

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
