"""
Flask app that handles web hook POST requests form Github.

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
from flask import Flask, request
import re

import sg_handler
from constants import APP_SETTINGS
from constants import HTTP_RESPONSE_NO_CONTENT

app = Flask(__name__)

# Load default config and override config from an environment variable
app.config.update(APP_SETTINGS)
app.config.from_envvar("SOME_OTHER_CONFIG_FILE", silent=True)


@app.route("/github_cr_assignment", methods=["POST"])
def github_cr_assignment():
    """
    Handle web hook from Github when a code review is assigned, unassigned or edited.

    This is currently keying off the PullRequestEvent web hook which is sent for other
    actions as well which we discard. There is currently no web hook for Review Requested so
    we rely on the Assigned field to trigger this for now.

    :returns: Empty response context with status code 204 - No Content.
    """
    app.logger.debug("Got data: %s" % request.get_data())
    data = request.get_json()

    # Check which action was performed on the pull request.
    action = data.get("action")
    app.logger.debug("Action: %s" % action)

    # If we don"t care about this action then we"re done.
    if action not in app.config["VALID_CR_ASSIGNMENT_ACTIONS"]:
        app.logger.debug("Action not valid, skipping")
        return HTTP_RESPONSE_NO_CONTENT

    # Get Ticket #
    pr_title = data["pull_request"]["title"]
    ticket_num = parse_ticket_from_str(pr_title)
    if not ticket_num:
        app.logger.info("No Ticket # could be parsed from the PR title: %s" % pr_title)
        return HTTP_RESPONSE_NO_CONTENT

    if action == "assigned":
        github_cr_assigned(ticket_num, data)

    elif action == "unassigned":
        github_cr_unassigned(ticket_num, data)

    elif action == "edited":
        github_pr_edited(ticket_num, data)

    return HTTP_RESPONSE_NO_CONTENT


def github_cr_assigned(ticket_num, data):
    """

    :param ticket_num:
    :param data:
    :return:
    """
    pr = data["pull_request"]
    assignee_login = pr["assignee"]["login"]
    sg_user = sg_handler.get_user_from_gh_login(assignee_login)
    if not sg_user:
        app.logger.info("Could not find a SG user with Github login: %s" % assignee_login)
        return

    sg_handler.assign_code_review(ticket_num, sg_user, pr["title"], pr["body"], pr["html_url"])


def github_cr_unassigned(ticket_num, data):
    """

    :param ticket_num:
    :param data:
    :return:
    """
    assignee_login = data["assignee"]["login"]
    sg_user = sg_handler.get_user_from_gh_login(assignee_login)
    if not sg_user:
        app.logger.info("Could not find a SG user with Github login: %s" % assignee_login)
        return

    sg_handler.unassign_code_review(ticket_num, sg_user)


def github_pr_edited(ticket_num, data):
    """

    :param ticket_num:
    :param data:
    :return:
    """
    pr = data["pull_request"]
    if not pr["assignee"]:
        return

    assignee_login = pr["assignee"]["login"]
    sg_user = sg_handler.get_user_from_gh_login(assignee_login)
    if not sg_user:
        app.logger.info("Could not find a SG user with Github login: %s" % assignee_login)
        return

    fields_changed = data["changes"].keys()
    sg_handler.notify_pull_request_updated(
            ticket_num, sg_user, pr["html_url"], fields_changed, pr["title"], pr["body"]
    )


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
