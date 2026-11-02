#include "issuemodel.h"

int IssueModel::rowCount(const QModelIndex &) const
{
    return m_issues.size();
}

QVariant IssueModel::data(const QModelIndex &index, int role) const
{
    const Issue &issue = m_issues.at(index.row());
    switch (role) {
    case Qt::DisplayRole: return issue.title;
    case IdRole: return issue.id;
    case EstimateRole: return issue.estimateMinutes;
    case ClosedRole: return issue.closed;
    }
    return {};
}

bool IssueModel::setData(const QModelIndex &index, const QVariant &value, int role)
{
    if (!index.isValid())
        return false;
    Issue &issue = m_issues[index.row()];
    if (role == EstimateRole)
        issue.estimateMinutes = value.toInt();
    else if (role == ClosedRole)
        issue.closed = value.toBool();
    else
        return false;
    emit dataChanged(index, index);
    return true;
}

QHash<int, QByteArray> IssueModel::roleNames() const
{
    return {{Qt::DisplayRole, "title"}, {IdRole, "issueId"},
            {EstimateRole, "estimate"}, {ClosedRole, "closed"}};
}

bool IssueModel::addIssue(const Issue &issue)
{
    beginResetModel();
    m_issues.append(issue);
    endResetModel();
    return true;
}

bool IssueModel::removeIssue(int id)
{
    for (int row = 0; row < m_issues.size(); ++row) {
        if (m_issues.at(row).id == id) {
            beginRemoveRows(QModelIndex(), row, row + 1);
            m_issues.removeAt(row);
            endRemoveRows();
            return true;
        }
    }
    return false;
}
