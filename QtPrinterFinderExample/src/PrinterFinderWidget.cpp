#include "PrinterFinderWidget.h"

#include <QtConcurrent/QtConcurrent>

#include <QDateTime>
#include <QElapsedTimer>
#include <QHeaderView>
#include <QLabel>
#include <QMessageBox>
#include <QHostAddress>
#include <QPageLayout>
#include <QPainter>
#include <QPrinter>
#include <QPrinterInfo>
#include <QProcess>
#include <QPushButton>
#include <QRegularExpression>
#include <QTableWidget>
#include <QTableWidgetItem>
#include <QUdpSocket>
#include <QVBoxLayout>
#include <QHBoxLayout>

#include <algorithm>
#include <map>

namespace {

enum Column {
    NameColumn = 0,
    StateColumn,
    RemoteColumn,
    DefaultColumn,
    LocationColumn,
    DescriptionColumn,
    ModelColumn,
    UriColumn,
    SourceColumn,
    ColumnCount
};

QString printerStateToString(QPrinter::PrinterState state)
{
    switch (state) {
    case QPrinter::Idle:
        return QStringLiteral("Idle");
    case QPrinter::Active:
        return QStringLiteral("Active");
    case QPrinter::Aborted:
        return QStringLiteral("Aborted");
    case QPrinter::Error:
        return QStringLiteral("Error");
    default:
        return QStringLiteral("Unknown");
    }
}

QByteArray dnsName(const QString &name)
{
    QByteArray result;
    const QStringList labels = name.split('.', Qt::SkipEmptyParts);
    for (const QString &label : labels) {
        const QByteArray bytes = label.toUtf8();
        result.append(char(bytes.size()));
        result.append(bytes);
    }
    result.append(char(0));
    return result;
}

QByteArray mdnsPtrQuery(const QString &serviceName)
{
    QByteArray packet;
    packet.append(char(0));
    packet.append(char(0));
    packet.append(char(0));
    packet.append(char(0));
    packet.append(char(0));
    packet.append(char(1)); // QDCOUNT
    packet.append(QByteArray(6, char(0)));
    packet.append(dnsName(serviceName));
    packet.append(char(0));
    packet.append(char(12)); // PTR
    packet.append(char(0x80));
    packet.append(char(1)); // IN with unicast-response requested
    return packet;
}

quint16 readU16(const QByteArray &packet, int offset)
{
    return (quint8(packet.at(offset)) << 8) | quint8(packet.at(offset + 1));
}

quint32 readU32(const QByteArray &packet, int offset)
{
    return (quint32(readU16(packet, offset)) << 16) | readU16(packet, offset + 2);
}

QString readDnsName(const QByteArray &packet, int &offset, int depth = 0)
{
    if (depth > 8) {
        return QString();
    }

    QStringList labels;
    while (offset < packet.size()) {
        const quint8 length = quint8(packet.at(offset++));
        if (length == 0) {
            break;
        }

        if ((length & 0xc0) == 0xc0) {
            if (offset >= packet.size()) {
                break;
            }
            int pointer = ((length & 0x3f) << 8) | quint8(packet.at(offset++));
            labels.append(readDnsName(packet, pointer, depth + 1));
            break;
        }

        if (offset + length > packet.size()) {
            break;
        }
        labels.append(QString::fromUtf8(packet.mid(offset, length)));
        offset += length;
    }

    return labels.join('.');
}

struct MdnsService
{
    QString instance;
    QString host;
    QString protocol;
    QString path;
    QString location;
    QString model;
    quint16 port = 0;
};

void parseTxtRecord(const QByteArray &data, MdnsService &service)
{
    int offset = 0;
    while (offset < data.size()) {
        const int length = quint8(data.at(offset++));
        if (offset + length > data.size()) {
            break;
        }

        const QString entry = QString::fromUtf8(data.mid(offset, length));
        offset += length;

        const int equals = entry.indexOf('=');
        const QString key = equals > 0 ? entry.left(equals).toLower() : entry.toLower();
        const QString value = equals > 0 ? entry.mid(equals + 1) : QString();
        if (key == QStringLiteral("rp")) {
            service.path = value;
        } else if (key == QStringLiteral("note")) {
            service.location = value;
        } else if (key == QStringLiteral("ty")) {
            service.model = value;
        }
    }
}

void parseMdnsPacket(const QByteArray &packet, std::map<QString, MdnsService> &services)
{
    if (packet.size() < 12) {
        return;
    }

    int offset = 12;
    const quint16 questionCount = readU16(packet, 4);
    const quint16 answerCount = readU16(packet, 6);
    const quint16 authorityCount = readU16(packet, 8);
    const quint16 additionalCount = readU16(packet, 10);

    for (int i = 0; i < questionCount; ++i) {
        readDnsName(packet, offset);
        offset += 4;
        if (offset > packet.size()) {
            return;
        }
    }

    const int recordCount = answerCount + authorityCount + additionalCount;
    for (int i = 0; i < recordCount; ++i) {
        const QString name = readDnsName(packet, offset);
        if (offset + 10 > packet.size()) {
            return;
        }

        const quint16 type = readU16(packet, offset);
        offset += 2;
        offset += 2; // class
        readU32(packet, offset);
        offset += 4;
        const quint16 dataLength = readU16(packet, offset);
        offset += 2;
        if (offset + dataLength > packet.size()) {
            return;
        }

        int dataOffset = offset;
        if (type == 12) { // PTR
            const QString instance = readDnsName(packet, dataOffset);
            MdnsService &service = services[instance];
            service.instance = instance;
            service.protocol = name.contains(QStringLiteral("_ipps._tcp"), Qt::CaseInsensitive)
                ? QStringLiteral("ipps")
                : QStringLiteral("ipp");
        } else if (type == 33) { // SRV
            MdnsService &service = services[name];
            service.instance = name;
            dataOffset += 4; // priority, weight
            service.port = readU16(packet, dataOffset);
            dataOffset += 2;
            service.host = readDnsName(packet, dataOffset);
        } else if (type == 16) { // TXT
            MdnsService &service = services[name];
            service.instance = name;
            parseTxtRecord(packet.mid(offset, dataLength), service);
        }

        offset += dataLength;
    }
}

QString instanceDisplayName(QString instance)
{
    instance.remove(QRegularExpression(QStringLiteral("\\._ipps?\\._tcp\\.local\\.?$"),
                                       QRegularExpression::CaseInsensitiveOption));
    return instance;
}

} // namespace

