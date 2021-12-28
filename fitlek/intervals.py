from .thttp import request


def upload_to_intervals(workout, athlete_id, api_key):
    # url = "https://intervals.icu/api/v1/athlete/{athlete_id}/workouts"
    url = f"https://intervals.icu/api/v1/athlete/{athlete_id}/folders"
    
    # check to see if the Run Randomly folder already exists
    response = request(f"https://intervals.icu/api/v1/athlete/{athlete_id}/folders", basic_auth=("API_KEY", api_key))
    print(response.json)

    folders = [x for x in response.json if x['name'] == 'Run Randomly' and x['type'] == 'FOLDER']

    # create a folder if it doesn't exist
    if not folders:
        response = request(f"https://intervals.icu/api/v1/athlete/{athlete_id}/folders", basic_auth=("API_KEY", api_key), json={"name": "Run Randomly", "type": "FOLDER"}, method='post')
        folder = response.json
    else:
        folder = folders[0]

    # create the workout string
    workout_str = ""
    paces = {
        "warmup": "70%",
        "interval": "100%",
        "recovery": "80%",
        "cooldown": "70%"
    }
    for step in workout.workout_steps:
        workout_str += step.step_type + "\n"
        workout_str += f"- {step.end_condition_value.replace(':', 'm')}s {paces[step.step_type]} Pace\n\n"

    print(workout_str)
    # upload our workout to that folder
    response = request(f"https://intervals.icu/api/v1/athlete/{athlete_id}/workouts", basic_auth=("API_KEY", api_key), method="post", json=[{
		"athlete_id": "i42258",
		"description": workout_str,
		"folder_id": folder['id'],
		"indoor": False,
		"name": workout.workout_name,
		"type": "Run",
    }])
    print(response.json)

    
