import threading
import queue
import subprocess
import os

def init_workers(count):
    [PostprocessingThread().start() for i in range(0, count)]

def put_item(command, uid, name, path):
    directory, filename = os.path.split(path)
    PostprocessingThread.work.put(command.split() + [path, filename, directory, name, uid])

class PostprocessingThread(threading.Thread):
    '''a thread to perform post processing work'''
    work = queue.Queue()

    def __init__(self):
        super().__init__()

    def run(self):
        while True:
            item = self.work.get(block=True)
            subprocess.call(item)
            self.work.task_done()
