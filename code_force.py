from queue import Queue, Empty
from requests_futures.sessions import FuturesSession
import json
import os
import pickle
import requests
import threading
import time

CONTEST_LIST_API = "http://codeforces.com/api/contest.list"
SUBMISSION_LIST_API = "https://codeforces.com/api/contest.status?contestId=%s"
PROMISES_AMOUNT = 4

def scrape_code_force(contest_amount=100):
    contest_list_dict = json.loads(requests.get(CONTEST_LIST_API).text)
    contest_ids = []
    i = 0
    for contest_dict in contest_list_dict["result"]:
        # If the contest is finished we'll include it
        if contest_dict["phase"] == "FINISHED":
            contest_ids.append(contest_dict['id'])
            i += 1
            if i == contest_amount:
                break

    print("Contests found: %s" % len(contest_ids))


    submission_result_queue = Queue()
    session = FuturesSession()
    promises = [None] * PROMISES_AMOUNT
    finish_index_set = set()
    while len(finish_index_set) != PROMISES_AMOUNT:
        time.sleep(1.2)
        for i in range(PROMISES_AMOUNT):
            if promises[i] is None:
                if len(contest_ids) != 0:
                    if len(contest_ids) % 5 == 0:
                        print("Remaining contests GET requests: %s" %len(contest_ids))
                    contest_submission_url = SUBMISSION_LIST_API % contest_ids.pop()
                    promises[i] = session.get(contest_submission_url)
                else:
                    finish_index_set.add(i)
            elif promises[i]._state == "FINISHED":
                submission_result_queue.put(promises[i].result())
                promises[i] = None
    
    submission_tuple_list = []
    threads = [None] * 3
    for i in range(len(threads)):
        threads[i] = threading.Thread(target=thread_process_submission_result_queue, args=(submission_result_queue, submission_tuple_list))
        threads[i].start()
    thread_process_submission_result_queue(submission_result_queue, submission_tuple_list)
    
    while threads_are_alive(threads): continue

    print("Saving %s submissions..." % len(submission_tuple_list))

    with open("submission_tuple_list.pkl", "wb") as f:
        pickle.dump(submission_tuple_list, f)
    
    

def threads_are_alive(threads):
    for t in threads:
        if t.is_alive():
            return True
    return False


def thread_process_submission_result_queue(submission_result_queue, submission_tuple_list):
    while True:
        try:
            result = submission_result_queue.get_nowait()
        except Empty:
            return
        
        amount_left = submission_result_queue.qsize()
        if amount_left % 5 == 0:
            print("%s remaining results to parse..." % amount_left)
        
        try:
            contest_submission_dict = json.loads(result.text)
        except:
            print(result.text)
            continue

        if "result" not in contest_submission_dict:
            print(contest_submission_dict)
            continue

        for submission_dict in contest_submission_dict["result"]:
            if submission_dict["verdict"] == "OK":
                submission_lang = submission_dict["programmingLanguage"].lower()
                if "c++" not in submission_lang:
                    continue
                submission_id = submission_dict["id"]
                submission_problem_id = submission_dict["problem"]["contestId"]
                submission_problem_index = submission_dict["problem"]["index"].lower()

                submission_tuple_list.append((submission_id, submission_problem_id, submission_problem_index, submission_lang))
