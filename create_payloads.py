from shutil import copyfile
import os
import pickle
import sys

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
PKL_NAME = "submission_tuple_list.pkl"

def create_payloads(worker_count):
    pkl_path = os.path.join(BASE_PATH, PKL_NAME)
    if not os.path.isfile(pkl_path):
        print("Please run code_force.py first to generate %s" % PKL_NAME)
        return
    
    with open(pkl_path, "rb") as f:
        submission_tuple_list = pickle.load(f)
    
    partion_list = split(submission_tuple_list, worker_count)

    for i in range(worker_count):
        folder_name = "payload_%s" % str(i)
        folder_path = os.path.join(BASE_PATH, folder_name)
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        
        list_pkl_name = "partioned_submission_tuple_list.pkl"
        list_pkl_path = os.path.join(folder_path, list_pkl_name)

        with open(list_pkl_path, "wb") as f:
            pickle.dump(partion_list[i], f)

        exec_py_code_file = "download_submission_requests.py"
        exec_py_code_source = os.path.join(BASE_PATH, exec_py_code_file)
        exec_py_code_dest = os.path.join(folder_path, exec_py_code_file)
        copyfile(exec_py_code_source, exec_py_code_dest)


def split(l, n):
    return_list = [[] for _ in range(n)]
    chunk_size = len(l) // n

    left_index = 0
    right_index = chunk_size

    for i in range(n):
        return_list[i] = l[left_index:right_index]
        left_index = right_index
        right_index += chunk_size
    
    if chunk_size != len(l):
        for j in range(left_index, len(l)):
            return_list[j - left_index].append(l[j])

    return return_list



if __name__ == "__main__":
    args = sys.argv

    n = 1
    if len(args) == 2:
        n = int(args[1])
    
    create_payloads(n)
    
