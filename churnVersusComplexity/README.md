# Helper to analyze and visualize churn versus complexity` for a git-project

## How to Run the Script

The script analyzes the churn (number of changes) and complexity (cognitive complexity) of files in a Git repository over the last N commits. It also generates a visual representation of churn versus complexity for easier understanding.

### Running Without Arguments

If you don't pass any arguments, the script will display the usage information:

```bash
python3 script_name.py
```

Output:

```
Usage: python3 script_name.py --path=<path_to_git_repo> --ncommits=<number_of_commits> [--rateQmlDifferently]
Example: python3 script_name.py --path=/home/user/myrepo --ncommits=10 --rateQmlDifferently
```

### Running With Custom Arguments

You can run the script with specific arguments to specify the path to the Git repository, the number of commits to analyze, and optional complexity handling for QML files:

```bash
python3 script_name.py --path=/path/to/git/repo --ncommits=1337 --rateQmlDifferently
```

This will analyze the last 10 commits in the specified Git repository and print the number of changes per file, along with the calculated cognitive complexity.

### Input Parameters

- `--path` (optional): Path to the Git repository. Default is the current directory (`.`).
- `--ncommits` (optional): Number of last commits to analyze. Default is `20`.
- `--rateQmlDifferently` (optional): If provided, the script will use a specialized complexity metric for `.qml` files. This is useful for UI code written using Qt's QML language, as it has different complexity characteristics compared to general code.

## Script Functionality

1. **Churn Analysis**: The script uses Git commands to get the last N commits from the specified repository. It then calculates how many times each file has been changed during these commits.

2. **Complexity Calculation**:
   - For general code files, the script calculates cognitive complexity based on the use of control structures, nesting depth, and readability factors.
   - For QML files, if the `--rateQmlDifferently` flag is set, it uses a separate complexity calculation more suited to UI elements, property bindings, and signals.

3. **Generating Visual Output**: After analyzing the churn and complexity, the script generates a scatter plot:
   - **X-axis**: Churn (number of changes per file).
   - **Y-axis**: Cognitive complexity.
   - Each point in the scatter plot represents a file, with a red dot and the filename labeled.
   - The plot can be zoomed interactively, and the filename can be clicked to show more details in the terminal.
   - The plot is saved as `churnVsComplexity.png` with high resolution.

## Example Output

After running the script, you will get a summary of file changes and complexity metrics in the terminal:

```
File changes summary (sorted by most changes):
ui/SystemSettings.qml: 2 changes, Cognitive Complexity: 10
src/KeySimulator.h: 2 changes, Cognitive Complexity: 15
ui/LabeledDelegate.qml: 3 changes, Cognitive Complexity: 20
...
```

Additionally, a scatter plot will be displayed, and a high-resolution version will be saved to `churnVsComplexity.png`.

## Complexity Metrics

- **Cognitive Complexity**: Measures how difficult it is to understand a file. It takes into account control structures, nesting, and readability.
- **QML Complexity**: Specifically for QML files, the script uses a tailored metric that considers UI elements, property bindings, and signal handlers.

## Notes

- The script is intended to help developers understand the relationship between code complexity and how frequently files change (churn), which can point to areas of the codebase that may need refactoring or improvement.
- The interactive plot can be zoomed using the scroll wheel, and clicking on individual points will print details about the selected file in the terminal.
