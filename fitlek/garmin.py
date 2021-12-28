import json
import random
import re
import sys

from .thttp import request


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
        self.cookiejar = None

    def connect(self):
        self._authenticate()

    def _authenticate(self):
        form_data = {
            "username": self.username,
            "password": self.password,
            "embed": "false",
        }

        request_params = {"service": "https://connect.garmin.com/modern"}
        headers = {
            "origin": "https://sso.garmin.com",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:82.0) Gecko/20100101 Firefox/82.0",
        }

        auth_response = request(
            SSO_LOGIN_URL,
            headers=headers,
            params=request_params,
            data=form_data,
            method="POST",
        )

        self.cookiejar = auth_response.cookiejar

        if auth_response.status != 200:
            raise ValueError("authentication failure: did you enter valid credentials?")

        auth_ticket_url = self._extract_auth_ticket_url(auth_response.content.decode())
        response = request(auth_ticket_url, cookiejar=self.cookiejar, headers=headers)

        if response.status != 200:
            raise RuntimeError(
                "auth failure: failed to claim auth ticket: {}: {}\n{}".format(
                    auth_ticket_url, response.status, response.content
                )
            )

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
        response = request(
            "https://connect.garmin.com/modern/proxy/workout-service/workout",
            method="POST",
            json=workout.json(),
            headers={
                "Referer": "https://connect.garmin.com/modern/workout/create/running",
                "NK": "NT",
                "X-app-ver": "4.38.2.0",
                "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:82.0) Gecko/20100101 Firefox/82.0",
            },
            cookiejar=self.cookiejar,
        )

        if response.status > 299:
            print(response)
        return response.json


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
