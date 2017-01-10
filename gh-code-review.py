"""
Web hook that handles POST requests form Github Code Review triggers.

PR Assigned
    - extract ticket #, assignee, title, and description
    - SG internal ticket update:
        - CR assignee
        - PR comment
        - Status to "code"
PR unassigned
    - extract ticket #, assignee, title, and description
    - SG internal ticket update:
        - CR assignee <blank>
        - comment CR has been unassigned
        - Status to ???
PR edited
    - extract ticket #, assignee, title, and description
    - SG internal ticket update:
        - comment PR comment has changed with new comment

"""
from flask import Flask, request, render_template
import os
import re

import shotgun_api3
from constants import CR_ASSIGNED_REPLY_TEMPLATE
from constants import CR_EDITED_REPLY_TEMPLATE

app = Flask(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    VALID_ACTIONS=["assigned", "unassigned", "edited"],
    SG_INTERNAL_SCRIPT_NAME=os.environ.get("SG_INTERNAL_SCRIPT_NAME"),
    SG_INTERNAL_API_KEY=os.environ.get("SG_INTERNAL_API_KEY"),
    DEBUG=True,
))
app.config.from_envvar("SOME_OTHER_CONFIG_FILE", silent=True)

# Setup Shotgun internal API handle
sg = shotgun_api3.Shotgun("http://internal.shotgunstudio.int",
        app.config["SG_INTERNAL_SCRIPT_NAME"], app.config["SG_INTERNAL_API_KEY"]
     )


@app.route("/github_cr_assignment", methods=["POST"])
def github_cr_assignment():
    app.logger.debug("Got data: %s" % request.get_data())
    data = request.get_json()

    # Check which action was performed on the pull request.
    action = data.get("action")
    app.logger.debug("Action: %s" % action)

    # If we don"t care about this action then we"re done.
    if action not in app.config["VALID_ACTIONS"]:
        app.logger.info("Action not valid, skipping")
        return '', 204

    pr = data["pull_request"]
    if not pr:
        app.logger.info("No PR data received.")
        return '', 204

    # Ticket #
    ticket_num = parse_ticket_from_title_str(pr["title"])
    if not ticket_num:
        app.logger.info("No Ticket # could be parsed from the PR title: %s" % pr["title"])
        return '', 204

    if action == "assigned":
        # Assignee
        sg_user = None
        if pr["assignee"]:
            assignee_login = pr["assignee"]["login"]
            sg_user = get_sg_user_from_gh_login(assignee_login)
            if not sg_user:
                app.logger.info("Could not find a SG user with Github login: %s" % assignee_login)
                return '', 204
        sg_assign_code_review(ticket_num, sg_user, pr["title"], pr["body"], pr["html_url"])
    elif action == "unassigned":
        # Assignee
        sg_user = None
        if data["assignee"]:
            assignee_login = data["assignee"]["login"]
            sg_user = get_sg_user_from_gh_login(assignee_login)
            if not sg_user:
                app.logger.info("Could not find a SG user with Github login: %s" % assignee_login)
                return '', 204
        sg_unassign_code_review(ticket_num, sg_user)
    elif action == "edited":
        # Assignee
        sg_user = None
        if pr["assignee"]:
            assignee_login = pr["assignee"]["login"]
            sg_user = get_sg_user_from_gh_login(assignee_login)
            if not sg_user:
                app.logger.info("Could not find a SG user with Github login: %s" % assignee_login)
                return '', 204
        sg_pull_request_updated(ticket_num, sg_user, pr_url, changed)

    return '', 204


def parse_ticket_from_str(title_str):
    """
    Get SG Internal ticket number out of the pull request title.

    :param str title_str: Title of the pull request
    :return: Ticket number on SG Internal as int.
    """
    result = re.match(".*#(\d+).*", title_str)
    if not result:
        return

    return int(result.group(1))


def get_sg_user_from_gh_login(github_login):
    """
    Lookup SG HumanUser entity with the specified Github login.

    :param str github_login: Github login to look up on Shotgun internal.
    :return: SG HumanUser as a standard entity dictionary or None.
    """
    if github_login:
        return sg.find_one("HumanUser", [["sg_github_login", "is", github_login]], ["name"])


def sg_assign_code_review(ticket_num, sg_user, pr_title, pr_body, pr_url):
    """
    Update SG ticket with the assigned code reviewer and set status to Pending Code Review. Add a
    Reply to the Ticket with the details.

    :param int ticket_num: SG internal ticket number.
    :param dict sg_user: SG user entity dictionary (with 'name' key as well).
    :param str pr_title: Title of the pull request.
    :param str pr_body: Body of the pull request.
    :param str pr_url: HTML url on Github for the pull request.
    :return:
    """
    # Update the SG Ticket fields assigning the code reviewer and setting status to Pending CR
    payload = {
        "sg_status_list": "code",
        "sg_code_review": [sg_user],
    }
    result = sg.update(
                "Ticket", ticket_num, payload, multi_entity_update_modes={"sg_code_review": "add"}
             )
    app.logger.debug("Updated SG Ticket %d: %s" % (ticket_num, result))

    # Add comment with the PR comment
    payload = {
        "entity": {"type": "Ticket", "id": ticket_num},
        "content": CR_ASSIGNED_REPLY_TEMPLATE % (sg_user["name"], pr_url, pr_title, pr_body)
    }
    result = sg.create("Reply", payload)
    app.logger.debug("Added Reply to SG Ticket %d: %s" % (ticket_num, result))


def sg_unassign_code_review(ticket_num, sg_user):
    """
    Update SG Ticket and remove code review assignment.
    :param ticket_num:
    :param sg_user:
    :return:
    """
    payload = {
        "sg_code_review": [sg_user]
    }
    result = sg.update(
                "Ticket", ticket_num, payload,
                    multi_entity_update_modes={"sg_code_review": "remove"}
             )
    app.logger.debug("Updated SG Ticket %d: %s" % (ticket_num, result))


def sg_notify_pull_request_updated(ticket_num, sg_user, pr_url, changed):
    """

    :param ticket_num:
    :param sg_user:
    :param pr_url:
    :param changed:
    :return:
    """
    # Add comment with the PR comment
    payload = {
        "entity": {"type": "Ticket", "id": ticket_num},
        "content": CR_EDITED_REPLY_TEMPLATE % (sg_user["name"], pr_url, " and ".join(changed))
    }
    result = sg.create("Reply", payload)
    app.logger.debug("Added Reply to SG Ticket %d: %s" % (ticket_num, result))

