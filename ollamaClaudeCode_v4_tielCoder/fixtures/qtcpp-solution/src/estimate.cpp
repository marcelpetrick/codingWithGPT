#include "estimate.h"
#include <QStringList>

int parseEstimate(const QString &text)
{
    const QStringList parts = text.split(' ', Qt::SkipEmptyParts);
    if (parts.isEmpty())
        return -1;
    int total = 0;
    for (const QString &part : parts) {
        bool ok = false;
        const int value = part.left(part.size() - 1).toInt(&ok);
        if (!ok || value < 0)
            return -1;
        const QChar unit = part.back();
        if (unit == 'w') total += value * 5 * 8 * 60;
        else if (unit == 'd') total += value * 8 * 60;
        else if (unit == 'h') total += value * 60;
        else if (unit == 'm') total += value;
        else return -1;
    }
    return total;
}

QString formatEstimate(int minutes)
{
    if (minutes < 0)
        return {};
    if (minutes == 0)
        return "0m";
    QStringList out;
    const int w = minutes / 2400; minutes %= 2400;
    const int d = minutes / 480; minutes %= 480;
    const int h = minutes / 60; minutes %= 60;
    if (w) out << QString::number(w) + "w";
    if (d) out << QString::number(d) + "d";
    if (h) out << QString::number(h) + "h";
    if (minutes) out << QString::number(minutes) + "m";
    return out.join(' ');
}
