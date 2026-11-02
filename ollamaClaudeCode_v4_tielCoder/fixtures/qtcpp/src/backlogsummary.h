#pragma once
#include <QObject>

class IssueModel;

// Keeps the sum of the estimates of the OPEN issues of a model. The sum follows
// each insert, remove, reset and data change of the model. totalChanged is emitted
// once for each change of the value, and never when the value stays the same.
// The summary does not own the model. After the model is destroyed, openMinutes() returns 0.
class BacklogSummary : public QObject
{
    Q_OBJECT
    Q_PROPERTY(int openMinutes READ openMinutes NOTIFY totalChanged)
public:
    explicit BacklogSummary(IssueModel *model, QObject *parent = nullptr);
    int openMinutes() const;

signals:
    void totalChanged(int minutes);

private:
    // Not implemented yet.
};
