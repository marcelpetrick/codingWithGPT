write me a python3 script, wich uses this ollama enpoint to review changed files from a cpp project.

the ollama insance you shall use: http://192.168.100.32:11434/api/tags

run it for each touched file sequentially. files for input are those from the last local commit. use the git history of the current working directory / repo then.

output as markdown.

the prompt aplplied toshall be file each file:

------
Act as an expert reviewer for GCC-built C++/Qt (QML) on embedded + desktop Linux. I will paste C++/QML/CMake/qmake. Find critical failures: runtime crashes/UB, deadlocks, QObject ownership bugs, QML binding loops/null access, plugin/module loading failures, and cross-compilation/deployment breakages.

Return:

Top 10 critical issues (ranked) with exact fixes.

Cross-compile + deployment red flags: sysroot/toolchain, host contamination, pkg-config, install layout, RPATH, Qt plugins/QML imports/qt.conf.

One-hour patch list: smallest changes to reduce crash risk and deployment failures fastest.

Be direct; include corrected snippets.
------
