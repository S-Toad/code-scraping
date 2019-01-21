

import os
import json
import requests

SUBMISSION_LIST_API = "https://codeforces.com/api/contest.status?contestId=%s"

def main():

    for contest_id in sorted(os.listdir("data")):
        print(contest_id)

        contest_json = SUBMISSION_LIST_API % contest_id
        r = requests.get(contest_json)
        id_dict = create_id_mapping_dict(r.text)

        contest_folder = os.path.join("data", contest_id)
        for problem_id in sorted(os.listdir(contest_folder)):
            print("    " + problem_id)
            problem_folder = os.path.join(contest_folder, problem_id)
            
            for sub_file in os.listdir(problem_folder):
                sub_id = sub_file.split(".")[0]
                code_lang = id_dict[sub_id]

                sub_path = os.path.join(problem_folder, sub_file)
                create_copy(sub_path, code_lang)


def create_id_mapping_dict(contest_json):
    contest_dict = json.loads(contest_json)
    
    id_dict = {}

    for sub_dict in contest_dict["result"]:
        id_dict[str(sub_dict["id"])] = sub_dict["programmingLanguage"]
    
    return id_dict

def create_copy(sub_path, code_lang):
    new_path = "patch_" + sub_path
    dir_path = os.path.dirname(new_path)

    if not os.path.isdir(dir_path):
        os.makedirs(dir_path)

    with open(sub_path, "r") as f1:
        with open(new_path, "w") as f2:
            new_json = f1.read()[:-1]
            #new_json = unicode(new_json, errors='ignore')
            new_json +=  ', "programmingLanguage": "%s"}' % code_lang

            f2.write(new_json)

main()