PrinterFinderWidget::PrinterFinderWidget(QWidget *parent)
    : QWidget(parent)
{
    buildUi();

    connect(&discoveryWatcher, &QFutureWatcher<QVector<PrinterRecord>>::finished,
            this, &PrinterFinderWidget::finishDiscovery);
}

void PrinterFinderWidget::buildUi()
{
    setWindowTitle(QStringLiteral("Qt Network Printer Finder"));

    detectButton = new QPushButton(QStringLiteral("Detect network printers"), this);
    printButton = new QPushButton(QStringLiteral("Print test page"), this);
    printButton->setEnabled(false);

    statusLabel = new QLabel(QStringLiteral("Press detect to search for configured and advertised printers."), this);

    auto *buttonLayout = new QHBoxLayout;
    buttonLayout->addWidget(detectButton);
    buttonLayout->addWidget(printButton);
    buttonLayout->addStretch();

    table = new QTableWidget(this);
    table->setColumnCount(ColumnCount);
    table->setHorizontalHeaderLabels({
        QStringLiteral("Name"),
        QStringLiteral("State"),
        QStringLiteral("Network"),
        QStringLiteral("Default"),
        QStringLiteral("Location"),
        QStringLiteral("Description"),
        QStringLiteral("Make / Model"),
        QStringLiteral("URI"),
        QStringLiteral("Source")
    });
    table->setSelectionBehavior(QAbstractItemView::SelectRows);
    table->setSelectionMode(QAbstractItemView::SingleSelection);
    table->setEditTriggers(QAbstractItemView::NoEditTriggers);
    table->setSortingEnabled(true);
    table->verticalHeader()->setVisible(false);
    table->horizontalHeader()->setStretchLastSection(false);
    table->horizontalHeader()->setSectionResizeMode(NameColumn, QHeaderView::ResizeToContents);
    table->horizontalHeader()->setSectionResizeMode(StateColumn, QHeaderView::ResizeToContents);
    table->horizontalHeader()->setSectionResizeMode(RemoteColumn, QHeaderView::ResizeToContents);
    table->horizontalHeader()->setSectionResizeMode(DefaultColumn, QHeaderView::ResizeToContents);
    table->horizontalHeader()->setSectionResizeMode(LocationColumn, QHeaderView::ResizeToContents);
    table->horizontalHeader()->setSectionResizeMode(DescriptionColumn, QHeaderView::ResizeToContents);
    table->horizontalHeader()->setSectionResizeMode(ModelColumn, QHeaderView::ResizeToContents);
    table->horizontalHeader()->setSectionResizeMode(UriColumn, QHeaderView::Stretch);
    table->horizontalHeader()->setSectionResizeMode(SourceColumn, QHeaderView::ResizeToContents);

    auto *mainLayout = new QVBoxLayout(this);
    mainLayout->addLayout(buttonLayout);
    mainLayout->addWidget(statusLabel);
    mainLayout->addWidget(table);

    connect(detectButton, &QPushButton::clicked, this, &PrinterFinderWidget::startDiscovery);
    connect(printButton, &QPushButton::clicked, this, &PrinterFinderWidget::printSelectedTestPage);
    connect(table, &QTableWidget::itemSelectionChanged, this, &PrinterFinderWidget::updatePrintButtonState);
}

