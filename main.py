import os
import textract
import unicodedata

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
        print(result)
        if result in teams_dict:
            teams_dict[result] += 1
            total_count += 1
    return total_count

teams_dict = teams_to_dict()
print(teams_dict)

text = textract.process('bracket_images/luke.pdf', method='pdfminer')

print(count_picks(teams_dict, text))
print(teams_dict)
