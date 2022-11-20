from .thttp import request


def upload_to_intervals(workout, athlete_id, api_key):
    url = f"https://intervals.icu/api/v1/athlete/{athlete_id}/folders"

    # check to see if the Run Randomly folder already exists
    response = request(f"https://intervals.icu/api/v1/athlete/{athlete_id}/folders", headers={
        'Authorization': f"Bearer {api_key}",
    })

    folders = [x for x in response.json if x['name'] == 'Run Randomly' and x['type'] == 'FOLDER']

    # create a folder if it doesn't exist
    if not folders:
        response = request(f"https://intervals.icu/api/v1/athlete/{athlete_id}/folders", json={"name": "Run Randomly", "type": "FOLDER"}, method='post', headers={
            'Authorization': f"Bearer {api_key}",
        })
        print(response.json)
        folder = response.json
    else:
        folder = folders[0]

    # create the workout string
    workout_str = ""
    paces = {
        "warmup": "60-80%",
        "interval": "90-120%",
        "recovery": "60-90%",
        "cooldown": "60-80%"
    }

    for step in workout.workout_steps:
        workout_str += step.step_type + "\n"
        workout_str += f"- {step.end_condition_value.replace(':', 'm')}s {paces[step.step_type]} Pace\n\n"

    # upload our workout to that folder
    response = request(f"https://intervals.icu/api/v1/athlete/{athlete_id}/workouts", method="post", json=[{
		"description": workout_str,
		"folder_id": folder['id'],
		"indoor": False,
		"name": workout.workout_name,
		"type": "Run",
    }], headers={
        'Authorization': f"Bearer {api_key}",
    })

    return response.json
