#include <QCoreApplication>
#include <QFile>
#include <QTextStream>
#include <QDebug>

class ValidationTest {
public:
    static bool binary_filesAreIdentical(const QString& filePath1, const QString& filePath2, int chopLastBytes) {
        QFile file1(filePath1);
        QFile file2(filePath2);

        if (!file1.open(QIODevice::ReadOnly) || !file2.open(QIODevice::ReadOnly)) {
            qDebug() << "Failed to open one or both files for reading.";
            return false;
        }

        QByteArray content1 = file1.readAll();
        QByteArray content2 = file2.readAll();

        if (chopLastBytes > 0) {
            if (content1.size() > chopLastBytes)
                content1.chop(chopLastBytes);
            if (content2.size() > chopLastBytes)
                content2.chop(chopLastBytes);
        }

        file1.close();
        file2.close();

        if (content1 == content2) {
            qDebug() << "The files are identical.";
            return true;
        } else {
            qDebug() << "The files are different.";
            return false;
        }
    }


    static bool textbased_filesAreIdentical(const QString& filePath1, const QString& filePath2, const int chopLastBytes) {
        qDebug() << "Comparing files.";
        qDebug() << filePath1;
        qDebug() << filePath2;
        QFile file1(filePath1);
        QFile file2(filePath2);

        if (!file1.open(QIODevice::ReadOnly | QIODevice::Text) || !file2.open(QIODevice::ReadOnly | QIODevice::Text)) {
            qDebug() << "Failed to open one or both files for reading.";
            return false;
        }

        QTextStream in1(&file1);
        QTextStream in2(&file2);

        QString content1 = in1.readAll();
        QString content2 = in2.readAll();

        if (!content1.isEmpty() && content1.endsWith('\n')) {
            content1.chop(1);
        }
        if (!content2.isEmpty() && content2.endsWith('\n')) {
            content2.chop(1);
        }

        content1.chop(chopLastBytes);
        content2.chop(chopLastBytes);

        file1.close();
        file2.close();

        if (content1 == content2) {
            qDebug() << "The files are identical.";
            return true;
        } else {
            qDebug() << "The files are different.";
            return false;
        }
    }
};

int main(int argc, char *argv[])
{
    QCoreApplication a(argc, argv);

    QString file1 = "12074798_000.hex";
    QString file2 = "2025-05-26_16-38-38_ili2315_afterExport.hex";
    int chopLastBytes = 1; // set this to whatever you need

    bool const result_text = ValidationTest::textbased_filesAreIdentical(file1, file2, chopLastBytes);
    qDebug() << "identical: " << result_text;

    bool const result_binary = ValidationTest::binary_filesAreIdentical(file1, file2, chopLastBytes);
    qDebug() << "identical: " << result_binary;

    // If you want to return 0 or 1 depending on result:
    return result_binary ? 0 : 1;
}
