import tkinter as tk
from tkinter import ttk
from datetime import datetime
import re


def convert_date_us_to_german(date_str: str) -> str:
    """
    Converts a date string from US format (e.g. 6/25/2025) to German format (DD.MM.YYYY).
    Handles malformed or irregular formats gracefully.

    Args:
        date_str (str): A date string in US format.

    Returns:
        str: Converted date string in German format, or original string if conversion fails.
    """
    match = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", date_str.strip())
    if match:
        month, day, year = match.groups()
        try:
            date_obj = datetime(int(year), int(month), int(day))
            return date_obj.strftime("%d.%m.%Y")
        except ValueError:
            return date_str
    return date_str


def process_dates(input_text: str) -> str:
    """
    Processes input text line by line and converts date formats.

    Args:
        input_text (str): Multiline string containing dates.

    Returns:
        str: Converted multiline string with dates in German format.
    """
    lines = input_text.strip().splitlines()
    return "\n".join(convert_date_us_to_german(line) for line in lines)


class DateConverterApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("US to German Date Converter")
        self.geometry("600x800")

        self.create_widgets()
        self.bind_events()

    def create_widgets(self):
        self.label_input = ttk.Label(self, text="Paste Dates (US Format):")
        self.label_input.pack(pady=(10, 0))

        self.text_input = tk.Text(self, height=20, wrap=tk.WORD)
        self.text_input.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.label_output = ttk.Label(self, text="Converted Dates (German Format):")
        self.label_output.pack()

        self.text_output = tk.Text(self, height=20, wrap=tk.WORD)
        self.text_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    def bind_events(self):
        self.text_input.bind("<KeyRelease>", lambda event: self.convert_dates())
        self.text_input.bind("<Control-a>", self.select_all)
        self.text_input.bind("<Control-A>", self.select_all)
        self.text_input.bind("<Control-c>", self.copy)
        self.text_input.bind("<Control-C>", self.copy)
        self.text_input.bind("<Control-x>", self.cut)
        self.text_input.bind("<Control-X>", self.cut)
        self.text_input.bind("<Delete>", lambda e: self.text_input.delete("sel.first", "sel.last") if self.text_input.tag_ranges("sel") else None)

        self.text_output.bind("<Control-a>", self.select_all)
        self.text_output.bind("<Control-A>", self.select_all)
        self.text_output.bind("<Control-c>", self.copy)
        self.text_output.bind("<Control-C>", self.copy)

    def convert_dates(self):
        input_data = self.text_input.get("1.0", tk.END)
        output_data = process_dates(input_data)
        self.text_output.config(state=tk.NORMAL)
        self.text_output.delete("1.0", tk.END)
        self.text_output.insert(tk.END, output_data)
        self.text_output.config(state=tk.NORMAL)

    def select_all(self, event):
        widget = event.widget
        widget.tag_add(tk.SEL, "1.0", tk.END)
        widget.mark_set(tk.INSERT, "1.0")
        widget.see(tk.INSERT)
        return 'break'

    def copy(self, event):
        try:
            event.widget.event_generate("<<Copy>>")
        except tk.TclError:
            pass
        return 'break'

    def cut(self, event):
        try:
            event.widget.event_generate("<<Cut>>")
        except tk.TclError:
            pass
        return 'break'


if __name__ == "__main__":
    app = DateConverterApp()
    app.mainloop()
