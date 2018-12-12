
from paramiko.client import SSHClient


COMPUTER_COUNT = 50
PAYLOAD_COUNT = 100
LABS = ["162", "164", "165", "167", "405", "418", "420"]
BASE_SSH_NAME = "cf%s-%s"


def main():
    ssh_connections = [None] * PAYLOAD_COUNT

    while True:
        for i in range(PAYLOAD_COUNT):
            if ssh_connections[i] is None or not session_is_active(ssh_connections[i]):
                ssh_connections[i] = get_next_computer_session()
                # do more stuff
            

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

    ssh_client = SSHClient()
    ssh_client.load_system_host_keys()

    while True:
        for lab_name in LABS:
            for computer_index in computer_indices:
                ssh_name = BASE_SSH_NAME % (lab_name, computer_index)

                try:
                    ssh_client.connect(ssh_name)
                except:
                    print("Can't connect to %s, skipping..." % ssh_name)
                    continue
                
                print("Connected to %s" % ssh_name)

                yield ssh_client
                
                ssh_client = SSHClient()
                ssh_client.load_system_host_keys()
