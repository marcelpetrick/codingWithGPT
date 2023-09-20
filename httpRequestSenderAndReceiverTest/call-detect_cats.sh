#!/bin/bash

# call the python script and pass the parameters
python3 sender_catProcessor.py tempgifs 1
# 1 returns 1 (no cat), 10 returns 0 (found cat)

# store the return code (boolean value) in a variable
is_cat_detected=$?

# print the returned value
echo "Return Value: $is_cat_detected"

# store the returned value for later usage
# this is just an example, you might want to use it differently
if [ $is_cat_detected -eq 0 ]; then
    echo "Cat is detected."
else
    echo "Cat is not detected."
fi


# example: directly manipulated
# $ ./call-detect_cats.sh
# Return Value: 0
# Cat is detected.
