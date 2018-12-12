
from paramiko.client import SSHClient
from paramiko import AutoAddPolicy


COMPUTER_COUNT = 50
PAYLOAD_COUNT = 100
PORT = 922
TIMEOUT = 1.0
LABS = ["162", "164", "165", "167", "405", "418", "420"]
BASE_SSH_NAME = "cf%s-%s"

ACTIVATE_COMMAND = "source ~/Desktop/code_scrape_env/bin/activate"
PYTHON_RUN_COMMAND = "python ~/Desktop/code-scraping/payloads/payload_%s/download_submission_requests.py"


def main():
    ssh_connections = [None] * PAYLOAD_COUNT
    computer_session_gen = get_next_computer_session()
    computer_connections = set()

    while True:
        for i in range(PAYLOAD_COUNT):
            if ssh_connections[i] is not None and not session_is_active(ssh_connections[i][1]):
                computer_connections.remove(ssh_connections[i][0])
                ssh_connections[i] = None

            if ssh_connections[i] is None:
                ssh_client = SSHClient()
                ssh_client.load_system_host_keys()
                ssh_client.set_missing_host_key_policy(AutoAddPolicy())

                while True:
                    ssh_name = next(computer_session_gen)
                    if ssh_name in computer_connections:
                        continue

                    try:
                        ssh_client.connect(ssh_name, timeout=TIMEOUT, port=PORT)
                    except:
                        print("Can't connect to %s, skipping..." % ssh_name)
                        continue
                    
                    print("Connection made with %s, telling to run payload_%s..." % (ssh_name, str(i)))
                    
                    computer_connections.add(ssh_name)
                    ssh_connections[i] = (ssh_name, ssh_client)

                    try:
                        ssh_connections[i][1].exec_command(ACTIVATE_COMMAND)
                        ssh_connections[i][1].exec_command(PYTHON_RUN_COMMAND % str(i))
                        break
                    except Exception as e:
                        print(e)



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

    while True:
        for lab_name in LABS:
            for computer_index in computer_indices:
                yield BASE_SSH_NAME % (lab_name, computer_index)

if __name__ == "__main__":
    main()
