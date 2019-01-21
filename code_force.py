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
    # Call an API request that will return ALL contests
    contest_list_dict = json.loads(requests.get(CONTEST_LIST_API).text)
    
    # Iterate over each contest
    contest_ids = []
    i = 0
    for contest_dict in contest_list_dict["result"]:
        # Only include contests that are FINISHED
        if contest_dict["phase"] == "FINISHED":
            # Append the ID to a list for later
            contest_ids.append(contest_dict['id'])
            i += 1
            if i == contest_amount:
                break

    print("Contests found: %s" % len(contest_ids))

    print(contest_ids)

    # We begin processing each contest API call
    submission_result_queue = Queue()  # Holds API respondes (JSONs) for each contest
    session = FuturesSession()  # Handles calling multiple API requests
    promises = [None] * PROMISES_AMOUNT  # Keep track of our promises
    finish_index_set = set()  # Holds a number of items as we run out of contest IDs to call

    # Begin loop
    while len(finish_index_set) != PROMISES_AMOUNT:
        # Sleep for a moment to avoid being blocked by API
        time.sleep(1.2)

        # Iterate over each promuise...
        for i in range(PROMISES_AMOUNT):
            # if a promise isn't made, we attempt to make one
            if promises[i] is None:
                # True if there's a contest id to process
                if len(contest_ids) != 0:
                    # Every multiple of 5 we print info to the console
                    if len(contest_ids) % 5 == 0:
                        print("Remaining contests GET requests: %s" %len(contest_ids))
                    
                    # Pop off the next contest_id to process and have a promise handle it
                    contest_submission_url = SUBMISSION_LIST_API % contest_ids.pop()
                    promises[i] = session.get(contest_submission_url)
                else:
                    # Otherwise this promise has nothing to do so we add to the finish index set
                    finish_index_set.add(i)
            # True if a promise is done
            elif promises[i]._state == "FINISHED":
                # Place its result (JSON) into a queue
                submission_result_queue.put(promises[i].result())
                promises[i] = None
    
    ignored_code_lang = set()
    included_code_lang = set()
    
    # Begin creation of a few threads to handle parsing the JSONs
    # 3 threads are made and the main thread are told to target 
    # 'thread_process_submission_result_queue' which will run until
    # submission_result_queue is empty
    submission_tuple_list = []
    threads = [None] * 3
    for i in range(len(threads)):
        threads[i] = threading.Thread(target=thread_process_submission_result_queue,
            args=(submission_result_queue, submission_tuple_list, ignored_code_lang, included_code_lang))
        threads[i].start()
    thread_process_submission_result_queue(submission_result_queue, submission_tuple_list, ignored_code_lang, included_code_lang)
    
    # The main thread may finish earlier than the other threads, if so, we wait
    while threads_are_alive(threads): continue

    print("Ignored languages: %s" % ignored_code_lang)
    print("Included languages: %s" % included_code_lang)

    # Save the list of tasks to a pkl
    print("Saving %s submissions..." % len(submission_tuple_list))
    with open("submission_tuple_list.pkl", "wb") as f:
        pickle.dump(submission_tuple_list, f)
    
    
def threads_are_alive(threads):
    for t in threads:
        if t.is_alive():
            return True
    return False


def thread_process_submission_result_queue(submission_result_queue, submission_tuple_list, ignored_code_lang, included_code_lang):
    while True:
        # Attempt to get a contest JSON dump
        try:
            result = submission_result_queue.get_nowait()
        except Empty:
            return
        
        # Print out info every 5 multiple
        amount_left = submission_result_queue.qsize()
        if amount_left % 5 == 0:
            print("%s remaining results to parse..." % amount_left)
        
        # Attempt to parse into a Dictionary
        try:
            contest_submission_dict = json.loads(result.text)
        except:
            print(result.text)
            continue

        # True if the contest has submissions
        if "result" not in contest_submission_dict:
            print(contest_submission_dict)
            continue

        # Iterate through each submission available
        for submission_dict in contest_submission_dict["result"]:
            # True if the submission is valid
            if submission_dict["verdict"] == "OK":

                # Get lanaguage of submission and ensure that it's c++ or c
                submission_lang = submission_dict["programmingLanguage"].lower()
                if "c++" not in submission_lang and "gnu" not in submission_lang and "clang++" not in submission_lang:
                    ignored_code_lang.add(submission_lang)
                    continue
                included_code_lang.add(submission_lang)
                
                # Extract submission ID, contestID, and problemID
                submission_id = submission_dict["id"]
                submission_problem_id = submission_dict["problem"]["contestId"]
                submission_problem_index = submission_dict["problem"]["index"].lower()

                # Dump to a list
                submission_tuple_list.append((submission_id, submission_problem_id, submission_problem_index, submission_lang))
