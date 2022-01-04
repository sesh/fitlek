import re
from .thttp import request


SSO_LOGIN_URL = "https://sso.garmin.com/sso/signin"


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
            json=workout.garminconnect_json(),
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
