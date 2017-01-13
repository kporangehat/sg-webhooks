"""
Flask app that handles web hook requests from 3rd-party sites.

Github post-commit
    When commits are pushed to Github, create a Revision entity in Shotgun for each commit
    with information about the repo, branch, author, component, commit id and commit message.
Github PR Assigned
    When pull request is assigned, find the corresponding ticket in Shotgun and assign the
    code review to the assignee, set the status to "Code Review" and add a Reply with the
    pull request description.
Github PR unassigned
    When pull request is unassigned, find the corresponding ticket in Shotgun and un-assign
    the code review from the assignee.
Github PR edited
    When a pull request title or description is edited, if there is a current assignee, add a
    Reply to the Shotgun ticket with the updated pull request title and description.
"""
from flask import Flask
from flask import request
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
    ticket_num = sg_handler.parse_ticket_from_str(pr_title)
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


@app.route("/github_commit_hook", methods=["POST"])
def github_commit_hook():
    """
    Handle post-commit webhook from Github, parse information and create Revision entities in
    Shotgun

    :returns: Empty response context with status code 204 - No Content.
    """
    data = request.get_json()

    # Get repo name
    repo = data["repository"]["name"]
    app.logger.debug("repo: %s", repo)

    # Get SG Project dict
    project = sg_handler.get_project_from_repo(repo)
    app.logger.info("project: %s", project)

    # Get commit list
    commits = data.get("commits", [])

    # Parse out the branch/tag name.
    branch_info = {}
    match = re.match("^refs/(?P<type>\w+)/(?P<name>.*)$", data.get("ref", ""))
    if match:
        branch_info = match.groupdict()

    if branch_info.get("type") == "heads":
        # Commits on master or other branch
        branch = branch_info.get("name")
        app.logger.info("branch: %s", branch)
        for i, commit in enumerate(commits):
            app.logger.info("commit %d: %s", i, commit)
            try:
                sg_handler.create_revision(
                    project,
                    repo,
                    branch,
                    commit.get("id"),
                    commit.get("url"),
                    commit.get("author", {}),
                    commit.get("message", "")
                )
            except Exception, e:
                app.logger.exception(
                        "commit %s: Create Revision Failed: %s" % (commit.get("id"), e)
                )
                raise

    elif branch_info.get("type") == "tags":
        # Commits of tags
        tag_name = branch_info.get("name")
        app.logger.info("tag: %s", tag_name)
        app.logger.info("tag data: %s", data)
        try:
            sg_handler.create_revision(
                project,
                repo,
                tag_name,
                data.get("after"),
                data.get("compare"),
                data.get("pusher", {}),
                "Tag \"%s\" created" % tag_name
            )
        except Exception, e:
            app.logger.exception("tag %s: Create Revision Failed: %s" % (data.get("after"), e))
            raise
    else:
        app.logger.warning("Unhandled branch type: %s" % data.get("ref"))

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


if __name__ == "__main__":
    app.run("0.0.0.0")
