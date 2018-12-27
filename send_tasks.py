from ssh_handler import SSHHandler
import os
import pickle

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
PKL_NAME = "submission_tuple_list.pkl"
COMMAND = "/home/ayalaa2/Desktop/code_scrape_env/bin/python -u /home/ayalaa2/Desktop/code-scraping/download_submission_requests.py"

def main:
    pkl_path = os.path.join(BASE_PATH, PKL_NAME)
    with open(pkl_path, "rb") as f:
        submission_tuple_list = pickle.load(f)

    ssh_handler = SSHHandler(submission_tuple_list, COMMAND, connection_limit=30, payload_size=20)
    ssh_handler.run()

if __name__ == "__main__":
    main()
