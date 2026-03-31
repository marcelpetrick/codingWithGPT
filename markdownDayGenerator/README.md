# markdownDayGenerator

Generates a reversed list of dates in markdown bullet format with one trailing space (e.g., `* 20250831 `) for use in a daily success journal.

## Purpose

I use this to prep the date headings in my daily success journal.

## Usage

```sh
python3 markdownDayGenerator.py [--month YYYYMM] [--tests]
```

### Parameters

* `--month YYYYMM`
  Generate dates for the given month. Example: `--month 202508` generates dates for August 2025.

* `--tests`
  Run the built-in unit tests to verify functionality.

### Example

```sh
python3 markdownDayGenerator.py --month 202507
```

## License
GPLv3; author mail@marcelpetrick.it
