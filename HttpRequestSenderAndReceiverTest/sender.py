import requests

def send_file(filename):
    url = 'http://marcel-precision3551:5000/upload'
    #url = 'http://127.0.0.1:5000/upload'
    files = {'file': open(filename, 'rb')}

    response = requests.post(url, files=files)
    if response.ok:
        print("response: ", response.json())  # should print the result: {'result': True/False}
    else:
        print('Error:', response.text)

send_file('tempgifs/cam0.gif')
