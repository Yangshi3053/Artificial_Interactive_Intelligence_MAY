import locale
import os
import platform
import socket
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests


LOCATION_CACHE_FILE = Path(__file__).resolve().parent / "location_cache.json"
IP_LOCATION_URL = "https://ipapi.co/json/"


def run_powershell(command):
    """Run a small PowerShell command and return text output."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except OSError:
        return ""

    return result.stdout.strip()


def get_windows_region():
    """Read Windows region and language settings when available."""
    culture = run_powershell("(Get-Culture).Name")
    home_location = run_powershell("(Get-WinHomeLocation).DisplayName")
    timezone_name = run_powershell("(Get-TimeZone).Id")

    return {
        "culture": culture or "unknown",
        "home_location": home_location or "unknown",
        "windows_timezone": timezone_name or "unknown",
    }


def get_ip_location():
    """
    Read approximate location from public IP.

    This is not GPS. It is an approximate network location and can be wrong,
    especially when using VPNs, campus networks, or mobile hotspots.
    """
    try:
        response = requests.get(IP_LOCATION_URL, timeout=8)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException:
        return {
            "available": False,
            "method": "public IP lookup",
            "note": "Approximate IP location unavailable.",
        }
    except ValueError:
        return {
            "available": False,
            "method": "public IP lookup",
            "note": "Location service returned invalid data.",
        }

    return {
        "available": True,
        "method": "public IP lookup, not GPS",
        "city": data.get("city") or "unknown",
        "region": data.get("region") or "unknown",
        "country": data.get("country_name") or "unknown",
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "timezone": data.get("timezone") or "unknown",
        "note": "Approximate network location. Do not treat as exact GPS.",
    }


def get_local_datetime_info():
    """Read the current local date, time, timezone, and UTC offset."""
    now = datetime.now().astimezone()
    timezone_name = now.tzname() or "unknown"

    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "weekday": now.strftime("%A"),
        "timezone_name": timezone_name,
        "utc_offset": now.strftime("%z"),
        "iso": now.isoformat(timespec="seconds"),
    }


def get_basic_computer_info():
    """Read safe basic local computer information."""
    return {
        "computer_name": socket.gethostname(),
        "username": os.environ.get("USERNAME") or os.environ.get("USER") or "unknown",
        "os": platform.platform(),
        "python": platform.python_version(),
        "locale": locale.getlocale(),
    }


def get_local_system_context(include_network_location=True):
    """Collect local system context for the assistant prompt."""
    context = {
        "datetime": get_local_datetime_info(),
        "computer": get_basic_computer_info(),
        "windows_region": get_windows_region(),
        "location": {
            "available": False,
            "method": "not requested",
            "note": "Network location lookup was not requested.",
        },
    }

    if include_network_location:
        context["location"] = get_ip_location()

    return context


def format_local_system_context(context):
    """Format local system context for the model prompt."""
    date_time = context["datetime"]
    computer = context["computer"]
    region = context["windows_region"]
    location = context["location"]

    lines = [
        "Local computer context:",
        f"- Local date: {date_time['date']} ({date_time['weekday']})",
        f"- Local time: {date_time['time']}",
        f"- Local timezone: {date_time['timezone_name']} UTC{date_time['utc_offset']}",
        f"- ISO datetime: {date_time['iso']}",
        f"- Windows culture: {region['culture']}",
        f"- Windows home location: {region['home_location']}",
        f"- Windows timezone id: {region['windows_timezone']}",
        f"- Computer name: {computer['computer_name']}",
        f"- Operating system: {computer['os']}",
        f"- Python version: {computer['python']}",
    ]

    if location.get("available"):
        lines.extend(
            [
                f"- Approximate location method: {location['method']}",
                f"- Approximate city/region/country: {location['city']}, {location['region']}, {location['country']}",
                f"- Approximate latitude/longitude: {location['latitude']}, {location['longitude']}",
                f"- Approximate location timezone: {location['timezone']}",
                f"- Location note: {location['note']}",
            ]
        )
    else:
        lines.append(f"- Location note: {location['note']}")

    return "\n".join(lines)
