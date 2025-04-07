### 💻 Usage

Run the script directly from terminal with pasted data:

$python3 main.py "$<your tabular data pasted here as a single string>$"

Or pipe it in from a file:

$python3 main.py "$(cat data.txt)$"

---

### 📋 What it does

1. Parses input where **each cell is on a new line** (5 lines per data row).
2. Filters entries containing one of the following names:
   - Saketh, Prajwal, Victor, Sandeep, Thomas, Marcel
3. Separates results into:
   - ❌ People **outside** ±8 hours delta
   - ✅ People **within** ±8 hours delta
4. Displays each group with their respective hours difference.

### ⚠️ Notes

- Input must have repeating 5-line rows, in this order:
  $Department$
  $Name$
  $Acc. Delta 2025$
  $thereof March 2025$
  $thereof prior months$
- The script **ignores incomplete or malformed rows**.