void PrinterFinderWidget::startDiscovery()
{
    if (discoveryWatcher.isRunning()) {
        return;
    }

    detectButton->setEnabled(false);
    printButton->setEnabled(false);
    table->clearSelection();
    table->setRowCount(0);
    statusLabel->setText(QStringLiteral("Detecting printers..."));

    discoveryWatcher.setFuture(QtConcurrent::run(&PrinterFinderWidget::discoverPrinters));
}

void PrinterFinderWidget::finishDiscovery()
{
    currentRecords = discoveryWatcher.result();
    populateTable(currentRecords);

    detectButton->setEnabled(true);
    updatePrintButtonState();

    statusLabel->setText(QStringLiteral("Found %1 printer(s). Select a configured printer to print a test page.")
                             .arg(currentRecords.size()));
}

void PrinterFinderWidget::populateTable(const QVector<PrinterRecord> &records)
{
    table->setSortingEnabled(false);
    table->setRowCount(records.size());

    for (int row = 0; row < records.size(); ++row) {
        const PrinterRecord &record = records.at(row);
        const QStringList values = {
            record.name,
            record.state,
            record.isRemote ? QStringLiteral("Yes") : QStringLiteral("No"),
            record.isDefault ? QStringLiteral("Yes") : QStringLiteral("No"),
            record.location,
            record.description,
            record.makeAndModel,
            record.uri,
            record.source
        };

        for (int column = 0; column < values.size(); ++column) {
            auto *item = new QTableWidgetItem(values.at(column));
            item->setData(Qt::UserRole, row);
            table->setItem(row, column, item);
        }
    }

    table->setSortingEnabled(true);
    table->sortByColumn(NameColumn, Qt::AscendingOrder);
}

void PrinterFinderWidget::updatePrintButtonState()
{
    const PrinterRecord *record = selectedPrinter();
    printButton->setEnabled(record != nullptr && record->installed);
}

void PrinterFinderWidget::printSelectedTestPage()
{
    const PrinterRecord *record = selectedPrinter();
    if (record == nullptr) {
        return;
    }

    if (!record->installed) {
        QMessageBox::information(this,
                                 QStringLiteral("Printer is not installed"),
                                 QStringLiteral("The selected printer was discovered on the network, but it is not configured as a system print queue yet."));
        return;
    }

    const QPrinterInfo printerInfo = QPrinterInfo::printerInfo(record->name);
    if (printerInfo.isNull()) {
        QMessageBox::warning(this,
                             QStringLiteral("Printer unavailable"),
                             QStringLiteral("The selected printer is no longer configured on this system."));
        return;
    }

    QPrinter printer(printerInfo, QPrinter::HighResolution);
    printer.setDocName(QStringLiteral("Qt Printer Finder Test Page"));

    if (!printer.isValid()) {
        QMessageBox::warning(this,
                             QStringLiteral("Printer unavailable"),
                             QStringLiteral("The selected printer is no longer available to Qt."));
        return;
    }

    QPainter painter;
    if (!painter.begin(&printer)) {
        QMessageBox::warning(this,
                             QStringLiteral("Print failed"),
                             QStringLiteral("Could not start the print job for the selected printer."));
        return;
    }

    const QRect page = printer.pageLayout().paintRectPixels(printer.resolution());
    QFont titleFont = painter.font();
    titleFont.setPointSize(22);
    titleFont.setBold(true);
    painter.setFont(titleFont);
    painter.drawText(page.adjusted(0, 0, 0, -page.height() * 2 / 3),
                     Qt::AlignCenter,
                     QStringLiteral("Qt Printer Finder Test Page"));

    QFont bodyFont = painter.font();
    bodyFont.setPointSize(11);
    bodyFont.setBold(false);
    painter.setFont(bodyFont);

    const int left = page.left() + page.width() / 10;
    int top = page.top() + page.height() / 3;
    const int lineHeight = painter.fontMetrics().height() + 10;

    const QStringList lines = {
        QStringLiteral("Printer: %1").arg(record->name),
        QStringLiteral("Model: %1").arg(record->makeAndModel.isEmpty() ? QStringLiteral("Unknown") : record->makeAndModel),
        QStringLiteral("Location: %1").arg(record->location.isEmpty() ? QStringLiteral("Unknown") : record->location),
        QStringLiteral("Printed: %1").arg(QDateTime::currentDateTime().toString(Qt::ISODate)),
        QStringLiteral("If you can read this page, Qt submitted the print job successfully.")
    };

    for (const QString &line : lines) {
        painter.drawText(left, top, line);
        top += lineHeight;
    }

    painter.drawRect(page.adjusted(page.width() / 10, page.height() / 10,
                                   -page.width() / 10, -page.height() / 10));
    painter.end();

    QMessageBox::information(this,
                             QStringLiteral("Print job submitted"),
                             QStringLiteral("The test page was submitted to \"%1\".").arg(record->name));
}

