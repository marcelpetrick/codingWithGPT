import sys
import pandas as pd


class KUGChecker:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = None

    def load_data(self):
        self.data = pd.read_excel(self.file_path, sheet_name='KUG_April', skiprows=12)

    def check_employee_name(self):
        employee_name_row_index = self.data[self.data.iloc[:, 0].str.contains('Name des Mitarbeiters:', na=False)].index
        if len(employee_name_row_index) > 0:
            employee_name = self.data.iloc[employee_name_row_index[0], 3]
            return pd.isnull(employee_name)
        return True

    def check_vacation_days(self):
        return self.data['Unnamed: 7'].isnull().values.any()

    def check_bottom_date(self):
        bottom_date = self.data.iloc[-1, 1]
        return pd.isnull(bottom_date)

    def check_hours_exceed_10(self):
        hours_logged = self.data['Unnamed: 4'].apply(pd.to_numeric, errors='coerce')
        return (hours_logged > 10).any()

    def check_sum_of_hours(self):
        if 42 in self.data.index:
            sum_of_hours_cell_E53 = self.data.at[42, 'Unnamed: 4']
            return sum_of_hours_cell_E53 == 136
        return False

    def run_checks(self):
        self.load_data()

        errors = []
        if self.check_employee_name():
            errors.append("Employee name is missing.")
        if self.check_vacation_days():
            errors.append("Vacation days not marked with an 'X' in column G.")
        if self.check_bottom_date():
            errors.append("Date at the bottom of the sheet is missing.")
        if self.check_hours_exceed_10():
            errors.append("There are cells with more than 10 hours logged.")
        if not self.check_sum_of_hours():
            errors.append("The sum of hours in cell E53 is missing or incorrect (should be 136 hours).")

        if errors:
            for error in errors:
                print("Error:", error)
        else:
            print("All checks passed. The sheet is correct.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python kug_checker.py input.xlsx")
    else:
        file_path = sys.argv[1]
        checker = KUGChecker(file_path)
        checker.run_checks()
