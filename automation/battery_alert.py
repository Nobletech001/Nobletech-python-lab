import json
import subprocess

LOW_BATTERY = 20


def get_battery():
    result = subprocess.run(
        ["termux-battery-status"],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


battery = get_battery()

percentage = battery["percentage"]
status = battery["status"]

print(f"Battery: {percentage}%")
print(f"Status: {status}")

if percentage <= LOW_BATTERY and status != "CHARGING":
    subprocess.run([
        "termux-notification",
        "--title",
        "🔋 Low Battery",
        "--content",
        f"Your S23 battery is at {percentage}%. Consider charging it.",
        "--priority",
        "high",
    ])

    print("⚠️ Low-battery notification sent!")
else:
    print("✅ Battery level is okay.")
