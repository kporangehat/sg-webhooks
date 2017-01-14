# SG Web Hooks

This is a Docker-enabled lightweight Flask app to handle incoming web hook requests.

## Current Web Hooks Handled

#### Github Post-Commit Hook
```
/github_commit_hook
```
When commits are pushed to Github, create a Revision entity in Shotgun for each commit
with information about the repo, branch, author, component, commit id and commit message.

For details about the request data sent to this endpoint see [Github PushEvent](https://developer.github.com/v3/activity/events/types/#pushevent)

#### Github Code Review Assignment
```
/github_cr_assignment
```
When pull request is **assigned**, find the corresponding ticket in Shotgun and assign the
code review to the assignee, set the status to "Code Review" and add a Reply with the
pull request description.

When pull request is **unassigned**, find the corresponding ticket in Shotgun and un-assign
the code review from the assignee.

When a pull request title or description is **edited**, if there is a current assignee, add a
Reply to the Shotgun ticket with the updated pull request title and description.

For details about the request data sent to this endpoint see [Github PullRequestEvent](https://developer.github.com/v3/activity/events/types/#pullrequestevent)

## Installation
Start with [Getting started with Docker](https://wiki.autodesk.com/display/SHOT/Getting+started+with+Docker)
```
    docker-compose up
```
