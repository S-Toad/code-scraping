import os
import json
import sqlite3
from sqlite3 import IntegrityError

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

def main():
    database_path = os.path.join(BASE_PATH, 'code_force_data.sqlite')

    with sqlite3.connect(database_path) as conn:
        cursor = conn.cursor()

        cursor.execute("CREATE TABLE IF NOT EXISTS problem_sets"
            "(contest_id INTEGER, problem_id TEXT, count INTEGER, PRIMARY KEY(contest_id, problem_id))")
        cursor.execute("CREATE TABLE IF NOT EXISTS submissions"
            "(contest_id INTEGER, problem_id TEXT, submission_id INTEGER PRIMARY KEY, source_code TEXT, source_lang TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS test_cases"
            "(contest_id INTEGER, problem_id TEXT, test_id INTEGER, test_input TEXT, PRIMARY KEY(contest_id, problem_id, test_id))")
        cursor.execute("CREATE TABLE IF NOT EXISTS test_results"
            "(submission_id INTEGER, test_id INTEGER, time_consumed INTEGER, memory_consumed INTEGER, PRIMARY KEY(submission_id, test_id))")
     
        contest_dirs = os.listdir(os.path.join(BASE_PATH, "data"))
        i = 1
        n = len(contest_dirs)

        for contest_id in contest_dirs:
            print("Starting %s/%s contest..." % (i, n))

            problem_dirs = os.listdir(os.path.join(BASE_PATH, "data", contest_id))    
            for problem_id in problem_dirs:
                problem_dir_path = os.path.join(BASE_PATH, "data", contest_id, problem_id)
                
                submission_count, test_cases = parse_and_write_problem_folder(cursor, problem_dir_path)
                write_contest_problem_to_db(cursor, contest_id, problem_id, submission_count)
                write_test_cases_to_db(cursor, contest_id, problem_id, test_cases)
            
            i += 1


def get_submission_dict_list(problem_dir_path):
    test_count_dict = {}

    for submission_name in os.listdir(problem_dir_path):
        submission_path = os.path.join(problem_dir_path, submission_name)
        with open(submission_path, 'r') as f:
            try:
                json_dict = json.load(f)
            except Exception as e:
                print(e)
                continue
            
            test_count = int(json_dict['testCount'])

            if test_count not in test_count_dict:
                test_count_dict[test_count] = [json_dict]
            else:
                test_count_dict[test_count].append(json_dict)
    
    test_count_key = None
    for key in test_count_dict.keys():
        if test_count_key is None or len(test_count_dict[key]) > len(test_count_dict[test_count_key]):
            test_count_key = key
    
    return test_count_dict[test_count_key]

def parse_and_write_problem_folder(cursor, problem_dir_path):
    submission_dict_list = get_submission_dict_list(problem_dir_path)
    test_count, test_cases = assert_test_cases(submission_dict_list)
    assert_valid(submission_dict_list, test_count)

    problem_id = os.path.basename(problem_dir_path)
    source_code_dict = {}

    successes = 0
    duplicates = 0
    for submission_dict in submission_dict_list:
        if submission_dict['ignore']:
            continue

        successes += 1

        # In format of: "/contest/886/submission/32248056"
        href = submission_dict['href']
        href_split = href.split('/')
        contest_id = href_split[2]
        submission_id = href_split[4]

        source_code = submission_dict['source']
        source_lang = submission_dict['programmingLanguage']

        if source_code in source_code_dict:
            #print("ERROR: %s is a duplicate of %s" % (href, source_code_dict[source_code]))
            duplicates += 1
            continue
        else:
            source_code_dict[source_code] = href

        test_results = extract_test_results(submission_id, submission_dict, test_count)
        write_submission_to_db(cursor, contest_id, submission_id, problem_id, source_code, source_lang, test_results)
    
    if duplicates > 0:
        print("Removed %s duplicates" % duplicates)

    return successes, test_cases

def write_submission_to_db(cursor, contest_id, submission_id, problem_id, source_code, source_lang, test_results):
    statement = "INSERT into submissions (contest_id, problem_id, submission_id, source_code, source_lang) VALUES (?, ?, ?, ?, ?)"
    try:
        cursor.execute(statement, (contest_id, problem_id, submission_id, source_code, source_lang))
    except IntegrityError: pass

    statement = "INSERT into test_results (submission_id, test_id, time_consumed, memory_consumed) VALUES (?,?,?,?)"
    try:
        cursor.executemany(statement, test_results)
    except IntegrityError: pass

def write_contest_problem_to_db(cursor, contest_id, problem_id, submission_count):
    statement = "INSERT into problem_sets (contest_id, problem_id, count) VALUES (?, ?, ?)"
    try:
        cursor.execute(statement, (contest_id, problem_id, submission_count))
    except IntegrityError: pass

def write_test_cases_to_db(cursor, contest_id, problem_id, test_cases):
    statement = "INSERT into test_cases (contest_id, problem_id, test_id, test_input) VALUES (%s, '%s', ?, ?)" % (contest_id, problem_id)
    try:
        cursor.executemany(statement, test_cases)
    except IntegrityError: pass

def extract_test_results(submission_id, submission_dict, test_count):
    test_results = []

    for i in range(1, test_count+1):
        test_results.append((submission_id, i, submission_dict['timeConsumed#%s' % i], submission_dict['memoryConsumed#%s' % i]))

    return test_results

def assert_valid(submission_dict_list, test_count):
    for submission_dict in submission_dict_list:
        for i in range(1, test_count+1):
            assert submission_dict['verdict#%s' % i] == 'OK'

def assert_test_cases(submission_dict_list):
    successes = 0
    fails = 0
    main_index = 0

    while (fails + 1) > successes:
        successes = 0
        fails = 0

        test_count = int(submission_dict_list[main_index]['testCount'])
        test_cases = [None] * test_count

        for i in range(1, test_count+1):
            test_cases[i-1] = (i, submission_dict_list[0]['input#%s' % i])


        for submission_dict in submission_dict_list:
            for i in range(1, test_count+1):
                try:
                    assert test_cases[i-1][1] == submission_dict['input#%s' % i]
                    submission_dict['ignore'] = False
                except:
                    #print("ERROR: Expected '%s' got '%s' on %s" % (repr(test_cases[i-1][1]), repr(submission_dict['input#%s' % i]), submission_dict['href']))
                    submission_dict['ignore'] = True
                    fails += 1
                    main_index = i
                    break
                successes += 1
    
    if fails > 0:
        print("Ignoring %s submissions that failed validation..., keeping %s that succeeded" % (fails, successes))

    return (test_count, test_cases)


if __name__ == "__main__":
    main()
