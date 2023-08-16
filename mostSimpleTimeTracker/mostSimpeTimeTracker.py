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


from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLineEdit, QRadioButton, QButtonGroup, QLabel
import sys

class TimeTrackingApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Time Tracking Tool")

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        self.layout = QVBoxLayout()
        central_widget.setLayout(self.layout)

        # Line edit for entering item names
        self.line_edit = QLineEdit(self)
        self.line_edit.setMaxLength(30)
        self.line_edit.returnPressed.connect(self.add_item)
        self.layout.addWidget(self.line_edit)

        # Radio box to display the list of items
        self.radio_group = QButtonGroup(self)
        self.layout.addWidget(QLabel("Items:"))

    def add_item(self):
        item_name = self.line_edit.text().strip()
        if item_name:
            radio_button = QRadioButton(item_name, self)
            self.layout.addWidget(radio_button)
            self.radio_group.addButton(radio_button)
            radio_button.setChecked(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TimeTrackingApp()
    window.show()
    sys.exit(app.exec_())
