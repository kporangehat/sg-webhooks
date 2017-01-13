import os

# App settings
APP_SETTINGS = dict(
    VALID_CR_ASSIGNMENT_ACTIONS=["assigned", "unassigned", "edited"],
    COMPONENT_ENTITY_TYPE="CustomEntity07",
    SG_PROJECT_ENTITY = {"type": "Project", "id": 2},
    TK_PROJECT_ENTITY = {"type": "Project", "id": 12},
    SG_INTERNAL_SCRIPT_NAME=os.environ.get("SG_INTERNAL_SCRIPT_NAME"),
    SG_INTERNAL_API_KEY=os.environ.get("SG_INTERNAL_API_KEY"),
    DEBUG=True,
)

# This is the default status response we return for the web hooks since they are one-way.
# content, status code
HTTP_RESPONSE_NO_CONTENT = "", 204

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

The *%s* was updated on the pull request below: %s

h4.
%s

%s
"""
