#pragma once
#include <QAbstractListModel>
#include <QString>
#include <QVector>

struct Issue {
    int id = 0;
    QString title;
    int estimateMinutes = 0;
    bool closed = false;
};

// A flat list model of issues. It follows the QAbstractItemModel contract:
// each change uses the matching begin/end calls or emits dataChanged, so an
// attached view or proxy stays correct. A valid parent has no rows.
class IssueModel : public QAbstractListModel
{
    Q_OBJECT
public:
    enum Role { IdRole = Qt::UserRole + 1, EstimateRole, ClosedRole };
    using QAbstractListModel::QAbstractListModel;

    int rowCount(const QModelIndex &parent = QModelIndex()) const override;
    // Qt::DisplayRole gives the title. An invalid index or role gives QVariant().
    QVariant data(const QModelIndex &index, int role = Qt::DisplayRole) const override;
    // EstimateRole and ClosedRole are editable. Returns false and emits nothing
    // for an invalid index, another role, a negative estimate, or an unchanged value.
    // On a change, dataChanged names exactly the changed role.
    bool setData(const QModelIndex &index, const QVariant &value, int role = Qt::EditRole) override;
    QHash<int, QByteArray> roleNames() const override;

    // Appends the issue. Returns false, and changes nothing, if the id already exists.
    bool addIssue(const Issue &issue);
    // Removes the issue with this id. Returns false if there is none.
    bool removeIssue(int id);

private:
    QVector<Issue> m_issues;
};
