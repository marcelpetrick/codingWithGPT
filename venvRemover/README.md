# venvRemover

While backing up some directories, I noticed that I don't want to transfer the venv too. Of course, cleaning using git would be a possibility, but I wanted to do this selectively.

So therefore we have this shellscript now, which lists all potential directories and offers to delete them all.

Invoke without parameter: use current working directory as root. Else use the given path.

```
  ./venvRemover.sh                                                                                                                              ✔  1m 12s  
Found the following .venv directories with their sizes:
15M  ./analyzeGPX/.venv
247M  ./faceRecognitionForFolder/.venv
211M  ./mostSimpleTimeTracker/.venv
32M  ./jpg2printablePDF/.venv
575M  ./icecreamPriceMapping/.venv
454M  ./AnswerGeist/.venv
5.4G  ./videoTranscriptionLocally/.venv
161M  ./treemapVisualisation/.venv
117M  ./rsthtech_RSH_A13_5_programmableUsbHub/.venv
30M  ./linkedin_API_test/.venv

Total size to be deleted: 7.0G

Do you want to delete all of them? [y/N]: n
Aborted. No directories were deleted.
```

