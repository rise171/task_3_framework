# test_di.py
import threading
import requests

URL = "http://127.0.0.1:8000/di-test"

def worker():
    r = requests.get(URL)
    print(r.json())

threads = []
for _ in range(5):
    t = threading.Thread(target=worker)
    t.start()
    threads.append(t)

for t in threads:
    t.join()