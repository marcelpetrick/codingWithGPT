# linkedinLearningEvaluator
# ingest a given file (as first param from command line). default shall be "inputData.txt". parse the file for all titles and also extract the run time length. normalize the values to minutes.
# print then a list of tuples "title: time". als give me the sum of all times in minutes as output to the commandline (stdout). add for each step some status output like "reading data", "processing data", "preparing accumulation", "printing".
# make the code PEP8-compatible and robust and well documented (Sphynx.) assume you are guide van rossum, the python master mind. Write pythonic code!
# let me give you some example text for the structure of the input data:

```
Course: Difficult Situations: Solutions for Managers
1h 6m
Difficult Situations: Solutions for Managers
COURSE Course

    LinkedIn
    By: Todd Dewett and Sara Canaday
    Updated Jun 2020

Completed 6/20/2024

Course: Delivering Employee Feedback
27m
Delivering Employee Feedback
COURSE Course

    LinkedIn
    By: Todd Dewett
    May 2019

Completed 6/18/2024

Course: Social Success at Work
18m
Social Success at Work
COURSE Course

    LinkedIn
    By: Todd Dewett
    Jul 2019

Completed 6/17/2024
```