#! /usr/bin/env python

import json
import random
import re
import sys

import requests

SSO_LOGIN_URL = "https://sso.garmin.com/sso/signin"

SPORT_TYPES = {
    "running": 1,
}

STEP_TYPES = {"warmup": 1, "cooldown": 2, "interval": 3, "recovery": 4}

END_CONDITIONS = {
    "lap.button": 1,
    "time": 2,
    "distance": 3,
}

TARGET_TYPES = {
    "no.target": 1,
    "power.zone": 2,
    "cadence.zone": 3,
    "heart.rate.zone": 4,
    "speed.zone": 5,
    "pace.zone": 6,  # meters per second
}


class GarminClient:
    """
    This is a modified version of:
    https://raw.githubusercontent.com/petergardfjall/garminexport/master/garminexport/garminclient.py

    The Garmin Export project was originally released under the Apache License 2.0.

    Lots of details about the Workouts grokked from:
    https://github.com/mgif/quick-plan
    """

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = None

    def connect(self):
        self.session = requests.Session()
        self._authenticate()

    def _authenticate(self):
        form_data = {
            "username": self.username,
            "password": self.password,
            "embed": "false",
        }
        request_params = {"service": "https://connect.garmin.com/modern"}
        headers = {"origin": "https://sso.garmin.com"}
        auth_response = self.session.post(
            SSO_LOGIN_URL, headers=headers, params=request_params, data=form_data
        )
        if auth_response.status_code != 200:
            raise ValueError("authentication failure: did you enter valid credentials?")
        auth_ticket_url = self._extract_auth_ticket_url(auth_response.text)

        response = self.session.get(auth_ticket_url)
        if response.status_code != 200:
            raise RuntimeError(
                "auth failure: failed to claim auth ticket: {}: {}\n{}".format(
                    auth_ticket_url, response.status_code, response.text
                )
            )

        # appears like we need to touch base with the old API to initiate
        # some form of legacy session. otherwise certain downloads will fail.
        # self.session.get("https://connect.garmin.com/legacy/session")

    @staticmethod
    def _extract_auth_ticket_url(auth_response):
        match = re.search(r'response_url\s*=\s*"(https:[^"]+)"', auth_response)
        if not match:
            raise RuntimeError(
                "auth failure: unable to extract auth ticket URL. did you provide a correct username/password?"
            )
        auth_ticket_url = match.group(1).replace("\\", "")
        return auth_ticket_url

    def add_workout(self, workout):
        response = self.session.post(
            "https://connect.garmin.com/modern/proxy/workout-service/workout",
            json=workout.json(),
            headers={
                "Referer": "https://connect.garmin.com/modern/workout/create/running",
                "NK": "NT",
            },
        )

        return response.json()


class Workout:
    def __init__(self, sport_type, name):
        self.sport_type = sport_type
        self.workout_name = name
        self.workout_steps = []

    def add_step(self, step):
        self.workout_steps.append(step)

    def json(self):
        return {
            "sportType": {
                "sportTypeId": SPORT_TYPES[self.sport_type],
                "sportTypeKey": self.sport_type,
            },
            "workoutName": self.workout_name,
            "workoutSegments": [
                {
                    "segmentOrder": 1,
                    "sportType": {
                        "sportTypeId": SPORT_TYPES[self.sport_type],
                        "sportTypeKey": self.sport_type,
                    },
                    "workoutSteps": [step.json() for step in self.workout_steps],
                }
            ],
        }


class WorkoutStep:
    def __init__(
        self,
        order,
        step_type,
        end_condition="lap.button",
        end_condition_value=None,
        target=None,
    ):
        """Valid end condition values:
        - distance: '2.0km', '1.125km', '1.6km'
        - time: 0:40, 4:20
        - lap.button
        """
        self.order = order
        self.step_type = step_type
        self.end_condition = end_condition
        self.end_condition_value = end_condition_value
        self.target = target or Target()

    def end_condition_unit(self):
        if self.end_condition and self.end_condition.endswith("km"):
            return {"unitKey": "kilometer"}
        else:
            return None

    def parsed_end_condition_value(self):
        # distance
        if self.end_condition_value and self.end_condition_value.endswith("km"):
            return int(float(self.end_condition_value.replace("km", "")) * 1000)

        # time
        elif self.end_condition_value and ":" in self.end_condition_value:
            m, s = [int(x) for x in self.end_condition_value.split(":")]
            return m * 60 + s
        else:
            return None

    def json(self):
        return {
            "type": "ExecutableStepDTO",
            "stepId": None,
            "stepOrder": self.order,
            "childStepId": None,
            "description": None,
            "stepType": {
                "stepTypeId": STEP_TYPES[self.step_type],
                "stepTypeKey": self.step_type,
            },
            "endCondition": {
                "conditionTypeKey": self.end_condition,
                "conditionTypeId": END_CONDITIONS[self.end_condition],
            },
            "preferredEndConditionUnit": self.end_condition_unit(),
            "endConditionValue": self.parsed_end_condition_value(),
            "endConditionCompare": None,
            "endConditionZone": None,
            **self.target.json(),
        }