const PrinterRecord *PrinterFinderWidget::selectedPrinter() const
{
    const QModelIndexList rows = table->selectionModel()->selectedRows();
    if (rows.isEmpty()) {
        return nullptr;
    }

    const int tableRow = rows.first().row();
    QTableWidgetItem *item = table->item(tableRow, NameColumn);
    if (item == nullptr) {
        return nullptr;
    }

    const int recordIndex = item->data(Qt::UserRole).toInt();
    if (recordIndex < 0 || recordIndex >= currentRecords.size()) {
        return nullptr;
    }

    return &currentRecords[recordIndex];
}

QVector<PrinterRecord> PrinterFinderWidget::discoverPrinters()
{
    QVector<PrinterRecord> records;

    for (const PrinterRecord &record : discoverQtPrinters()) {
        mergePrinter(records, record);
    }
    for (const PrinterRecord &record : discoverMdnsPrinters()) {
        mergePrinter(records, record);
    }
#ifdef Q_OS_UNIX
    for (const PrinterRecord &record : discoverCupsPrinters()) {
        mergePrinter(records, record);
    }
#endif

    std::sort(records.begin(), records.end(), [](const PrinterRecord &left, const PrinterRecord &right) {
        return QString::localeAwareCompare(left.name, right.name) < 0;
    });

    return records;
}

QVector<PrinterRecord> PrinterFinderWidget::discoverQtPrinters()
{
    QVector<PrinterRecord> records;
    const QStringList printerNames = QPrinterInfo::availablePrinterNames();

    for (const QString &printerName : printerNames) {
        const QPrinterInfo printer = QPrinterInfo::printerInfo(printerName);
        if (printer.isNull()) {
            continue;
        }

        PrinterRecord record;
        record.name = printer.printerName();
        record.description = printer.description();
        record.location = printer.location();
        record.makeAndModel = printer.makeAndModel();
        record.source = QStringLiteral("QPrinterInfo");
        record.state = printerStateToString(printer.state());
        record.isDefault = printer.isDefault();
        record.isRemote = printer.isRemote();
        record.installed = true;
        records.append(record);
    }

    return records;
}

QVector<PrinterRecord> PrinterFinderWidget::discoverMdnsPrinters()
{
    QVector<PrinterRecord> records;
    QUdpSocket socket;
    const QHostAddress mdnsAddress(QStringLiteral("224.0.0.251"));

    if (!socket.bind(QHostAddress::AnyIPv4, 5353,
                     QUdpSocket::ShareAddress | QUdpSocket::ReuseAddressHint)) {
        socket.bind(QHostAddress(QHostAddress::AnyIPv4), 0);
    }
    socket.joinMulticastGroup(mdnsAddress);

    const QByteArray ippQuery = mdnsPtrQuery(QStringLiteral("_ipp._tcp.local"));
    const QByteArray ippsQuery = mdnsPtrQuery(QStringLiteral("_ipps._tcp.local"));
    socket.writeDatagram(ippQuery, mdnsAddress, 5353);
    socket.writeDatagram(ippsQuery, mdnsAddress, 5353);

    std::map<QString, MdnsService> services;
    QElapsedTimer timer;
    timer.start();
    while (timer.elapsed() < 2500) {
        if (!socket.waitForReadyRead(250)) {
            continue;
        }

        while (socket.hasPendingDatagrams()) {
            QByteArray datagram;
            datagram.resize(int(socket.pendingDatagramSize()));
            socket.readDatagram(datagram.data(), datagram.size());
            parseMdnsPacket(datagram, services);
        }
    }

    for (const auto &entry : services) {
        const MdnsService &service = entry.second;
        if (service.instance.isEmpty()) {
            continue;
        }

        PrinterRecord record;
        record.name = instanceDisplayName(service.instance);
        record.location = service.location;
        record.makeAndModel = service.model;
        record.source = QStringLiteral("DNS-SD");
        record.state = QStringLiteral("Advertised");
        record.isRemote = true;
        record.installed = false;

        if (!service.host.isEmpty()) {
            QString path = service.path;
            if (!path.isEmpty() && !path.startsWith('/')) {
                path.prepend('/');
            }
            record.uri = QStringLiteral("%1://%2:%3%4")
                             .arg(service.protocol.isEmpty() ? QStringLiteral("ipp") : service.protocol,
                                  service.host)
                             .arg(service.port == 0 ? 631 : service.port)
                             .arg(path);
        }

        records.append(record);
    }

    return records;
}

