import os
import random
import textract
import time
import glob
import teams2016

from datetime import datetime

BASE_POINTS = 10
ROUND_MULTIPLE = 2
NUM_ROUNDS = 6

TOTAL_SIMS = 50000

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
    teams_dict = {}
    # For performing simulations.
    permanent_teams_dict = {}
    sim_points = 0
    num_wins = 0
    win_percentage = 0.0

    def __str__(self):
        return ("Bracket: " + self.bracket_name +
                "\nPoints: " + str(self.points) +
                "\nPPR: " + str(self.ppr) +
                "\nExpected Total Points: " + str(self.expected_points) +
                "\nNum Wins: " + str(self.num_wins) +
                "\nWin Percentage: " + str(self.win_percentage))


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
    entry = BracketEntry()
    entry.permanent_teams_dict = teams_dict
    entry.bracket_name = bracket
    entries.append(entry)

num_sims = 0
while (num_sims < TOTAL_SIMS):
    # Make a copy of the teams dict for new simulation.
    for entry in entries:
        entry.teams_dict = entry.permanent_teams_dict.copy()
        entry.sim_points = 0
        entry.points = 0
        entry.ppr = 0
        entry.expected_points = 0
    current_point_award = BASE_POINTS

    for i in range(NUM_ROUNDS):
        current_round_idx = round_1_win_idx + i
        for j in range(len(prob_rows)):
            rand_val = random.uniform(0, 1)
            for entry in entries:
                row = prob_rows[j]
                # If the team won and the pick was made.
                team_name = id_map[int(row[team_id_idx])]
                if float(row[current_round_idx]) == 1.0 and entry.teams_dict[team_name] > 0:
                    entry.points += current_point_award
                    entry.sim_points += current_point_award
                    entry.expected_points += current_point_award
                    # Remove a selected win from that team.
                    # print(team_name + " won in round " + str(current_round_idx-round_1_win_idx))
                    entry.teams_dict[team_name] -= 1
                elif entry.teams_dict[team_name] > 0:
                    team_percentage = float(row[current_round_idx])
                    added = current_point_award * team_percentage
                    entry.expected_points += added
                    if team_percentage != 0:
                        entry.ppr += current_point_award
                        # Add to simulated points, if correctly picked.
                        if rand_val <= team_percentage:
                            entry.sim_points += current_point_award
                    # print(team_name + " for win in round " + str(current_round_idx-round_1_win_idx) +
                    #       " will get: " + str(added))
                    entry.teams_dict[team_name] -= 1
        # Double the points at the end of the round.
        current_point_award *= ROUND_MULTIPLE
    # Mark who won the simulation.
    entries.sort(key=lambda x: x.sim_points, reverse=True)
    entries[0].num_wins += 1
    # Print every N sims.
    if num_sims % 10000 == 0:
        entries.sort(key=lambda x: x.num_wins, reverse=True)
        for entry in entries:
            if num_sims > 0:
                entry.win_percentage = entry.num_wins*100.0 / num_sims
            print(entry)
        print("\n\n\n")
    # Keep track of the number of simulations.
    num_sims += 1


entries.sort(key=lambda x: x.num_wins, reverse=True)
for entry in entries:
    entry.win_percentage = entry.num_wins*100.0 / TOTAL_SIMS
    print(entry)

