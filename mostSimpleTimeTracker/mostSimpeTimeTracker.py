# i want to write a time tracking tool in python with pyqt. it should have a minimal ui and be very flexible.
#
# for the ui: when starting the app, you see a main-view, which has just a field (lineedit) where you can enter a name. maximum 30 chars. when pressing enter, then put the value into a model. use this model to create then a list of all items and show them in some radio-box. only the last entered item is selected. unless the user is selecting one of the other elements from the radiobox. the labels of the radiobox-items should be the entered texts.
#
# for the behaviour: as soon as we have a non empty list in the radio-box, log for each second (realtime) which passed, that name into a text-file. the name of the textfile should be the current day. if there is no fitting file with such a name, then create a new one. Else just append to the existing file.
#
# also write me an evaluator: parse the text-file with the entries for the given day. count the appearances of each item. since those are multiples of seconds, convert them into a good human readable format. with hours, minutes, seconds.
# take all that data and put it into the last section (vertical layout for the gui) and show it like this: "item 1: 2 h 1 m; item 2: 1h, .. and so on".
#
# is everything clear? impress me. it is really, important to me.
#
# .. added way more requests ..

from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLineEdit, QRadioButton, QButtonGroup, \
    QLabel, QFrame
from PyQt5.QtGui import QPalette
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QColor
import sys
import datetime
from collections import Counter
import configparser


def seconds_to_hms(seconds):
    """
    Convert seconds to hours, minutes, and seconds format.

    :param int seconds: The number of seconds.
    :return: A string representation of the time in "h m s" format.
    :rtype: str
    """
    h, s = divmod(seconds, 3600)
    m, s = divmod(s, 60)
    return f"{h}h {m}m {s}s"


class TimeTrackingApp(QMainWindow):
    """
    The main window for the time tracking application.
    """

    def __init__(self):
        """
        Initialize the main window.
        """
        super().__init__()

        self.setWindowTitle("Most Simple Time Tracker")

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        self.main_layout = QVBoxLayout()
        central_widget.setLayout(self.main_layout)

        # Line edit for entering item names
        self.line_edit = QLineEdit(self)
        self.line_edit.setMaxLength(30)
        self.line_edit.returnPressed.connect(self.add_item)
        self.main_layout.addWidget(self.line_edit)

        # Divider line
        divider1 = QFrame(self)
        divider1.setFrameShape(QFrame.HLine)
        self.main_layout.addWidget(divider1)

        # Radio box to display the list of items
        self.radio_layout = QVBoxLayout()
        self.main_layout.addLayout(self.radio_layout)
        self.radio_group = QButtonGroup(self)

        # Timer to log the selected item every second and update the used times
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.log_selected_item)
        self.timer.timeout.connect(self.evaluate)
        self.timer.start(1000)

        # Divider line
        divider2 = QFrame(self)
        divider2.setFrameShape(QFrame.HLine)
        self.main_layout.addWidget(divider2)

        # Label to display the evaluation results
        self.results_label = QLabel(self)
        self.main_layout.addWidget(self.results_label)

        # Load configuration
        self.load_configuration()

        # Set color palette
        self.set_palette()

    def set_palette(self):
        """
        Set a light green color palette for the application.
        """
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(240, 255, 240))
        palette.setColor(QPalette.WindowText, QColor(0, 128, 0))
        palette.setColor(QPalette.Base, QColor(245, 255, 245))
        palette.setColor(QPalette.AlternateBase, QColor(240, 255, 240))
        palette.setColor(QPalette.ToolTipBase, QColor(240, 255, 240))
        palette.setColor(QPalette.ToolTipText, QColor(0, 128, 0))
        palette.setColor(QPalette.Text, QColor(0, 128, 0))
        palette.setColor(QPalette.Button, QColor(240, 255, 240))
        palette.setColor(QPalette.ButtonText, QColor(0, 128, 0))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Link, QColor(0, 128, 0))
        palette.setColor(QPalette.Highlight, QColor(0, 128, 0))
        palette.setColor(QPalette.HighlightedText, QColor(240, 255, 240))
        self.setPalette(palette)

    def add_item(self):
        """
        Add a new item to the radio button group.
        """
        item_name = self.line_edit.text().strip()
        if item_name:
            radio_button = QRadioButton(item_name, self)
            self.radio_layout.addWidget(radio_button)
            self.radio_group.addButton(radio_button)
            radio_button.setChecked(True)

    def log_selected_item(self):
        """
        Log the currently selected item every second.
        """
        checked_button = None
        for button in self.radio_group.buttons():
            if button.isChecked():
                checked_button = button
                break

        if checked_button:
            item_name = checked_button.text()
            date = datetime.datetime.now().strftime("%Y-%m-%d")
            with open(f"{date}.txt", "a") as file:
                file.write(f"{item_name}\n")

    def evaluate(self):
        """
        Evaluate the text file for the current day, count the appearances of each item,
        and display the results in a label.
        """
        date = datetime.datetime.now().strftime("%Y-%m-%d")
        try:
            with open(f"{date}.txt", "r") as file:
                lines = file.readlines()
                item_names = [line.strip() for line in lines]
                item_counts = Counter(item_names)
                sorted_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)
                results = [f"{item}: {seconds_to_hms(count)}" for item, count in sorted_items]
                self.results_label.setText("\n".join(results))
        except FileNotFoundError:
            pass

    def load_configuration(self):
        """
        Load the configuration from the config.ini file.
        """
        config = configparser.ConfigParser()
        config.read("config.ini")
        if "items" in config:
            for item_name, status in config["items"].items():
                radio_button = QRadioButton(item_name, self)
                self.radio_layout.addWidget(radio_button)
                self.radio_group.addButton(radio_button)
                if status == "selected":
                    radio_button.setChecked(True)

    def save_configuration(self):
        """
        Save the configuration to the config.ini file.
        """
        config = configparser.ConfigParser()
        config["items"] = {}
        for button in self.radio_group.buttons():
            item_name = button.text()
            if button.isChecked():
                config["items"][item_name] = "selected"
            else:
                config["items"][item_name] = "unselected"
        with open("config.ini", "w") as file:
            config.write(file)

    def closeEvent(self, event):
        """
        Handle the close event of the main window.

        :param event: The close event.
        """
        self.save_configuration()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TimeTrackingApp()
    window.show()
    sys.exit(app.exec_())
