#include "estimate.h"
#include <QStringList>

int parseEstimate(const QString &text)
{
    int total = 0;
    const QStringList parts = text.split(' ');
    for (const QString &part : parts) {
        const int value = part.left(part.size() - 1).toInt();
        const QChar unit = part.back();
        if (unit == 'd')
            total += value * 24 * 60;
        else if (unit == 'h')
            total += value * 60;
        else if (unit == 'm')
            total += value;
    }
    return total;
}

QString formatEstimate(int minutes)
{
    QStringList out;
    const int hours = minutes / 60;
    if (hours)
        out << QString::number(hours) + "h";
    out << QString::number(minutes % 60) + "m";
    return out.join(' ');
}
