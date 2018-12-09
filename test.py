
import asyncio
import aiohttp
import time
import re
import requests
import os
import threading
from queue import Queue, Empty

amount = 10
submission_ids = []
sub_url = "https://codeforces.com/data/submitSource"
base_download_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_files")

submission_queue = []
with open("test.txt", "r") as file:
    for _ in range(amount):
        url = file.readline().rstrip()
        id = url.split("/")[-1]
        submission_queue.append(id)


async def fetch(url, csrf_token):
    pass

async def main():
    tasks = []
    async with aiohttp.ClientSession() as session:
        for sub_id in submission_queue:
            tasks.append(fetch(session, url, csrf_token))


s = requests.Session()
r = s.get("https://codeforces.com/contest/1090/status")

token_str = re.search(r'(data-csrf=\')([0-9a-z])+\'', r.text)
token_str = token_str.group(0).split("=")[1][1:-1]

for _ in range(3):
    t = threading.Thread(target=thread_test, args=(s, submission_queue, token_str))
    t.start()
while threading.active_count() != 1:
    continue
