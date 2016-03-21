import os
import textract
import time
import glob
import teams2016

from datetime import datetime

BASE_POINTS = 10
ROUND_MULTIPLE = 2
NUM_ROUNDS = 6

FORECAST_LOC = "fivethirtyeight_ncaa_forecasts.csv"
GENDER_KEY = "gender"
FORECAST_DATE_KEY = "forecast_date"
TEAM_ID_KEY = "team_id"
ROUND_1_WIN_KEY = "rd1_win"
ROUND_2_WIN_KEY = "rd2_win"
LEAGUE = "mens"

class BracketEntry:
    bracket_name = ""
    points = 0
    ppr = 0
    expected_points = 0.0

    def __str__(self):
        return ("Bracket: " + self.bracket_name +
                "\nPoints: " + str(self.points) +
                "\nPPR: " + str(self.ppr) +
                "\nExpected Total Points: " + str(self.expected_points))


def teams_to_dict():
    import teams2016
    teams_dict = {}
    for team in teams2016.TEAMS:
        # Start at -1 so that only picks are counted. The name appearing once means nothing.
        teams_dict[team] = -1

    num_teams = len(teams_dict)
    if num_teams != 64:
        raise ValueError('The number of entered teams is ' + str(num_teams))

    id_map = {}
    for i in range(len(teams2016.FTE_TEAM_IDS)):
        id_map[teams2016.FTE_TEAM_IDS[i]] = teams2016.TEAMS[i]

    return teams_dict, id_map


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
        else:
            if result in teams2016.ALTERNATES:
                teams_dict[teams2016.ALTERNATES[result]] += 1
    return total_count


def process_538_data():
    f = open(FORECAST_LOC, "r")
    rows = []
    for line in f:
        rows.append(line.strip().split(","))
    # First row is keys. Find the indexes I need.
    gender_idx = 0
    forecast_date_idx = 0
    team_id_idx = 0
    round_1_win_idx = 0
    round_2_win_idx = 0
    first_row = rows[0]
    for i in range(len(first_row)):
        if first_row[i] == GENDER_KEY:
            gender_idx = i
        elif first_row[i] == FORECAST_DATE_KEY:
            forecast_date_idx = i
        elif first_row[i] == TEAM_ID_KEY:
            team_id_idx = i
        elif first_row[i] == ROUND_1_WIN_KEY:
            round_1_win_idx = i
        elif first_row[i] == ROUND_2_WIN_KEY:
            round_2_win_idx = i
    # Filter out old data and women's data.
    latest_date = None
    for i in range(len(rows) - 1, -1, -1):
        if rows[i][gender_idx] != LEAGUE:
            rows.remove(rows[i])
        # Remove teams that did not win the play in.
        elif float(rows[i][round_1_win_idx]) == 0.0:
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
    return rows, team_id_idx, round_2_win_idx

prob_rows, team_id_idx, round_1_win_idx = process_538_data()

brackets = glob.glob('bracket_images/*.pdf')
entries = []

for bracket in brackets:
    teams_dict, id_map = teams_to_dict()
    text = textract.process(bracket, method='pdfminer')
    count_picks(teams_dict, text)

    points = 0
    expected_points = 0
    ppr = 0
    current_point_award = BASE_POINTS
    for i in range(NUM_ROUNDS):
        current_round_idx = round_1_win_idx + i
        for i in range(len(prob_rows)):
            row = prob_rows[i]
            # If the team won and the pick was made.
            team_name = id_map[int(row[team_id_idx])]
            if float(row[current_round_idx]) == 1.0 and teams_dict[team_name] > 0:
                points += current_point_award
                expected_points += current_point_award
                # Remove a selected win from that team.
                # print(team_name + " won in round " + str(current_round_idx-round_1_win_idx))
                teams_dict[team_name] -= 1
            elif teams_dict[team_name] > 0:
                added = current_point_award * float(row[current_round_idx])
                expected_points += added
                if float(row[current_round_idx]) != 0:
                    ppr += current_point_award
                # print(team_name + " for win in round " + str(current_round_idx-round_1_win_idx) +
                #       " will get: " + str(added))
                teams_dict[team_name] -= 1
        # Double the points at the end of the round.
        current_point_award *= ROUND_MULTIPLE

    entry = BracketEntry()
    entry.bracket_name = bracket
    entry.points = points
    entry.ppr = ppr
    entry.expected_points = expected_points
    entries.append(entry)

entries.sort(key=lambda x: x.expected_points, reverse=True)
for entry in entries:
    print(entry)

