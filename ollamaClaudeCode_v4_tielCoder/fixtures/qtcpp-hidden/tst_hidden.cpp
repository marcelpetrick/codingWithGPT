#include <QAbstractItemModelTester>
#include <QSignalSpy>
#include <QTest>
#include "backlogsummary.h"
#include "estimate.h"
#include "issuemodel.h"

using Tester = QAbstractItemModelTester;

class TstHidden : public QObject
{
    Q_OBJECT
private slots:
    void weekIsFiveDays() { QCOMPARE(parseEstimate("1w"), 2400); }
    void anyOrderAndOuterSpaces() { QCOMPARE(parseEstimate("  30m 1h "), 90); }
    void parseRejectsBadInput()
    {
        QCOMPARE(parseEstimate(""), -1);
        QCOMPARE(parseEstimate("   "), -1);
        QCOMPARE(parseEstimate("3x"), -1);
        QCOMPARE(parseEstimate("h"), -1);
        QCOMPARE(parseEstimate("-2h"), -1);
    }
    void formatEdges()
    {
        QCOMPARE(formatEstimate(0), QString("0m"));
        QCOMPARE(formatEstimate(2400), QString("1w"));
        QCOMPARE(formatEstimate(-1), QString());
        QCOMPARE(formatEstimate(60), QString("1h"));
    }
    void validParentHasNoRows()
    {
        IssueModel m;
        m.addIssue({1, "a", 1, false});
        QCOMPARE(m.rowCount(m.index(0)), 0);
    }
    void invalidIndexGivesNull()
    {
        IssueModel m;
        QVERIFY(!m.data(QModelIndex()).isValid());
        QVERIFY(!m.data(m.index(3)).isValid());
    }
    void duplicateIdRefused()
    {
        IssueModel m;
        QVERIFY(m.addIssue({1, "a", 1, false}));
        QSignalSpy about(&m, &QAbstractItemModel::rowsAboutToBeInserted);
        QVERIFY(!m.addIssue({1, "b", 1, false}));
        QCOMPARE(m.rowCount(), 1);
        QCOMPARE(about.count(), 0);
    }
    void addDoesNotReset()
    {
        IssueModel m;
        QSignalSpy reset(&m, &QAbstractItemModel::modelReset);
        m.addIssue({1, "a", 1, false});
        QCOMPARE(reset.count(), 0);
    }
    void setDataNamesTheRole()
    {
        IssueModel m;
        m.addIssue({1, "a", 1, false});
        QSignalSpy spy(&m, &QAbstractItemModel::dataChanged);
        QVERIFY(m.setData(m.index(0), 5, IssueModel::EstimateRole));
        QCOMPARE(spy.count(), 1);
        QCOMPARE(spy.at(0).at(2).value<QList<int>>(), QList<int>{IssueModel::EstimateRole});
    }
    void setDataRefusals()
    {
        IssueModel m;
        m.addIssue({1, "a", 7, false});
        QSignalSpy spy(&m, &QAbstractItemModel::dataChanged);
        QVERIFY(!m.setData(m.index(0), -1, IssueModel::EstimateRole));
        QVERIFY(!m.setData(m.index(0), 7, IssueModel::EstimateRole));
        QVERIFY(!m.setData(m.index(0), "x", Qt::DisplayRole));
        QVERIFY(!m.setData(m.index(9), 3, IssueModel::EstimateRole));
        QCOMPARE(spy.count(), 0);
        QCOMPARE(m.data(m.index(0), IssueModel::EstimateRole).toInt(), 7);
    }
    void modelContract()
    {
        IssueModel m;
        Tester tester(&m, Tester::FailureReportingMode::QtTest);
        m.addIssue({1, "a", 1, false});
        m.addIssue({2, "b", 2, false});
        m.setData(m.index(1), true, IssueModel::ClosedRole);
        m.removeIssue(1);
        QCOMPARE(m.rowCount(), 1);
    }
    void summaryFollowsChangesOnce()
    {
        IssueModel m;
        m.addIssue({1, "a", 10, false});
        BacklogSummary s(&m);
        QSignalSpy spy(&s, &BacklogSummary::totalChanged);
        m.addIssue({2, "b", 20, false});
        QCOMPARE(s.openMinutes(), 30);
        m.setData(m.index(0), 15, IssueModel::EstimateRole);
        QCOMPARE(s.openMinutes(), 35);
        m.setData(m.index(1), true, IssueModel::ClosedRole);
        QCOMPARE(s.openMinutes(), 15);
        m.removeIssue(1);
        QCOMPARE(s.openMinutes(), 0);
        QCOMPARE(spy.count(), 4);
        QCOMPARE(spy.last().at(0).toInt(), 0);
    }
    void summaryQuietWithoutValueChange()
    {
        IssueModel m;
        m.addIssue({1, "a", 10, true});
        BacklogSummary s(&m);
        QSignalSpy spy(&s, &BacklogSummary::totalChanged);
        m.setData(m.index(0), 25, IssueModel::EstimateRole);
        m.addIssue({2, "b", 0, false});
        QCOMPARE(spy.count(), 0);
    }
    void summarySurvivesModelDestruction()
    {
        auto *m = new IssueModel;
        m->addIssue({1, "a", 10, false});
        BacklogSummary s(m);
        QCOMPARE(s.openMinutes(), 10);
        delete m;
        QCOMPARE(s.openMinutes(), 0);
    }
};

QTEST_GUILESS_MAIN(TstHidden)
#include "tst_hidden.moc"
