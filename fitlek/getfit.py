import json
from .thttp import request


GETFIT_URL = "https://getfitfile.azurewebsites.net/api/getfitfromjson"


def getfit_download(workout):
    j = {
        "name": "GetFIT Test",
        "steps": [{
            "intensity": step.step_type,
            "duration": int(step.parsed_end_condition_value()),
            "targetSpeedLow": step.target.from_value if step.target.from_value else None,
            "targetSpeedHigh": step.target.to_value if step.target.to_value else None
        } for step in workout.workout_steps]
    }

    print(json.dumps(j, indent=2))
    response = request(GETFIT_URL, json=j, method="POST")
    
    if response.status == 200:
        with open("fitlek.fit", "wb") as f:
            f.write(response.content)
    else:
        print(response.content)