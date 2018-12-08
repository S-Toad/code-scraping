from bs4 import BeautifulSoup
from queue import Queue, Empty
import json
import time
import threading
import re
import requests
import os

CONTEST_LIST_API = "http://codeforces.com/api/contest.list?gym=%s"
SUBMISSION_LIST_API = "https://codeforces.com/api/contest.status?contestId=%s&count=100"
CONTEST_URL = "http://codeforces.com/contest/%s/status"
GYM_URL = "http://codeforces.com/gym/%s/status/"
SUBMISSION_URL = "https://codeforces.com/contest/%s/submission/%s"

SUBMISSION_INDEX = 0
PROBLEM_INDEX = 2
LANG_INDEX = 3
TIME_INDEX = 5
MEMORY_INDEX = 6


def scrape_code_force(gym=False):
    contest_list_query = CONTEST_LIST_API % str(gym).lower()
    code_page_url = GYM_URL if gym else CONTEST_URL

    base_download_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "problem_data")
    if not os.path.isdir(base_download_path):
        os.mkdir(base_download_path)


    i = 0
    contest_id_queue = Queue()
    contest_list_dict = json.loads(requests.get(contest_list_query).text)
    for contest_dict in contest_list_dict["result"]:
        if contest_dict["phase"] == "FINISHED":
            contest_id_queue.put(contest_dict['id'])

            i+=1
            if i == 1:
                break
        
    print("Contests found: %s" % contest_id_queue.qsize())
    
    # TODO: Implement per contest per thread
    submission_id_queue = Queue()
    while not contest_id_queue.empty():
        contest_id = contest_id_queue.get_nowait()
        submission_list_request = requests.get(SUBMISSION_LIST_API % contest_id)
        submission_list_dict = json.loads(submission_list_request.text)

        for submission_dict in submission_list_dict['result']:
            if submission_dict['verdict'] != "OK" or "C++" not in submission_dict['programmingLanguage']:
                continue
            submission_id_queue.put((str(contest_id), str(submission_dict['id'])))
    
    print("Submissions found: %s" % submission_id_queue.qsize())

    request_queue = Queue()
    while not submission_id_queue.empty():
        contest_id, submission_id = submission_id_queue.get_nowait()

        problem_folder = os.path.join(base_download_path, contest_id)
        if not os.path.isdir(problem_folder):
            os.mkdir(problem_folder)
        
        page_url = SUBMISSION_URL % (contest_id, submission_id)
        r = requests.get(page_url)
        request_queue.put(r.text)
    
    print("Requests made: %s" % request_queue.qsize())
    
    for _ in range(3):
        t = threading.Thread(target=thread_process_request_queue, args=(base_download_path, request_queue))
        t.start()
    thread_process_request_queue(base_download_path, request_queue)
    while threading.active_count() != 1:
        continue
    

def thread_process_request_queue(base_download_path, request_queue):
    while True:
        try:
            request_text = request_queue.get_nowait()
        except Empty:
            return
        
        soup = BeautifulSoup(request_text, 'html.parser')
        submission_data = soup.find('table').find_all('tr')[1].find_all('td')

        submission_id = submission_data[SUBMISSION_INDEX].text

        problem_name = submission_data[PROBLEM_INDEX].text.lower()
        problem_name = problem_name.split(" -")[0]
        problem_name = problem_name.lstrip()
        problem_name = problem_name.rstrip()
        
        contest_id = problem_name[:-1]
        problem_id = problem_name[-1]

        code_lang = submission_data[LANG_INDEX].text.lower()
        code_lang = code_lang.rstrip()
        code_lang = code_lang.lstrip()
        code_lang = re.sub(r'  +', r'', code_lang)
        code_lang = code_lang.replace(" ", '_')
        if code_lang[-1] == '+':
            code_lang = code_lang.replace("++", "pp")
        else:
            code_lang = code_lang.replace("++", "pp_")


        code_time = submission_data[TIME_INDEX].text
        code_time = code_time.lstrip()
        code_time = code_time.rstrip()
        code_time = code_time[:-3]

        code_memory = submission_data[MEMORY_INDEX].text
        code_memory = code_memory.lstrip()
        code_memory = code_memory.rstrip()
        code_memory = code_memory[:-3]

        source_code = soup.find('pre', {'id': "program-source-text"})

        problem_path = os.path.join(base_download_path, contest_id)
        if not os.path.isdir(problem_path):
            os.mkdir(problem_path)
        
        problem_path = os.path.join(problem_path, problem_id)
        if not os.path.isdir(problem_path):
            os.mkdir(problem_path)
        
        file_path = os.path.join(problem_path, submission_id + '.cpp')
        info_path = os.path.join(problem_path, submission_id + '.yaml')

        with open(file_path, 'wb') as source_code_file:
            source_code_file.write(source_code.text.encode())
        
        with open(info_path, 'w') as submission_info_file:
            submission_info_file.write('lang: %s\n' % code_lang)
            submission_info_file.write('time: %s\n' % code_time)
            submission_info_file.write('memory: %s\n' % code_memory)
