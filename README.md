# code-scraping

This project was used to gather programming solutions and problems from [Codeforces](https://codeforces.com/).

## Files of Interest

### [ssh_handler.py](https://github.com/S-Toad/code-scraping/blob/master/ssh_handler.py)
This is the main program that is ran that will seek out computers to connect to and manage existing connections. It's abstracted enough to allow this project to be used with other web-scraping tasks.
It really should be moved to its own repo at some point...

### [download_submission_requests.py](https://github.com/S-Toad/code-scraping/blob/master/download_submission_requests.py)
This is the main child task. SSHHandler will create connections and then will execute this file on each machine. 

### [code_force.py](https://github.com/S-Toad/code-scraping/blob/master/code_force.py)
This file generates the URLs for every submission to be scraped. This is ran a single time to generate the master list and then it passed off to ssh_handler and download_submission_requests to do the rest.
