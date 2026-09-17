This directory has a C program `prices.c`. Build and run it:

    gcc -O0 -g -o prices prices.c && ./prices

It crashes with a segmentation fault. It is supposed to print the price of "pear":

    pear costs 45 cents

Find the cause of the crash, fix the source, and confirm it prints the correct line.
Do not change the price data.