class Target:
    def __init__(self, target="no.target", to_value=None, from_value=None, zone=None):
        self.target = target
        self.to_value = to_value
        self.from_value = from_value
        self.zone = zone

    def json(self):
        return {
            "targetType": {
                "workoutTargetTypeId": TARGET_TYPES[self.target],
                "workoutTargetTypeKey": self.target,
            },
            "targetValueOne": self.to_value,
            "targetValueTwo": self.from_value,
            "zoneNumber": self.zone,
        }


def mmss_to_seconds(s):
    parts = s.split(":")

    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    else:
        raise Exception("Invalid duration provided, must use mm:ss format")


def seconds_to_mmss(seconds):
    mins = int(seconds / 60)
    seconds = seconds - mins * 60
    return f"{mins:02}:{seconds:02}"


def pace_to_ms(pace):
    seconds = mmss_to_seconds(pace)
    km_h = 60 / (seconds / 60)
    return km_h * 0.27778


def fartlek(target_time):
    target_seconds = mmss_to_seconds(target_time)

    if target_seconds >= 30 * 60:
        # runs greater than 30 minutes == 10 minute warmup / cooldown
        warmup = 60 * 10
        cooldown = 60 * 10
    elif target_seconds >= 20 * 60:
        # runs greater than 20 mins == 8 mins warmup + 4 mins cooldown
        warmup = 60 * 8
        cooldown = 60 * 4
    else:
        # all other runs get a 5 minute warmup and 2 minute cooldown
        warmup = 60 * 5
        cooldown = 60 * 2

    workout = [warmup, cooldown]

    while sum(workout) < target_seconds:
        # add an interval, recovery pair
        interval = 15 * random.randint(2, 8)
        recovery = interval + 15 * random.randint(2, 4)

        workout.insert(-1, interval)
        workout.insert(-1, recovery)

    if sum(workout) > target_seconds:
        # remove the last interval and increase something by the amount remaining
        workout.pop(-2) + workout.pop(-2)
        remaining = target_seconds - sum(workout)
        i = random.randint(1, len(workout) - 1)
        workout[i] += remaining

    return workout


def create_workout(duration, target_pace):
    workout_steps = fartlek(duration)
    target_min = round(pace_to_ms(target_pace), 1)
    target_max = round(pace_to_ms(target_pace) * 0.85, 1)

    w = Workout("running", f"Fitlek ({duration})")
    w.add_step(
        WorkoutStep(
            1,
            "warmup",
            end_condition="time",
            end_condition_value=seconds_to_mmss(workout_steps.pop(0)),
        )
    )

    for i, step in enumerate(workout_steps[:-1]):
        step_type = "interval" if i % 2 == 0 else "recovery"
        target = (
            Target("pace.zone", target_min, target_max)
            if step_type == "interval"
            else Target()
        )
        w.add_step(
            WorkoutStep(
                i + 2,
                step_type,
                end_condition="time",
                end_condition_value=seconds_to_mmss(step),
                target=target,
            )
        )

    w.add_step(
        WorkoutStep(
            len(w.workout_steps) + 1,
            "cooldown",
            end_condition="time",
            end_condition_value=seconds_to_mmss(workout_steps[-1]),
        )
    )
    return w


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
    result["[]"] = [a for a in args if not a.startswith('--')]
    return result


def get_or_throw(d, key, error):
    try:
        return d[key]
    except:
        raise Exception(error)


if __name__ == "__main__":
    args = parse_args(sys.argv)

    duration = get_or_throw(args, '--duration', 'The --duration value is required (format: HH:MM)')
    target_pace = get_or_throw(args, '--target-pace', 'The --target-pace value is required (format: MM:MM - mins/km)')
    username = get_or_throw(args, '--username', 'The Garmin Connect --username value is required')
    password = get_or_throw(args, '--password', 'The Garmin Connect --password value is required')

    workout = create_workout(duration, target_pace)

    client = GarminClient(username, password)
    client.connect()
    client.add_workout(workout)
    print("Added workout. Check https://connect.garmin.com/modern/workouts and get ready to run!")