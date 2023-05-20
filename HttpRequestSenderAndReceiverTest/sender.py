import requests
import time

def send_file(filename):
    #url = 'http://127.0.0.1:5000/upload' # local development
    #url = 'http://marcel-precision3551:5000/upload' # host: laptop
    url = 'http://malina400:5000/upload' # host: the rpi
    files = {'file': open(filename, 'rb')}

    response = requests.post(url, files=files)
    if response.ok:
        print('response:', response.json())  # should print the result: {'result': True/False}
    else:
        print('Error:', response.text)

def processWithTiming(filename):
    startTime = time.time()
    send_file(filename)
    print(f"  processing took {time.time()-startTime}")

processWithTiming('mojo.gif') # FALSE
processWithTiming('cat.gif') # FALSE
processWithTiming('frame09.gif') # TRUE

# stays within 1.2 seconds with request and processing
for i in range(0,9):
    processWithTiming('mojo.gif')
