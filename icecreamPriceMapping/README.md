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
### output of one run - ~5s on the current machine
```sh
python main.py                                                                                             ✔  icecreamPriceMapping  
### Starting Heatmap Generation Process
### Loading Bayern shapefile
### No CRS found for Bayern shapefile. Setting CRS to EPSG:4326 (WGS84).
### Reprojecting Bayern map to EPSG:3857
### Loading input CSV data
### Cleaning price data
### Dropping rows with missing lat/lon/price
### Creating GeoDataFrame from data
### Reprojecting GeoDataFrame to EPSG:3857
### Preparing interpolation grid
### Extracting coordinates and price values
### Filtering valid data points
### Performing cubic interpolation
### Starting plot generation
### Converting grid coordinates from EPSG:3857 to EPSG:4326
### Plotting heatmap
### Plotting Bayern borders in lat/lon
### Plotting original data points in lat/lon
### Adding colorbar and labels
### Formatting axis tick labels for lat/lon
### Adding legend
### Saving plot to heatmap_bayern.png
### Displaying plot
### Heatmap Generation Completed
```
### heatmap
![](heatmap_bayern.png)

### city dots
Since this is hardly readable - here a version with proper map.
![](bayern_dots.png)

## todo list
* all done for now

## note
Code for this `tool` is GPL-v3.0.  
The map-files are created by [](https://www.geoboundaries.org/countryDownloads.html) and the icecream-data is from [Antenne Bayern](https://www.antenne.de/nachrichten/bayern/der-antenne-bayern-eiskugel-index-2025).
