import logging
import shotgun_api3
from constants import APP_SETTINGS
from constants import CR_ASSIGNED_REPLY_TEMPLATE
from constants import CR_EDITED_REPLY_TEMPLATE

logger = logging.getLogger("sg_webhooks.%s" % __name__)

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


def get_user_from_gh_login(github_login):
    """
    Lookup SG HumanUser entity with the specified Github login.

    :param str github_login: Github login to look up on Shotgun internal.
    :return: SG HumanUser as a standard entity dictionary or None.
    """
    if github_login:
        sg = ShotgunHandler.get_conn()
        return sg.find_one("HumanUser", [["sg_github_login", "is", github_login]], ["name"])


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
    logger.debug("Updated SG Ticket %d: %s" % (ticket_num, result))

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
    logger.debug("Updated SG Ticket %d: %s" % (ticket_num, result))


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
    logger.debug("Added Reply to SG Ticket %d: %s" % (ticket_num, result))