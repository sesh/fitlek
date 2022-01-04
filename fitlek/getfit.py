import json
from .utils import request


GETFIT_URL = "http://localhost:7071/api/getfitfromjson"


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
    
    with open("fitlek.fit", "wb") as f:
        f.write(response.content)