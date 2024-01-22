# Annual Progress Calculator

This Python script calculates the progress of the current year in percentage. It takes into account leap years and provides the functionality to calculate the year's progress for the current date, a specified date, or run unit tests.

![](logo.png)

## Features

- Calculate the current year's progress as a percentage.
- Option to calculate the progress for any specified date.
- Includes unit tests to ensure accuracy, especially for leap years.
- Command-line interface for ease of use.

## Requirements

- Python 3.x

## Usage

To use the script, you have several options:

1. **Current Year Progress**: Simply run the script without any arguments to get the progress of the current year.

```bash
python annualProgress.py
```

2. **Specific Date Progress**: To get the progress for a specific date, use the `-date` option followed by the date in `DD.MM.` format.

```bash
python annualProgress.py -date 31.12.
```

3. **Run Unit Tests**: To run the unit tests, use the `-tests` option.
```bash
python annualProgress.py -tests
```
   

## Development

Developed by Marcel Petrick - mail@marcelpetrick.it

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Contributions

Contributions are welcome.
