# How to Run:

If you don't pass any arguments, the script will display the usage information:

```bash
python3 script_name.py
```

Output:

```
Usage: python3 script_name.py --path=<path_to_git_repo> --ncommits=<number_of_commits>
Example: python3 script_name.py --path=/home/user/myrepo --ncommits=10
```

To use the script with custom arguments:

```bash
python3 script_name.py --path=/path/to/git/repo --ncommits=10
```

This will check the last 10 commits in the specified Git repository and print the number of changes per file.
