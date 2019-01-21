from requests_futures.sessions import FuturesSession
import pickle
import re
import time
import os
import json
import sys

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
PKL_NAME = "partioned_submission_tuple_list.pkl"
CSRF_URL = "https://codeforces.com/contest/1033/status"
SUB_API = "https://codeforces.com/data/submitSource"

PROMISES_AMOUNT = 4
BATCH_SIZE = 50
SLEEP_TIME = 1.2


def download_submissions(tuple_list):
    request_tuple_list = make_requests(tuple_list)

    for file_path, sub_json_result, code_lang in request_tuple_list:
        try:
            sub_dict = json.loads(sub_json_result.text)
            dummy = sub_dict['source']
        except KeyboardInterrupt:
            return
        except:
            print("ERROR: %s failed to load as proper json, skipping..." % file_path)
            continue
        
        new_json_text = sub_json_result.text[:-1]
        new_json_text +=  ', "programmingLanguage": "%s"}' % code_lang

        with open(file_path, "w") as f:
            f.write(sub_json_result.text)

def make_requests(l):
    request_tuple_list = []

    session = FuturesSession()
    csrf_token = get_csrf_token(session)
    promises = [None] * PROMISES_AMOUNT
    file_paths = [None] * PROMISES_AMOUNT
    lang = [None] * PROMISES_AMOUNT
    finish_index_set = set()
    lang_dict = {}

    while len(finish_index_set) != PROMISES_AMOUNT:
        time.sleep(SLEEP_TIME)
        for i in range(PROMISES_AMOUNT):
            if promises[i] is None:
                if len(l) == 0:
                    finish_index_set.add(i)
                    continue

                while (len(l) != 0):
                    sub_id, contest_id, problem_index, code_lang = l.pop()
                    file_path = get_file_path(sub_id, contest_id, problem_index)
                    if file_path is not None:
                        break

                if file_path is None:
                    break

                post_data = {}
                post_data['submissionId'] = sub_id
                post_data['csrf_token'] = csrf_token

                file_paths[i] = file_path
                lang[i] = code_lang
                promises[i] = session.post(SUB_API, data=post_data)
            elif promises[i]._state == "FINISHED":
                request_tuple_list.append((file_paths[i], promises[i].result(), lang[i]))
                file_paths[i] = None
                lang[i] = None
                promises[i] = None

    return request_tuple_list

def get_csrf_token(session):
    r_text = session.get(CSRF_URL).result().text

    search_result = re.search(r'(data-csrf=\'([0-9a-z])+)', r_text)
    csrf_token = search_result.group(0)
    csrf_token = csrf_token.split("='")[1]

    return csrf_token

def get_file_path(sub_id, contest_id, problem_index):
    file_path = os.path.join(BASE_PATH, "data", str(contest_id), problem_index)
    os.makedirs(file_path, exist_ok=True)
    
    file_name = "%s.json" % str(sub_id)
    file_path = os.path.join(file_path, file_name)

    if os.path.isfile(file_path):
        return None
    else:
        return file_path


if __name__ == "__main__":
    with open(sys.argv[1], "rb") as f:
        tuple_list = pickle.load(f)
    download_submissions(tuple_list)

    time.sleep(0.5)
    print("FINISHED")
    time.sleep(0.5)
