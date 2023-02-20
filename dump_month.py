import datetime
import json
import collections

import keyring
from jira_dump import Dumper

import config


def main():
    today = datetime.datetime.today()

    with Dumper(
        server=config.jira_server,
        jql=config.issue_jql,
        auth=(
            config.username,
            keyring.get_password(config.jira_instance, config.username),
        ),
    ) as jira_dump:
        dev_hours = collections.defaultdict(int)

        development = [
            {
                "day": int(worklog["started"][8:10]),
                "task": "Development",
                "hours": worklog["time_spent"] / 3600,
                "comment": f"{worklog['issue']}\n{worklog['comment']}",
            }
            for worklog in jira_dump.worklogs
            if worklog["author"] == config.username
            if worklog["started"].startswith(f"{today.year}-{today.month:02}")
        ]

        for dev in development:
            dev_hours[dev["day"]] += dev["hours"]

        maintenance_issues = {
            issue["issue"]: issue["assignee"]
            for issue in jira_dump.issues
            if issue["issue_type"] == config.maintenance_issue_type
        }

        comments = [
            {
                "day": int(comment["created"][8:10]),
                "issue": comment["issue"],
                "comment": f"{comment['issue']} "
                + (
                    "investigation"
                    if maintenance_issues[comment["issue"]] == config.username
                    else "code review"
                    if comment["author"] == config.deployment_user
                    and config.username in comment["body"]
                    else "consultation"
                ),
            }
            for comment in jira_dump.comments
            if (
                (
                    comment["author"] == config.username
                    and comment["body"] != "Will check ASAP!"
                )
                or (
                    comment["author"] == config.deployment_user
                    and config.username in comment["body"]
                )
            )
            and comment["issue"] in maintenance_issues
            and comment["created"].startswith(f"{today.year}-{today.month:02}")
        ]

        maintenance = collections.defaultdict(str)

        for comment in comments:
            if comment["comment"] not in maintenance[comment["day"]]:
                maintenance[
                    comment["day"]
                ] = f"{maintenance[comment['day']]}\n{comment['comment']}".strip()

        maintenance = [
            {
                "day": day,
                "task": "Maintenance",
                "hours": 8.0 - dev_hours[day],
                "comment": comment,
            }
            for (day, comment) in maintenance.items()
            if 8 - dev_hours[day] > 0
        ]

        all_worklog = maintenance + development

        total_hours = collections.defaultdict(int)
        for issue in all_worklog:
            total_hours[issue["day"]] += issue["hours"]

        for day, hours in total_hours.items():
            if hours != 8:
                all_worklog += [
                    {
                        "day": day,
                        "task": "Maintenance",
                        "hours": 8.0 - hours,
                        "comment": "miscellaneous consultation + non-development tasks",
                    }
                ]

        all_worklog = sorted(all_worklog, key=lambda x: x["day"])

        with open("test", mode="w", encoding="utf8") as file:
            file.write(json.dumps(all_worklog, indent=4))


if __name__ == "__main__":
    main()
