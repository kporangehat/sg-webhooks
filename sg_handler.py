from flask import current_app
import re

import shotgun_api3
from constants import APP_SETTINGS
from constants import CR_ASSIGNED_REPLY_TEMPLATE
from constants import CR_EDITED_REPLY_TEMPLATE


class ShotgunHandler(object):
    """
    Small class to store the Shotgun API handle.
    """
    _sg = None

    @classmethod
    def get_conn(cls):
        """
        :return: Shotgun API handle
        """
        if not ShotgunHandler._sg:
            ShotgunHandler._sg = shotgun_api3.Shotgun(
                "http://internal.shotgunstudio.int",
                APP_SETTINGS["SG_INTERNAL_SCRIPT_NAME"],
                APP_SETTINGS["SG_INTERNAL_API_KEY"]
            )

        return ShotgunHandler._sg


def assign_code_review(ticket_num, sg_user, pr_title, pr_body, pr_url):
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
    sg = ShotgunHandler.get_conn()
    payload = {
        "sg_status_list": "code",
        "sg_code_review": [sg_user],
    }
    result = sg.update(
        "Ticket", ticket_num, payload, multi_entity_update_modes={"sg_code_review": "add"}
    )
    current_app.logger.debug("Updated SG Ticket %d: %s" % (ticket_num, result))

    # Add comment with the PR comment
    reply_text = CR_ASSIGNED_REPLY_TEMPLATE % (sg_user["name"], pr_url, pr_title, pr_body)
    add_ticket_reply(ticket_num, reply_text)


def unassign_code_review(ticket_num, sg_user):
    """
    Update SG Ticket and remove code review assignment.
    :param ticket_num:
    :param sg_user:
    :return:
    """
    sg = ShotgunHandler.get_conn()
    payload = {
        "sg_code_review": [sg_user]
    }
    result = sg.update(
        "Ticket", ticket_num, payload, multi_entity_update_modes={"sg_code_review": "remove"}
    )
    current_app.logger.debug("Updated SG Ticket %d: %s" % (ticket_num, result))


def notify_pull_request_updated(ticket_num, sg_user, pr_url, changed, pr_title, pr_body):
    """

    :param ticket_num:
    :param sg_user:
    :param pr_url:
    :param changed:
    :param pr_title:
    :param pr_body:
    :return:
    """
    # Add comment with the PR comment
    reply_text = CR_EDITED_REPLY_TEMPLATE % (
        sg_user["name"], pr_url, " and ".join(changed), pr_title, pr_body
    )
    add_ticket_reply(ticket_num, reply_text)


def add_ticket_reply(ticket_num, reply_content):
    """

    :param ticket_num:
    :param reply_content:
    :return:
    """
    sg = ShotgunHandler.get_conn()
    payload = {
        "entity": {"type": "Ticket", "id": ticket_num},
        "content": reply_content
    }
    result = sg.create("Reply", payload)
    current_app.logger.debug("Added Reply to SG Ticket %d: %s" % (ticket_num, result))


def get_component(name, project):
    """
    Find Component given a name and project

    :param str name: Component name
    :param dict project: Shotgun project entity dict.
    :returns dict: Shotgun component entity dict or None.
    """
    sg = ShotgunHandler.get_conn()
    return sg.find_one(APP_SETTINGS["COMPONENT_ENTITY_TYPE"],
        [
            ["code", "is", name],
            ["project", "is", project]
        ]
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


def get_project_from_repo(repo_name):
    """
    Find Project based on repo name

    :param str repo_name: Github repo name.
    :returns dict: Shotgun Project entity dict.
    """
    if repo_name.startswith("tk-"):
        return APP_SETTINGS["TK_PROJECT_ENTITY"]
    return APP_SETTINGS["SG_PROJECT_ENTITY"]


def get_user_by_email(author):
    """
    Find author based on email address

    Tries to match the author account email with an Email address on Shotgun, falls
    back to searching on the Github Email field.

    :param dict author: author dict from github commit dict.
    :returns dict: Shotgun HumanUser entity dict or None.
    """
    sg = ShotgunHandler.get_conn()
    user = sg.find_one("HumanUser", [["email", "is", author.get("email")]])
    if not user:
        user = sg.find_one("HumanUser", [["sg_github_email", "is", author.get("email")]])

    return user


def get_user_from_gh_login(github_login):
    """
    Lookup SG HumanUser entity with the specified Github login.

    :param str github_login: Github login to look up on Shotgun internal.
    :return: SG HumanUser as a standard entity dictionary or None.
    """
    if github_login:
        sg = ShotgunHandler.get_conn()
        return sg.find_one("HumanUser", [["sg_github_login", "is", github_login]], ["name"])


def create_revision(project, repo, branch, revision, url, author, message):
    """
    Create a shotgun Revision

    :param dict project: Shotgun Project entity dict.
    :param str repo: repo name
    :param str branch: branch name
    :param str revision: revision name
    :param str url: commit url on Github
    :param dict author: github author dict from commit dict
    :param str message: commit message
    """
    sg_branch = "%s/%s" % (repo, branch)
    # Special format for Shotgun web app.
    if repo == "shotgun":
        sg_branch = branch

    revision_data = {
        "project": project,
        "code": revision,
        "description": message,
        "attachment": {"name": "Github", "url": url},
        "sg_branch": sg_branch,
        "sg_component": get_component(repo, project)
    }

    if author:
        user = get_user_by_email(author)
        if not user:
            user = get_user_from_gh_login(author["username"])
        if user:
            revision_data["created_by"] = user

    sg = ShotgunHandler.get_conn()
    sg_revision = sg.create("Revision", revision_data)
    current_app.logger.info("Created Revision: %s" % sg_revision)
