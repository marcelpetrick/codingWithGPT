import requests

def send_file(filename):
    url = 'http://server-ip:5000/upload'
    files = {'file': open(filename, 'rb')}

    response = requests.post(url, files=files)
    if response.ok:
        print(response.json())  # should print the result: {'result': True/False}
    else:
        print('Error:', response.text)

send_file('mojo.gif')
