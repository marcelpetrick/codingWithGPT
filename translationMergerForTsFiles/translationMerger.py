# idea to fix:
# * take current v1.12.7 release
# * import take the current db from TDM
# * import the given ts-files (`source`)
# * export the ts-files (`target`)
# * create program which does the matchin from `source` to `target` and fixes the `target`-file
#
#-------------------------------------------
#
# translationMergerForTsFiles: helper-tool needed which can fix all open, unfinished translations with translations coming from some other input-file (not context-bound)

# load target ts-file, then check each "unfinished" string
# for each: find the string in the source-file
# replace it with translation
# save resulting file
#
#-------------------------------------------
