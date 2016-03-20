import os
import textract
import time
from datetime import datetime

FORECAST_LOC = "fivethirtyeight_ncaa_forecasts.csv"
GENDER_KEY = "gender"
FORECAST_DATE_KEY = "forecast_date"
TEAM_ID_KEY = "team_id"
LEAGUE = "mens"

def teams_to_dict():
    import teams2016
    teams_dict = {}
    for team in teams2016.TEAMS:
        teams_dict[team.replace(" ", "")] = 0
    num_teams = len(teams_dict)
    if num_teams != 64:
        raise ValueError('The number of entered teams is ' + str(num_teams))
    return teams_dict


def count_picks(teams_dict, text):
    lines = text.split(os.linesep)
    total_count = 0
    for line in lines:
        # Remove numbers from the line.
        line = line.decode("utf8")
        no_nums = ''.join([i for i in line if not i.isdigit()])
        result = no_nums.encode('ascii', errors='backslashreplace').replace(" ", "")
        if result in teams_dict:
            teams_dict[result] += 1
            total_count += 1
    return total_count


def resolve_missed_picks(teams_dict):
    pass


def process_538_data():
    f = open(FORECAST_LOC, "r")
    rows = []
    for line in f:
        rows.append(line.strip().split(","))
    # First row is keys. Find the indexes I need.
    gender_idx = 0
    forecast_date_idx = 0
    team_id_idx = 0
    first_row = rows[0]
    for i in range(len(first_row)):
        if first_row[i] == GENDER_KEY:
            gender_idx = i
        elif first_row[i] == FORECAST_DATE_KEY:
            forecast_date_idx = i
        elif first_row[i] == TEAM_ID_KEY:
            team_id_idx = i

    # Filter out old data and women's data.
    latest_date = None
    for i in range(len(rows) - 1, -1, -1):
        if rows[i][gender_idx] != LEAGUE:
            rows.remove(rows[i])
        else:
            # Find the date on each row and determine the last date supplied.
            rows[i][forecast_date_idx] = datetime.fromtimestamp(
                time.mktime(time.strptime(rows[i][forecast_date_idx], "%Y-%m-%d")))
            if latest_date == None or rows[i][forecast_date_idx] > latest_date:
                latest_date = rows[i][forecast_date_idx]
    # Remove any data from a previous date.
    for i in range(len(rows) - 1, -1, -1):
        if rows[i][forecast_date_idx] != latest_date:
            rows.remove(rows[i])
    print(rows)

process_538_data()

# teams_dict = teams_to_dict()
# text = textract.process('bracket_images/luke.pdf', method='pdfminer')
#
# print(count_picks(teams_dict, text))
# print(teams_dict)