#ifdef Q_OS_UNIX
QVector<PrinterRecord> PrinterFinderWidget::discoverCupsPrinters()
{
    QVector<PrinterRecord> records;
    const QString output = runCommand(QStringLiteral("lpstat"), {QStringLiteral("-v")});
    const QStringList lines = output.split('\n', Qt::SkipEmptyParts);
    const QRegularExpression expression(QStringLiteral("^device for (.+):\\s+(.+)$"));

    for (const QString &line : lines) {
        const QRegularExpressionMatch match = expression.match(line.trimmed());
        if (!match.hasMatch()) {
            continue;
        }

        PrinterRecord record;
        record.name = match.captured(1).trimmed();
        record.uri = match.captured(2).trimmed();
        record.source = QStringLiteral("CUPS");
        record.state = QStringLiteral("Configured");
        record.isRemote = record.uri.startsWith(QStringLiteral("ipp:"), Qt::CaseInsensitive)
            || record.uri.startsWith(QStringLiteral("ipps:"), Qt::CaseInsensitive)
            || record.uri.startsWith(QStringLiteral("socket:"), Qt::CaseInsensitive)
            || record.uri.startsWith(QStringLiteral("lpd:"), Qt::CaseInsensitive)
            || record.uri.startsWith(QStringLiteral("smb:"), Qt::CaseInsensitive)
            || record.uri.startsWith(QStringLiteral("dnssd:"), Qt::CaseInsensitive);
        record.installed = true;
        records.append(record);
    }

    return records;
}
#endif

QString PrinterFinderWidget::runCommand(const QString &program, const QStringList &arguments)
{
    QProcess process;
    process.start(program, arguments);
    if (!process.waitForStarted(1000)) {
        return QString();
    }
    if (!process.waitForFinished(5000)) {
        process.kill();
        process.waitForFinished();
        return QString();
    }

    return QString::fromLocal8Bit(process.readAllStandardOutput());
}

void PrinterFinderWidget::mergePrinter(QVector<PrinterRecord> &records, const PrinterRecord &candidate)
{
    if (candidate.name.isEmpty() && candidate.uri.isEmpty()) {
        return;
    }

    for (PrinterRecord &record : records) {
        const bool sameName = !candidate.name.isEmpty()
            && record.name.compare(candidate.name, Qt::CaseInsensitive) == 0;
        const bool sameUri = !candidate.uri.isEmpty()
            && record.uri.compare(candidate.uri, Qt::CaseInsensitive) == 0;

        if (!sameName && !sameUri) {
            continue;
        }

        if (record.name.isEmpty()) {
            record.name = candidate.name;
        }
        if (record.description.isEmpty()) {
            record.description = candidate.description;
        }
        if (record.location.isEmpty()) {
            record.location = candidate.location;
        }
        if (record.makeAndModel.isEmpty()) {
            record.makeAndModel = candidate.makeAndModel;
        }
        if (record.uri.isEmpty()) {
            record.uri = candidate.uri;
        }
        if (!record.source.contains(candidate.source)) {
            record.source += record.source.isEmpty() ? candidate.source : QStringLiteral(", ") + candidate.source;
        }
        if (record.state.isEmpty() || record.state == QStringLiteral("Advertised")) {
            record.state = candidate.state;
        }
        record.isDefault = record.isDefault || candidate.isDefault;
        record.isRemote = record.isRemote || candidate.isRemote;
        record.installed = record.installed || candidate.installed;
        return;
    }

    records.append(candidate);
}
