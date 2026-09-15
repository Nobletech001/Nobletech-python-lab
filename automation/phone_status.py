import json
import subprocess


def get_battery():
    result = subprocess.run(
        ["termux-battery-status"],
        capture_output=True,
        text=True,
        check=True
    )
    return json.loads(result.stdout)


battery = get_battery()

print("=" * 40)
print("       NOBLETECH PHONE STATUS")
print("=" * 40)

print(f"Battery:   {battery['percentage']}%")
print(f"Status:    {battery['status']}")
print(f"Plugged:   {battery['plugged']}")

print("=" * 40)
