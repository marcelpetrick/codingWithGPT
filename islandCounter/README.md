# What is this?
Recreation of the "island counter"-challenge I had to solve some years ago for a coding test for a job inteview. I could not remember the exact notation, but made it up while I went. I guess you can find on hackerrand or geekforgeeks and other pages enough similar challenges.  
So the task was to count the amount of islands in a text-file. The used character-set is { _ , X}, where _ denotes water, X the land. Borders count as water.  
I made up with the help of fitting prompts four text-files as test-cases. Each had an increased number of islands and an increased difficulty (first fully surrounded by water, ..).  

## How?
I created a working solution with unit-test in less than an hour with the help of Chat-GPT-4. Prompts are added as comments above the function-definitions. Of course, I knew the algorithm for the search by heart and I also know how to sequence each single task. (Maybe I should give it a one-shot-prompt and see if this can be done?)
Aside from two tiny errors, which result from my different structure in the local py-file, I saw no flaws. Of course, this is just a minor problem but I would estimate to take for the solution at least 2-4 h.

So the speedup is like 100%? Wow 😲👍🏻

## Resulting call

```
Testing started at 16:24 ...
Launching unittests with arguments python -m unittest islandCounter.TestCountIslands.test_count_islands in C:\mpetrick\repos\codingWithGPT\islandCounter


Ran 1 test in 0.007s

OK
checking now file: dataset\test0_1island.txt
checking now file: dataset\test1_2islands.txt
checking now file: dataset\test2_3islandsWithBorders.txt
checking now file: dataset\test3_4islandsWithBorders.txt

Process finished with exit code 0
```
