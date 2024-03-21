# Simple test to use the (unofficial) API to get more data out of my Garmin Connect account
* first use case: just acquire general data - works (but commented)
* second use case: acquire all the runs from the current year - works
  * 20 runs, then filtered by grep for the avgHR - wow, amazing

```bash
[mpetrick@marcel-precision3551 simpleGarminConnect]$ python3 simpleGarminConnect.py | grep "averageHR"
        "averageHR": 126.0,
        "averageHR": 139.0,
        "averageHR": 145.0,
        "averageHR": 134.0,
        "averageHR": 118.0,
        "averageHR": 140.0,
        "averageHR": 151.0,
        "averageHR": 146.0,
        "averageHR": 139.0,
        "averageHR": 132.0,
        "averageHR": 149.0,
        "averageHR": 131.0,
        "averageHR": 144.0,
        "averageHR": 123.0,
        "averageHR": 137.0,
        "averageHR": 137.0,
        "averageHR": 117.0,
        "averageHR": 147.0,
        "averageHR": 120.0,
        "averageHR": 133.0,
```