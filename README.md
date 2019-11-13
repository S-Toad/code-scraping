# code-scraping

This project was used to gather programming solutions and problems from [Codeforces](https://codeforces.com/).

## Files of Interest

### [ssh_handler.py](https://github.com/S-Toad/code-scraping/blob/master/ssh_handler.py)
This main file handles seeking out computers to connect to and manage existing connections. It's capable of handling other scraping tasks as well.
TODO: Move to another repo

### [download_submission_requests.py](https://github.com/S-Toad/code-scraping/blob/master/download_submission_requests.py)
The main child task. SSHHandler executes this child task on each connected machine.

### [code_force.py](https://github.com/S-Toad/code-scraping/blob/master/code_force.py)
This file generates the URLs for every submission that will later be scraped Ran a single time to generate the master list, and then it passed off to ssh_handler and download_submission_requests to do the rest.
