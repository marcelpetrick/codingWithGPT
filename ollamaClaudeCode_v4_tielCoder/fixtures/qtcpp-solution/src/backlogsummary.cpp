#include "backlogsummary.h"
#include "issuemodel.h"

BacklogSummary::BacklogSummary(IssueModel *model, QObject *parent) : QObject(parent), m_model(model)
{
    connect(model, &QAbstractItemModel::rowsInserted, this, &BacklogSummary::recompute);
    connect(model, &QAbstractItemModel::rowsRemoved, this, &BacklogSummary::recompute);
    connect(model, &QAbstractItemModel::modelReset, this, &BacklogSummary::recompute);
    connect(model, &QAbstractItemModel::dataChanged, this, &BacklogSummary::recompute);
    connect(model, &QObject::destroyed, this, [this] { m_model = nullptr; if (m_total) { m_total = 0; emit totalChanged(0); } });
    int total = 0;
    for (int r = 0; r < model->rowCount(); ++r)
        if (!model->data(model->index(r), IssueModel::ClosedRole).toBool())
            total += model->data(model->index(r), IssueModel::EstimateRole).toInt();
    m_total = total;
}

int BacklogSummary::openMinutes() const
{
    return m_model ? m_total : 0;
}

void BacklogSummary::recompute()
{
    int total = 0;
    for (int r = 0; r < m_model->rowCount(); ++r)
        if (!m_model->data(m_model->index(r), IssueModel::ClosedRole).toBool())
            total += m_model->data(m_model->index(r), IssueModel::EstimateRole).toInt();
    if (total != m_total) {
        m_total = total;
        emit totalChanged(total);
    }
}
