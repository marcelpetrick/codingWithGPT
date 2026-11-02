#include <QSignalSpy>
#include <QTest>
#include "backlogsummary.h"
#include "estimate.h"
#include "issuemodel.h"

class TstBacklog : public QObject
{
    Q_OBJECT
private slots:
    void parsesHoursAndMinutes() { QCOMPARE(parseEstimate("2h 30m"), 150); }
    void dayIsEightHours() { QCOMPARE(parseEstimate("1d"), 480); }
    void formatsLargestFirst() { QCOMPARE(formatEstimate(630), QString("1d 2h 30m")); }
    void addSignalsInsert()
    {
        IssueModel model;
        QSignalSpy inserted(&model, &QAbstractItemModel::rowsInserted);
        QVERIFY(model.addIssue({1, "a", 10, false}));
        QCOMPARE(inserted.count(), 1);
        QCOMPARE(model.rowCount(), 1);
    }
    void removeOneRow()
    {
        IssueModel model;
        model.addIssue({1, "a", 10, false});
        model.addIssue({2, "b", 20, false});
        QSignalSpy removed(&model, &QAbstractItemModel::rowsRemoved);
        QVERIFY(model.removeIssue(2));
        QCOMPARE(removed.at(0).at(2).toInt(), 1);
    }
    void summaryCountsOpen()
    {
        IssueModel model;
        model.addIssue({1, "a", 10, false});
        model.addIssue({2, "b", 20, true});
        BacklogSummary summary(&model);
        QCOMPARE(summary.openMinutes(), 10);
    }
};

QTEST_GUILESS_MAIN(TstBacklog)
#include "tst_backlog.moc"
