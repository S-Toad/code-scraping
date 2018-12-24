

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


# TODO: Move this code to its own repo
class SSHHandler():
    def __init__(self, task_tuple_list, command, connection_limit=10, payload_size=10):
        """Constructs an SSHHandler object that will be able to manage SSH connections and send tasks

        task_tuple_list - A list of tuples in which a subset will be sent to computers to complete
        command - A command to be ran, in the form of 'python -u mytask.py', absolute paths are needed
        connection_limit - Upper number of computers to attempt to connect to
        payload_size - Integer specifying how big of a subset to send to computers
        """
        # Store passed variables
        self.task_tuple_list = task_tuple_list
        self.command = command
        self.connection_limit = connection_limit
        self.payload_size = payload_size

        # Create an ssh name generator
        self.ssh_gen = self.get_ssh_name_gen()

        # Hold an array as big as our connections
        self.ssh_threads = [None] * self.connection_limit

        # Computers we're connected to
        self.active_connections = set()

        # Number of batches needing to be sent out.
        # Equiv to the ceil of number of tasks divided by payload size
        self.batch_size = (len(task_tuple_list) + payload_size) // payload_size


    def run(self):
        # Create a thread responsible for creating ssh connections
        connection_thread = threading.Thread()
        # Timestamp of when the last detailed print was
        last_print_time = time.time()
        # Batch we're sending out
        batch_index = 0

        # True while there are tasks to send out or tasks are running
        while batch_index != self.batch_size or self.are_tasks_remaining():
            # Sleep a second between each major loop
            time.sleep(1)
            # Print out detailed infomation each PRINT_DELAY seconds
            if time.time() - last_print_time > PRINT_DELAY:
                last_print_time = time.time()
                print("Active connections: " + str(self.active_connections))
                print("Batch: %s/%s" % (batch_index, self.batch_size))

            # Loop over each connection
            for i in range(self.connection_limit):
                # True if no connection exists
                if self.ssh_threads[i] is None:
                    # True if connection_thread isn't working
                    if not connection_thread.is_alive():
                        # Tell the connection_thread to start attempting to fill this
                        # index with a connection. See def create_new_connection for more information
                        print("Spawning a thread to create a task on %s" % i)
                        connection_thread = threading.Thread(
                            target=self.create_new_connection,
                            args=(i,)
                        )
                        connection_thread.start()
                # True if connection exists and its done
                elif self.ssh_threads[i].is_task_done():
                    # True if the last task was not successful
                    if not self.ssh_threads[i].is_task_successful():
                        print("Last task for %s wasn't successful" % i)
                        # TODO: Read pkl and do something
                        pass
                    # True if ssh connection is still active
                    if self.ssh_threads[i].is_ssh_alive():
                        # Create a pkl payload and get its path
                        pkl_path = self.package_tasks(i)
                        # True if more tasks are left
                        if pkl_path is not None:
                            print("Starting Batch %s" % (batch_index + 1))
                            self.ssh_threads[i].run_task(pkl_path, "-" + str(batch_index + 1))
                            batch_index += 1
                    else:
                        # If the ssh connection is dead, set as None and wait for connection_thread
                        # to spawn a new connection
                        print("Thread %s ssh connection died" % i)
                        self.ssh_threads[i] = None
                else:
                    # If the connection is active and is running a task, print out any output waiting
                    while len(self.ssh_threads[i].print_list) != 0:
                        print(self.ssh_threads[i].print_list.pop())
    
    def are_tasks_remaining(self):
        """Returns true if any ssh thread objects are running a task"""
        # Iterate through each ssh thread object and return True if any are running a task
        for ssh_thread in self.ssh_threads:
            if ssh_thread is not None and not ssh_thread.is_task_done():
                return True
        return False
    
    def package_tasks(self, index):
        """Creates a pkl object containing a subset of tasks, returns path to pkl"""
        # List to hold subset
        new_list = []

        # True if the main list is smaller than the payload size
        if len(self.task_tuple_list) < self.payload_size:
            # If so, the payload is the remaining tasks
            new_list = self.task_tuple_list
            self.task_tuple_list = []
        else:
            # Otherwise get subset of list and update main list
            new_list = self.task_tuple_list[:self.payload_size]
            self.task_tuple_list = self.task_tuple_list[self.payload_size:]

        # If new list was completely empty, return None
        if len(new_list) == 0:
            return None

        # Pkl path is under temp/i.pkl, where is some index
        pkl_path = os.path.join(BASE_PATH, "temp", str(index) + ".pkl")

        with open(pkl_path, "wb") as f:
            pickle.dump(new_list, f)

        return pkl_path


    def create_new_connection(self, index):
        """Attempts to create a new SSHThread object at the given index"""
        # Spawns a paramiko SSHClient
        ssh_client = SSHClient()
        ssh_client.load_system_host_keys()
        ssh_client.set_missing_host_key_policy(AutoAddPolicy())

        # We loop until we can make a connection
        while True:
            # Get the next ssh connection name (hostname) to attempt
            ssh_name = next(self.ssh_gen)
            # Ignore if we already have a connection with this computer
            if ssh_name in self.active_connections:
                continue

            # Try the connection and continue on a fail
            try:
                ssh_client.connect(ssh_name, timeout=TIMEOUT, port=PORT)
            except Exception as e:
                #print(e)
                time.sleep(0.1)
                continue
            
            # Store connection in array and add hostname to set
            self.ssh_threads[index] = SSHThread(ssh_client, self.command, ssh_name)
            self.active_connections.add(ssh_name)
            
            print("Connection made with %s." % ssh_name)
            break

    def get_ssh_name_gen(self):
        """Returns ssh_name_gen generator"""
        # Call the generator
        gen = self.ssh_name_gen()
        # Calls a necessary next to precompute the data
        next(gen)
        return gen

    def ssh_name_gen(self):
        """Generator for lab hostnames"""
        ssh_names = []
        # Iterate over each lab name and append -01, -02, ..., -30
        # These will be our attempted hostnames
        for lab in LABS:
            for i in range(1, COMPUTER_COUNT):
                num_str = "0" + str(i) if i < 10 else str(i)
                ssh_names.append("%s-%s" % (lab, num_str))
        
        # Dummy yield
        yield None

        # Yields a name in ssh_names infinitely
        while True:
            for ssh_name in ssh_names:
                yield ssh_name

