import threading
import time
from collections import deque

class MyQueue(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.q = deque()
        self.start()

    def run(self):
        while True:
            try:
                print(self.q.popleft())
            except IndexError:
                pass
            time.sleep(1)

    def add_to_q(self, val):
        # this function is called from outside
        self.q.append(val)

# main
# fill the queue with values
qu = MyQueue()
for i in range(0,100):
    qu.add_to_q(i)