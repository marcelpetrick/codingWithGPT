# List of potential improvements
* run codespell in parallel over all fitting files
* add for codespell some watchdog (timeout 10s?) - in case the check of a single file takes longer, it can be assumed it is either binary or otherwise specail content - maybe even filter by magic number?
* do a short "review" if a fixing is even fruitful - "two changes" (see git status, etc) are not worth the effort
