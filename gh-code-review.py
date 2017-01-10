"""
Web hook that handles POST requests form Github Code Review triggers.
"""
from flask import Flask, request, render_template
import re

app = Flask(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    VALID_ACTIONS=["assigned", "unassigned"],
    DEBUG=True,
))
app.config.from_envvar("SG_CODE_REVIEW_SETTINGS", silent=True)


@app.route("/", methods=["POST"])
def handle_request():
    data = request.get_json()
    app.logger.debug("Got JSON data: %s" % data)

    # Check which action was performed on the pull request.
    action = data.get("action")
    app.logger.debug("Action: %s" % action)

    # If we don"t care about this action then we"re done.
    if action not in app.config["VALID_ACTIONS"]:
        app.logger.info("Action not valid, skipping")
        return ('', 204)

    pr = data.get("pull_request")
    if not pr:
        app.logger.info("No PR data received.")
        return ('', 204)

    ticket_num = parse_ticket_from_title(pr.get("title"))
    if not ticket_num:
        pass

    data = {
        "ticket": ticket_num,
        "assignee": pr["assignee"]["login"],
        "title": pr["title"],
        "description": pr["body"]
    }
    return render_template("code_review.html", pr=data)


def parse_ticket_from_title(title):
    """
    Get SG Internal ticket number out of the pull request title.

    :param str title: Title of the pull request
    :return: Ticket number on SG Internal as int.
    """
    result = re.match(".*#(\d+).*", title)
    if not result:
        return

    return result.group(1)
