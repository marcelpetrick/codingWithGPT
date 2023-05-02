// run in https://qmlonline.kde.org/
//
//Generate me QML (from Qt) code for the following design.
// On the left side we have a sidebar with three buttons with the labels "first", "second", "third". If I click on one of the buttons, then a corresponding view is shown to the right of the sidebar showing the number 1, 2 or 3.

import QtQuick 2.15
import QtQuick.Controls 2.15

ApplicationWindow {
    visible: true
    width: 640
    height: 480
    title: "Sidebar Example"

    Rectangle { // was Row before, which was wrong
        anchors.fill: parent

        // Sidebar with buttons
        Rectangle {
            id: sidebar
            width: parent.width * 0.25
            height: parent.height
            color: "#333"

            Column {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 10

                Button {
                    id: firstButton
                    text: "first"
                    onClicked: stackView.replace(firstView)
                }

                Button {
                    id: secondButton
                    text: "second"
                    onClicked: stackView.replace(secondView)
                }

                Button {
                    id: thirdButton
                    text: "third"
                    onClicked: stackView.replace(thirdView)
                }
            }
        }

        // StackView for different views
        StackView {
            id: stackView
            anchors.left: sidebar.right
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom

            initialItem: firstView

            Component {
                id: firstView
                Item {
                    Text {
                        anchors.centerIn: parent
                        text: "1111"
                        font.pixelSize: 24
                    }
                }
            }

            Component {
                id: secondView
                Item {
                    Text {
                        anchors.centerIn: parent
                        text: "2222"
                        font.pixelSize: 24
                    }
                }
            }

            Component {
                id: thirdView
                Item {
                    Text {
                        anchors.centerIn: parent
                        text: "3333"
                        font.pixelSize: 24
                    }
                }
            }
        }
    }
}
