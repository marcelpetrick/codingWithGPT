#include "backlogsummary.h"

BacklogSummary::BacklogSummary(IssueModel *, QObject *parent) : QObject(parent) {}

int BacklogSummary::openMinutes() const
{
    return -1;
}
