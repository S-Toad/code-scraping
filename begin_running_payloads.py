
from paramiko.client import SSHClient
from paramiko import AutoAddPolicy
import time
import threading
from queue import Queue

COMPUTER_COUNT = 30
PAYLOAD_COUNT = 35
PORT = 922
TIMEOUT = 1.0
LABS = ["linux", "165", "167", "405", "418", "420"]
BASE_SSH_NAME = "cf%s-%s"

ACTIVATE_COMMAND = "/home/ayalaa2/Desktop/code_scrape_env/bin/python -u /home/ayalaa2/Desktop/code-scraping/payloads/payload_%s/download_submission_requests.py"


def main():
    ssh_connections = [None] * PAYLOAD_COUNT
    computer_session_gen = get_next_computer_session()
    global computer_connections
    global payload_indices
    computer_connections = set()
    payload_indices = set()
    last_print_time = time.time()

    a = True
    while True:
        time.sleep(1)
        if time.time() - last_print_time > 20:
            print("Active connections: %s" % sorted(computer_connections))
            print("Active\Finished payloads: %s" % payload_indices)
            last_print_time = time.time()
        for i in range(PAYLOAD_COUNT):
            if i in payload_indices:
                continue
            if ssh_connections[i] is None or not ssh_connections[i][2].is_alive():
                ssh_client = SSHClient()
                ssh_client.load_system_host_keys()
                ssh_client.set_missing_host_key_policy(AutoAddPolicy())

                while True:
                    if time.time() - last_print_time > 20:
                        print("Active connections: %s" % sorted(computer_connections))
                        print("Active\Finished payloads: %s" % payload_indices)
                        last_print_time = time.time()
                    time.sleep(0.05)
                    ssh_name = next(computer_session_gen)
                    if ssh_name in computer_connections:
                        continue

                    try:
                        ssh_client.connect(ssh_name, timeout=TIMEOUT, port=PORT)
                    except:
                        #print("Can't connect to %s, skipping..." % ssh_name)
                        continue
                    
                    print("Connection made with %s, telling to run payload_%s..." % (ssh_name, str(i)))
                    t = threading.Thread(target=thread_run_exec, args=(ssh_name, ssh_client, i))
                    t.start()

                    if True:
                        print("%s started succesfully" % ssh_name)
                        computer_connections.add(ssh_name)
                        ssh_connections[i] = (ssh_name, ssh_client, t)
                        payload_indices.add(i)
                        break

def thread_run_exec(ssh_name, ssh_client, payload_index):
    global computer_connections
    global payload_indices
    a, b, c = ssh_client.exec_command(ACTIVATE_COMMAND % str(payload_index))
    curr_out = b""
    b.channel.setblocking(0)
    remove_index = True
    
    clean_payload_name = "payload_"
    if payload_index < 10:
        clean_payload_name += "0" + str(payload_index)
    else:
        clean_payload_name += str(payload_index)

    while not b.channel.exit_status_ready():
        try:
            data = b.channel.recv(1)
            curr_out += data
        except: continue
        if curr_out.endswith(b'\n'):
            str_out = curr_out.decode("utf-8").rstrip()
            curr_out = b""
            print("%s-%s: %s" % (ssh_name, clean_payload_name, str_out))
            if str_out == "FINISHED":
                remove_index = False
    print("%s ended" % ssh_name)
    computer_connections.remove(ssh_name)
    if remove_index:
        payload_indices.remove(payload_index)

def session_is_active(ssh_client):
    try:
        transport = ssh_client.get_transport()
        transport.send_ignore()
        return True
    except:
        return False

def get_next_computer_session():
    computer_indices = []
    for i in range(1, COMPUTER_COUNT + 1):
        computer_index = str(i)
        if i < 10:
            computer_index = "0" + computer_index
        computer_indices.append(computer_index)
    
    computer_names = []
    for lab_name in LABS:
        for computer_index in computer_indices:
            if lab_name == "linux":
                computer_names.append("linux-%s" % computer_index)
            else:
                computer_names.append(BASE_SSH_NAME % (lab_name, computer_index))

    #print(computer_names)
    while True:
        for computer_name in computer_names:
            yield computer_name
if __name__ == "__main__":
    main()
