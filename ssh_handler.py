

from paramiko.client import SSHClient
from paramiko import AutoAddPolicy
import time
import threading
from queue import Queue

LABS = ["linux", "cf165", "cf167", "cf405", "cf418", "cf420"]
COMPUTER_COUNT = 30
PRINT_DELAY = 20

class SSHHandler():
    def __init__(self, task_tuple_list, command, connection_limit=10):
        self.task_tuple_list = task_tuple_list
        self.command = command
        self.connection_limit = connection_limit
        self.ssh_gen = self.get_ssh_name_gen()
        self.ssh_threads = [None] * self.connection_limit

        self.active_connections = set()

    def run(self):
        connection_thread = threading.Thread()
        last_print_time = time.time()

        while True:
            time.sleep(1)
            if time.time() - last_print_time > PRINT_DELAY:
                last_print_time = time.time()
                print(self.active_connections)

            for i in range(self.connection_limit):
                # We attempt one thread at a time
                if not connection_thread.is_alive() and self.ssh_threads[i] is None:
                    connection_thread = threading.Thread(
                        target=self.create_new_connection,
                        args=(i,)
                    )
                    connection_thread.start()
                
                if self.ssh_threads[i].is_task_done():
                    if not self.ssh_threads[i].is_task_successful():
                        # TODO: Add task to some sort of failed list
                        pass
                    task_sent = self.ssh_threads[i].run_task(self.task_tuple_list.pop(), "test")
                    if not task_sent:
                        print("Task could not be sent to %s, removing..." % self.ssh_threads[i].ssh_name)
                        self.ssh_threads[i] = None
                        continue
                
                while len(self.ssh_threads[i].print_list) != 0:
                    print(self.ssh_threads[i].pop())
                
                

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
            except:
                time.sleep(0.05)
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
        self.task_finish = False
        self.task_successful = False
        self.thread = threading.Thread()
    
    def is_task_done(self):
        return not self.thread.is_alive()
    
    def is_task_successful(self):
        return self.task_successful
    
    def format_command(self, arg_tuple):
        command_str = self.command
        for item in arg_tuple:
            command_str += " "
            if isinstance(item, str):
                command_str += '"' + item + '"'
            else:
                command_str += str(item)
        return command_str
    
    def run_task(self, arg_tuple, task_name=""):
        # TODO: Return false if ssh connection is dead
        # if ssh is dead:
        #    return False

        self.thread = threading.Thread(
            target=self.thread_run_task,
            args=(arg_tuple, task_name))
        self.thread.start()

        return True
    
    def thread_run_task(self, arg_tuple, task_name):
        self.task_successful = False
        command_str = self.format_command(arg_tuple)

        std_in, std_out, std_err = self.ssh_client.exec_command(command_str)
        std_out.channel.setblocking(0)
        std_err.channel.setblocking(0)

        out_data = b""
        err_data = b""

        # TODO: Make sure that we don't exit before reading all the data
        while not std_out.exit_status_ready():
            out_data = self.read_pipe(out_data, std_out, task_name)
            err_data = self.read_pipe(err_data, std_err, task_name)
    
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

    
