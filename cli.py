#! /usr/bin/env python
import json
import sys

from fitlek.garmin import GarminClient
from fitlek.fartlek import create_fartlek_workout

try:
    from fitlek.getfit import getfit_download

    ENABLE_GETFIT = True
except ImportError:
    print("Getfit disabled")
    ENABLE_GETFIT = False


def parse_args(args):
    result = {
        a.split("=")[0]: int(a.split("=")[1])
        if "=" in a and a.split("=")[1].isnumeric()
        else a.split("=")[1]
        if "=" in a
        else True
        for a in args
        if "--" in a
    }
    result["[]"] = [a for a in args if not a.startswith("--")]
    return result


def get_or_throw(d, key, error):
    try:
        return d[key]
    except:
        raise Exception(error)


if __name__ == "__main__":
    args = parse_args(sys.argv)

    duration = get_or_throw(
        args, "--duration", "The --duration value is required (format: MM:SS)"
    )
    target_pace = get_or_throw(
        args,
        "--target-pace",
        "The --target-pace value is required (format: MM:SS - mins/km)",
    )

    workout = create_fartlek_workout(duration, target_pace)

    if "--dry-run" in args:
        print(json.dumps(workout.garminconnect_json(), indent=2))
    elif ENABLE_GETFIT and "--fit" in args:
        getfit_download(workout)
    else:
        username = get_or_throw(
            args, "--username", "The Garmin Connect --username value is required"
        )
        password = get_or_throw(
            args, "--password", "The Garmin Connect --password value is required"
        )

        client = GarminClient(username, password)
        client.connect()
        client.add_workout(workout)

        print(
            "Added workout. Check https://connect.garmin.com/modern/workouts and get ready to run!"
        )
