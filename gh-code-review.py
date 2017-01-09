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
app.config.from_envvar("GH_CODE_REVIEW_SETTINGS", silent=True)


@app.route("/", methods=["POST"])
def handle_request():
    # Check which action was performed on the pull request.
    action = request.form.get("action")
    # If we don"t care about this action then we"re done.
    if action not in app.config["VALID_ACTIONS"]:
        return

    pr = request.form.get("pull_request")

    ticket_num = parse_ticket_from_title(pr.get("title"))
    if not ticket_num:
        return

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
