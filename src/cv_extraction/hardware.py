import platform

import psutil


def get_cpu_model() -> str | None:
    if platform.system() == "Windows":
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            ) as key:
                value, _ = winreg.QueryValueEx(
                    key,
                    "ProcessorNameString"
                )

                return value.strip()
        except OSError:
            pass

    return platform.processor() or None


def capture_hardware() -> dict:
    memory = psutil.virtual_memory()
    battery = psutil.sensors_battery()

    return {
        "cpu": {
            "model": get_cpu_model(),
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_processors": psutil.cpu_count(logical=True)
        },
        "memory": {
            "total_bytes": memory.total,
            "available_before_run_bytes": memory.available
        },
        "power": {
            "plugged_in": (
                battery.power_plugged
                if battery is not None
                else None
            )
        },
        "gpu": {
            "collection_status": "not_collected"
        }
    }