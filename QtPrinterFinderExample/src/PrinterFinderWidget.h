#pragma once

#include <QFutureWatcher>
#include <QWidget>

class QLabel;
class QPushButton;
class QTableWidget;

struct PrinterRecord
{
    QString name;
    QString description;
    QString location;
    QString makeAndModel;
    QString uri;
    QString source;
    QString state;
    bool isDefault = false;
    bool isRemote = false;
    bool installed = false;
};

class PrinterFinderWidget : public QWidget
{
    Q_OBJECT

public:
    explicit PrinterFinderWidget(QWidget *parent = nullptr);

private slots:
    void startDiscovery();
    void finishDiscovery();
    void updatePrintButtonState();
    void printSelectedTestPage();

private:
    static QVector<PrinterRecord> discoverPrinters();
    static QVector<PrinterRecord> discoverQtPrinters();
    static QVector<PrinterRecord> discoverMdnsPrinters();
#ifdef Q_OS_UNIX
    static QVector<PrinterRecord> discoverCupsPrinters();
#endif
    static QString runCommand(const QString &program, const QStringList &arguments);
    static void mergePrinter(QVector<PrinterRecord> &records, const PrinterRecord &candidate);

    void buildUi();
    void populateTable(const QVector<PrinterRecord> &records);
    const PrinterRecord *selectedPrinter() const;

    QPushButton *detectButton = nullptr;
    QPushButton *printButton = nullptr;
    QLabel *statusLabel = nullptr;
    QTableWidget *table = nullptr;
    QVector<PrinterRecord> currentRecords;
    QFutureWatcher<QVector<PrinterRecord>> discoveryWatcher;
};
