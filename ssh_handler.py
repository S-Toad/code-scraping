

from paramiko.client import SSHClient
from paramiko import AutoAddPolicy
import time
import threading
import pickle
from queue import Queue
from random import randint
import os

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
LABS = ["linux", "cf165", "cf167", "cf405", "cf418", "cf420"]
COMPUTER_COUNT = 30
PRINT_DELAY = 20
TIMEOUT = 5
PORT = 922

class SSHHandler():
    def __init__(self, task_tuple_list, command, connection_limit=10, payload_size=10):
        self.task_tuple_list = task_tuple_list
        self.command = command
        self.connection_limit = connection_limit
        self.payload_size = payload_size
        self.ssh_gen = self.get_ssh_name_gen()
        self.ssh_threads = [None] * self.connection_limit
        self.pkl_set = set()
        self.active_connections = set()

        self.batch_size = (len(task_tuple_list) + payload_size) // payload_size
        print(self.batch_size)

    def run(self):
        connection_thread = threading.Thread()
        last_print_time = time.time()
        batch_index = 0

        while batch_index != self.batch_size or self.are_tasks_remaining():
            time.sleep(1)
            if time.time() - last_print_time > PRINT_DELAY:
                last_print_time = time.time()
                print("Active connections: " + str(self.active_connections))
                print("Batch: %s/%s" % (batch_index, self.batch_size))

            for i in range(self.connection_limit):
                if self.ssh_threads[i] is None:
                    if not connection_thread.is_alive():
                        print("Spawning a thread to create a task on %s" % i)
                        connection_thread = threading.Thread(
                            target=self.create_new_connection,
                            args=(i,)
                        )
                        connection_thread.start()
                    continue
                elif self.ssh_threads[i].is_task_done():
                    if not self.ssh_threads[i].is_task_successful():
                        print("Last task for %s wasn't succesful" % i)
                        # TODO: Read pkl and do something
                        pass
                    if self.ssh_threads[i].is_ssh_alive():
                        pkl_path = self.package_tasks(i)
                        if pkl_path is None:
                            #print("Empty task list")
                            continue
                        print("Starting Batch %s" % (batch_index + 1))
                        self.ssh_threads[i].run_task(pkl_path, "-" + str(batch_index + 1))
                        batch_index += 1
                    else:
                        print("Thread %s ssh connection died" % i)
                        self.ssh_threads[i] = None
                else:
                    while len(self.ssh_threads[i].print_list) != 0:
                        print(self.ssh_threads[i].print_list.pop())
    
    def are_tasks_remaining(self):
        for ssh_thread in self.ssh_threads:
            if ssh_thread is not None and not ssh_thread.is_task_done():
                return True
        return False
    
    def package_tasks(self, index):
        new_list = []

        if len(self.task_tuple_list) < self.payload_size:
            new_list = self.task_tuple_list
            self.task_tuple_list = []
        else:
            new_list = self.task_tuple_list[:self.payload_size]
            self.task_tuple_list = self.task_tuple_list[self.payload_size:]

        if len(new_list) == 0:
            return None

        pkl_path = os.path.join(BASE_PATH, "temp", str(index) + ".pkl")

        with open(pkl_path, "wb") as f:
            pickle.dump(new_list, f)

        return pkl_path


    def create_new_connection(self, index):
        ssh_client = SSHClient()
        ssh_client.load_system_host_keys()
        ssh_client.set_missing_host_key_policy(AutoAddPolicy())

        while True:
            ssh_name = next(self.ssh_gen)
            if ssh_name in self.active_connections:
                continue

            try:
                ssh_client.connect(ssh_name, timeout=TIMEOUT, port=PORT)
            except Exception as e:
                #print(e)
                time.sleep(0.1)
                continue
            
            self.ssh_threads[index] = SSHThread(ssh_client, self.command, ssh_name)
            self.active_connections.add(ssh_name)
            
            print("Connection made with %s." % ssh_name)
            break

    def get_ssh_name_gen(self):
        gen = self.ssh_name_gen()
        next(gen)
        return gen

    def ssh_name_gen(self):
        ssh_names = []
        for lab in LABS:
            for i in range(1, COMPUTER_COUNT):
                num_str = "0" + str(i) if i < 10 else str(i)
                ssh_names.append("%s-%s" % (lab, num_str))
        yield None
        while True:
            for ssh_name in ssh_names:
                yield ssh_name

class SSHThread():
    def __init__(self, ssh_client, command, ssh_name):
        self.ssh_client = ssh_client
        self.command = command
        self.ssh_name = ssh_name

        self.print_list = []
        self.task_successful = True
        self.thread = threading.Thread()
    
    def is_ssh_alive(self):
        try:
            transport = self.ssh_client.get_transport()
            transport.send_ignore()
            return True
        except:
            return False
    
    def is_task_done(self):
        return not self.thread.is_alive()
    
    def is_task_successful(self):
        return self.task_successful
    
    def run_task(self, pkl_path, task_name=""):
        self.thread = threading.Thread(
            target=self.thread_run_task,
            args=(pkl_path, task_name))
        self.thread.start()

    def thread_run_task(self, pkl_path, task_name):
        self.task_successful = False
        command_str = self.command + " " + pkl_path

        std_in, std_out, std_err = self.ssh_client.exec_command(command_str)

        out_data = b""
        err_data = b""

        # TODO: Make sure that we don't exit before reading all the data
        while not std_out.channel.exit_status_ready():
            out_data = self.read_pipe(out_data, std_out, task_name)
            # TODO: Fix this pipe?
            #err_data = self.read_pipe(err_data, std_err, task_name)
    
    def read_pipe(self, curr_data, pipe, task_name):
        # TODO: Look for another way to check if theres data to receive?
        try:
            data = pipe.channel.recv(1)
        except:
            return curr_data
        
        if data == b'\n':
            str_out = curr_data.decode("utf-8")
            self.print_list.append("%s%s: %s" % (self.ssh_name, task_name, str_out))
            if str_out == "FINISHED":
                self.task_successful = True
            return b''
        else:
            return curr_data + data

    
    def get_output(self):
        pass

    
