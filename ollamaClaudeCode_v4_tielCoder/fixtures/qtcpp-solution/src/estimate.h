#pragma once
#include <QString>

// Parses a GitLab-style time estimate and returns minutes.
// Accepted units: w (5 days), d (8 hours), h, m. Parts are separated by spaces
// and appear in any order, for example "1d 2h 30m" or "30m 1h".
// Surrounding spaces are ignored. Returns -1 for an empty string, an unknown
// unit, a missing number, or a negative number.
int parseEstimate(const QString &text);

// Formats minutes in the largest units first, without empty parts:
// 630 -> "1d 2h 30m", 2400 -> "1w", 0 -> "0m". Negative input returns "".
QString formatEstimate(int minutes);
