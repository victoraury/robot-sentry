import requests
import json
import time

start = time.time()
r = requests.post(
    "http://localhost:8000",
    json.dumps({'x': 1.0, 'y': 2.0})
);
print( (time.time() - start)*1000 )
print(r);