class SSHThread():
    def __init__(self, ssh_client, command, ssh_name):
        """Creates an SSHThread object that will handle a SSH connection to a computer
        and handle sending tasks to said computer
        
        ssh_client - Paramiko SSHClient object
        command - command to send to computer
        ssh_name - (hostname) name of computer
        """
        self.ssh_client = ssh_client
        self.command = command
        self.ssh_name = ssh_name

        # print_list will store strings to be printed out by main thread
        self.print_list = []
        # Boolean is the last task was successful or not
        self.task_successful = True
        # Thread to run tasks
        self.thread = threading.Thread()
    
    def is_ssh_alive(self):
        """Returns True if SSHClient is still active"""
        try:
            transport = self.ssh_client.get_transport()
            transport.send_ignore()
            return True
        except:
            return False
    
    def is_task_done(self):
        """Returns False if thread is still running task"""
        return not self.thread.is_alive()
    
    def is_task_successful(self):
        """Returns True if last completed task was successful"""
        return self.task_successful
    
    def run_task(self, pkl_path, task_name=""):
        """Tells thread to start running new task
        pkl_path - path to pkl to pass as an arg
        task_name - prefix string for printing purposes"""
        self.thread = threading.Thread(
            target=self.thread_run_task,
            args=(pkl_path, task_name))
        self.thread.start()

    def thread_run_task(self, pkl_path, task_name):
        """Runs the specify task until finish"""

        # Init to False
        self.task_successful = False
        command_str = self.command + " " + pkl_path

        # Run command and init pipes
        std_in, std_out, std_err = self.ssh_client.exec_command(command_str)

        out_data = b""
        #err_data = b""

        # TODO: Make sure that we don't exit before reading all the data
        while not std_out.channel.exit_status_ready():
            out_data = self.read_pipe(out_data, std_out, task_name)
            # TODO: Fix this pipe?
            #err_data = self.read_pipe(err_data, std_err, task_name)
    
    def read_pipe(self, curr_data, pipe, task_name):
        """Handles reading from a pipe
        curr_data - bytes object containing the current running output
        pipe - pipe to read data from
        task_name - prefix for printing"""
        # TODO: Look for another way to check if theres data to receive?
        # Attempt to get more data
        try:
            data = pipe.channel.recv(1)
        except:
            return curr_data
        
        # If new line, store line as a print statement
        if data == b'\n':
            # Cast to string, format into hostname-taskname: string form
            str_out = curr_data.decode("utf-8")
            self.print_list.append("%s%s: %s" % (self.ssh_name, task_name, str_out))
            # If the program prints FINISHED then the task was successful
            if str_out == "FINISHED":
                self.task_successful = True
            # Returns empty bytes to start a new running output
            return b''
        else:
            # If the last data isn't new line then return what we current have plus the extra data
            return curr_data + data
