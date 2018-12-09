from bs4 import BeautifulSoup
from queue import Queue, Empty
import json
import time
import threading
import re
import requests
import os

CONTEST_LIST_API = "http://codeforces.com/api/contest.list?gym=%s"
SUBMISSION_LIST_API = "https://codeforces.com/api/contest.status?contestId=%s&count=50"
CONTEST_URL = "http://codeforces.com/contest/%s/status"
GYM_URL = "http://codeforces.com/gym/%s/status/"
SUBMISSION_URL = "https://codeforces.com/contest/%s/submission/%s"

SUBMISSION_INDEX = 0
PROBLEM_INDEX = 2
LANG_INDEX = 3
TIME_INDEX = 5
MEMORY_INDEX = 6


def scrape_code_force(gym=False):
    base_download_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "problem_data")
    contest_list_query = CONTEST_LIST_API % str(gym).lower()

    # Queue to hold id's of contests
    contest_id_queue = Queue()
    # Process an api call into a dictionary
    contest_list_dict = json.loads(requests.get(contest_list_query).text)

    i = 0
    for contest_dict in contest_list_dict["result"]:
        # If the contest is finished we'll include it
        if contest_dict["phase"] == "FINISHED":
            contest_id_queue.put(contest_dict['id'])
            i+=1
            if i == 10:
                break

    print("Contests found: %s" % contest_id_queue.qsize())
    
    # Queue will hold contest id's and submission id's
    submission_id_queue = Queue()
    for _ in range(3):
        t = threading.Thread(target=thread_make_api_calls, args=(contest_id_queue, submission_id_queue))
        t.start()
    thread_make_api_calls(contest_id_queue, submission_id_queue)
    while threading.active_count() != 1:
        continue

    print("Submissions found: %s" % submission_id_queue.qsize())

    # The website is stingy and forces us to use the main thread to make requests
    # Otherwise the threads make calls too quickly and gives us bad results, so the solution
    # is to let the main thread handle the request calls while other threads process parsing
    # requests as they enter the queue


    


    amount = 50
    with open("test.txt", "w") as file:
        while not submission_id_queue.empty():
            contest_id, submission_id = submission_id_queue.get_nowait()
            page_url = SUBMISSION_URL % (contest_id, submission_id)
            file.write(page_url + "\n")
            amount -= 1
            if amount == 0:
                break
    
    return









    # Global variable letting threads know requests are actively being made
    global making_requests
    making_requests = True

    # Queue that requests will be entered to
    # These will start running immediately and wait for the queue while making_requests is true
    request_queue = Queue()
    for _ in range(3):
        t = threading.Thread(target=thread_process_request_queue, args=(base_download_path, request_queue))
        t.start()

    # Start processing requests
    while not submission_id_queue.empty():
        if submission_id_queue.qsize() % 10 == 0:
            print("Remaining submission requests: %s" % submission_id_queue.qsize())

        contest_id, submission_id = submission_id_queue.get_nowait()

        # Make the folder problem_data/contest_id if it doesnt exist
        contest_folder = os.path.join(base_download_path, contest_id)
        if not os.path.isdir(contest_folder):
            os.mkdir(contest_folder)
        
        # Get the submission page and dump the page into the queue
        page_url = SUBMISSION_URL % (contest_id, submission_id)
        r = requests.get(page_url)
        request_queue.put(r.text)
    
    print("All requests have been made. Processing remaining requests...")
    
    # Let threads know that no more requests will be added to the queue
    making_requests = False
    # Let the main thread help out
    thread_process_request_queue(base_download_path, request_queue)
    while threading.active_count() != 1:
        continue

def thread_make_api_calls(contest_id_queue, submission_id_queue):
    while True:
        time.sleep(1)  # Prevent API blocks
        try:
            print("Remaining API requests: %s" % contest_id_queue.qsize())
            contest_id = contest_id_queue.get_nowait()
        except Empty:
            return
        
        submission_list_dict = json.loads(requests.get(SUBMISSION_LIST_API % contest_id).text)

        if submission_list_dict["status"] == "FAILED":
            continue
        
        for submission_dict in submission_list_dict['result']:
            # If the submission is valid and is written in C++, add it to the queue
            if submission_dict['verdict'] == "OK" and "C++" in submission_dict['programmingLanguage']:
                submission_id_queue.put((str(contest_id), str(submission_dict['id'])))


def thread_process_request_queue(base_download_path, request_queue):
    # Let threads know that requests are still being made
    global making_requests
    while True:
        try:
            request_text = request_queue.get_nowait()
        except Empty:
            # If we're still making requests, we wait a moment and continue
            if making_requests:
                time.sleep(1)
                continue
            else:
                return
        
        # Process the page into a soup
        soup = BeautifulSoup(request_text, 'html.parser')

        # Get the first table and the second row of said table
        # Then get all columns of the row
        submission_data = soup.find('table').find_all('tr')[1].find_all('td')

        # Get submission id
        submission_id = submission_data[SUBMISSION_INDEX].text

        # Get the problem name in the format XXXXY where X is the contest id and Y
        # is the problem letter
        problem_name = submission_data[PROBLEM_INDEX].text.lower()
        problem_name = problem_name.split(" -")[0]
        problem_name = problem_name.lstrip()
        problem_name = problem_name.rstrip()
        
        # Split into XXXX and Y here
        contest_id = problem_name[:-1]
        problem_id = problem_name[-1]

        # Get the language that the submission was written in
        code_lang = submission_data[LANG_INDEX].text.lower()
        code_lang = code_lang.rstrip()
        code_lang = code_lang.lstrip()
        code_lang = re.sub(r'  +', r'', code_lang)
        code_lang = code_lang.replace(" ", '_')
        # If there's a version number after c++, i.e, c++ 11, we replace
        # the ++ and space with pp_, otherwise just pp
        if code_lang[-1] == '+':
            code_lang = code_lang.replace("++", "pp")
        else:
            code_lang = code_lang.replace("++", "pp_")


        # Get the elapsed time of the solution
        code_time = submission_data[TIME_INDEX].text
        code_time = code_time.lstrip()
        code_time = code_time.rstrip()
        code_time = code_time[:-3]

        # Get the memory used by the solution
        code_memory = submission_data[MEMORY_INDEX].text
        code_memory = code_memory.lstrip()
        code_memory = code_memory.rstrip()
        code_memory = code_memory[:-3]

        # Find the source code
        source_code = soup.find('pre', {'id': "program-source-text"})

        # If the problem letter folder doesnt exist, make it
        problem_path = os.path.join(base_download_path, contest_id, problem_id)
        if not os.path.isdir(problem_path):
            os.mkdir(problem_path)
        
        # Paths for the code and info on it
        file_path = os.path.join(problem_path, submission_id + '.cpp')
        info_path = os.path.join(problem_path, submission_id + '.yaml')

        # Write the source code
        with open(file_path, 'wb') as source_code_file:
            source_code_file.write(source_code.text.encode())
        
        # Write info about the code
        with open(info_path, 'w') as submission_info_file:
            submission_info_file.write('lang: %s\n' % code_lang)
            submission_info_file.write('time: %s\n' % code_time)
            submission_info_file.write('memory: %s\n' % code_memory)
