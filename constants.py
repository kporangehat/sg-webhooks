# Template for Reply when a code review is assigned.
# Requires: assignee name, pull request url, pull request title, pull request description
CR_ASSIGNED_REPLY_TEMPLATE = \
"""
--------------------------------------------------------------------------------
Code Review Assigned to: %s
Pull Request: %s
--------------------------------------------------------------------------------

h4.
%s

%s
"""

# Template for Reply when a code review is edited.
# Requires: assignee name, pull request url, changed fields str
CR_EDITED_REPLY_TEMPLATE = \
"""
--------------------------------------------------------------------------------
Code Review Assigned to: %s
Pull Request: %s
--------------------------------------------------------------------------------

The pull request was updated  Please follow the link to see the changes to the %s.
"""
