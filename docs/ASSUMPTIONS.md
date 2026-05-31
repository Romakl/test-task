# Choices we made

The task left room for some decisions. Here they are in plain words: what we
chose, why, and how to change it.

| Choice | Why | How to change |
|---|---|---|
| Built with Python and FastAPI. | It matched the example project we were pointed at. | The design (listen → read → check → forward) would work in any language. |
| Alerts come in and go out over UDP, one alert per message. | That is what the task described. | To use TCP instead, add a TCP listener and agree on a separator with the big alert system. |
| `name` and `severity` are header fields; the other eight are `name=value` pairs. | This matches the standard CEF format. | Change the mapping in `backend/app/cef/models.py`. |
| If no rule matches, the alert is **kept** (not dropped). | For alerts, losing a real one by accident is worse than keeping a boring one. | Set the default to "drop" in the settings or in the rules file. |
| If a message cannot be read, it is **kept** and counted. | Same reason — do not throw away something that might be real. | Set `FORWARD_ON_PARSE_ERROR` to false. |
| Rules are checked in order, first match wins, with simple AND/OR. | This matches how well-known tools work, and it is easy to predict. | Add grouped conditions later if you need them. |
| Data is saved in **Postgres**: the rules, a history of every change, and a copy of each decision. | A real database keeps data safe across restarts and is easy to search. | Point `DATABASE_URL` at your own database. |
| Live counts and the recent-events list are kept **in memory**. | They are only for the screen and can reset on restart. | They are also published at `/metrics` if you want to record them elsewhere. |
| Changing rules can need a secret token; reading is open. | Simple protection for a prototype. | Put a login system in front, or add real user accounts. |
| Severity words like "High" are turned into numbers. | So a rule like "severity is 9 or higher" works whether the source sends `9` or `High`. | Adjust the word-to-number mapping in `backend/app/rules/engine.py`. |

The choices most worth a second look: **keeping** (not dropping) when nothing
matches or when a message cannot be read, and using **UDP**, which can lose
messages. Both are easy to change if your needs are different.
