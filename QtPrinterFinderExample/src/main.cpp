#include "PrinterFinderWidget.h"

#include <QApplication>

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);

    PrinterFinderWidget window;
    window.resize(1100, 650);
    window.show();

    return app.exec();
}
