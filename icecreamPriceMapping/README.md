# Icecream prices as heatmap for Bavaria
Idea to vibecode a tool which can map that textual list to some visual representation of icecream-prices for Bavaria.

## data source
* https://www.antenne.de/nachrichten/bayern/der-antenne-bayern-eiskugel-index-2025

## workflow
* data cleaning: convert the input data into a list of format "city-name;price" .. any LLM
* converted first the city-name-list to geo-coordinates (latitude, longitude) - see `locationConverter.py`
* combined it with the price list: `dataCombiner.py` -> cleanData.csv
* vibecode program to display the data on a map (heatmap?) of the outline of Bavaria. With interpolation inbetween. Scaled colors orange/red for high prices to green for low prices? With scale at the side?

## effort
42 minutes with several interruptions for the initial PoC - then 30 min to fix several bugs in computation and display.

## result
![](heatmap_bayern.png)

## todo list
* all done for now

## note
Code for this `tool` is GPL-v3.0.  
The map-files are created by [](https://www.geoboundaries.org/countryDownloads.html) and the icecream-data is from [Antenne Bayern](https://www.antenne.de/nachrichten/bayern/der-antenne-bayern-eiskugel-index-2025).
