# Agile assessment evidence

The staff message supplied on 28 October 2026 says the Week 13 demonstration will
review the Jira backlog, burndown chart and Agile meeting logs. These are project
delivery evidence; the retail application's ten core use cases remain unchanged.

## Jira setup

Existing project: **mon-13-15-group-8**, key **KAN**,
[board 2](https://mbse5620.atlassian.net/jira/software/projects/KAN/boards/2).
The owner created this board; preserve its existing KAN-1 and KAN-2 items.
The connected Atlassian service currently cannot access Jira, so no backlog import,
board conversion or sprint creation has been performed by this integration.
Reconnect the Atlassian integration to this site before making those changes.
Check the board's available sprint/backlog/report settings; use Scrum-compatible
tracking for the required burndown. Keep the existing review column.

`backlog.csv` is an import-ready starting backlog. Check the actual project's
available issue types and map Summary, Description and Labels during import.
It contains all ten core UCs plus current integration/verification work. No
assignees, estimates, historical status changes or completion dates are invented.
Items labelled `retrospective` document work already evidenced by source/PRs;
the team should confirm their acceptance and current status after importing.

[Contribution evidence](contribution-evidence.md) maps current implementations,
original authors, integration credit, remaining work and suggested present-day
tracking states to commits/PRs. It also records Avan's two newer unmerged commits;
their presence is contribution evidence, not proof they are already integrated.

## Real sprint and burndown

1. Review the remaining work with all five members and agree the sprint goal.
2. Estimate the remaining items together before starting the sprint. Enable the
   board's estimation feature if the team uses story points.
3. Choose actual start/end dates, based on the confirmed Canvas/demo schedule.
4. Start the sprint and update issue statuses as work actually progresses. Add
   PR/test links before marking an implementation accepted.
5. Review remaining work daily. Keep scope changes visible in Jira rather than
   altering the original estimates to make the chart look better.
6. During the demo, open the actual sprint burndown and explain its scope,
   remaining work and changes. A newly created sprint cannot demonstrate a
   week of historical Jira tracking; use Git/PR evidence for earlier work and
   describe the late tracking setup honestly.

Atlassian references: [Sprint burndown](https://support.atlassian.com/jira-software-cloud/docs/what-is-the-sprint-burndown-report/),
[board insights and scope changes](https://support.atlassian.com/jira-software-cloud/docs/understand-insights-on-the-board-in-a-team-managed-project/).

## Meetings and evidence

Copy `meeting-log-template.md` for each actual planning meeting, stand-up,
review or retrospective. Record date/time/timezone, real attendees, decisions,
progress, blockers and agreed actions with Jira keys. Link supporting PRs and
tests. Never fill in attendance, votes or historical meetings that were not
reported by participants. This chat is implementation evidence, not proof that
all five students attended an Agile meeting.

For the demo, each member should be able to show their real issues, commits,
reviews/tests and a meeting contribution. Use `../team-status.md` as an evidence
index, not a substitute for participation or the required contribution statement.

## Definition of done

- Behaviour checked against the submitted report, with relevant section/figure.
- Tests appropriate to the feature pass; fixture/live verification is labelled.
- Changes reviewed and merged through a pull request; no credentials committed.
- README/interface notes updated when behaviour or setup changes.
- Jira item links the evidence; the team confirms completion rather than relying
  only on an automated test count.
