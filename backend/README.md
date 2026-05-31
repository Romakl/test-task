# Backend — CEF Filter Proxy

This is the service. It receives security alerts over the network, keeps only the
ones that match your rules, and forwards those to your big alert system (ELK). It
saves your rules and a history of what it did in a Postgres database. The web page
that controls it is in [`../frontend`](../frontend).

```
[ tool that finds problems ] --alert/UDP--> [ this service ] --UDP--> [ big alert system ]
                                                  │
                                             your rules
                                            (keep / drop)
                                                  │
                                    web API (port 8080)  ◀──  web page (../frontend, :3000)
```

Built with Python 3.13, FastAPI, SQLAlchemy + Postgres, and uv.

## The fields it works with

```
eventid  filterhostname  filterid  filteripaddress  filternodename
filterpriority  filtertype  notificationtime  name  severity
```

`name` and `severity` are header fields; the other eight are `name=value` pairs.
Your rules can test any of them. There is more in
[`../docs/01-research-what-why.md`](../docs/01-research-what-why.md).

## What it can do

- Reads alerts quickly and never crashes on a broken message.
- Checks each alert against your rules, top to bottom — first match wins.
- Forwards kept alerts exactly as they arrived.
- Saves the rules, every rule change, and a copy of each decision in Postgres.
- Offers a web API with live updates for the web page.
- Writes a clear log line for every decision.
- Ships as a locked-down container.

## Quick start

You need a Postgres database. The easiest way is Docker.

```bash
# 1. Install dependencies and git hooks
make dev

# 2. Start a local Postgres (or point DATABASE_URL at your own)
make db-up

# 3. Copy the example settings
cp .env.example .env

# 4. Run the service (http://localhost:8080). On first run it creates its tables
#    and loads the starter rules from config/rules.example.yaml.
make run

# 5. In another terminal, run a stand-in for the big alert system
make run-mock-elk

# 6. In a third terminal, send some test alerts
make generate ARGS="--count 20 --malformed-rate 0.1"
```

The API and its built-in docs are at http://localhost:8080/docs. To use the web
page, start it from [`../frontend`](../frontend) (`bun install && bun dev`, then
open http://localhost:3000).

### With Docker

```bash
docker compose up    # starts Postgres, the service, and the stand-in receiver
```

## Common commands

| Command | What it does |
|---|---|
| `make run` | Run the service (reloads on changes) |
| `make db-up` / `make db-down` | Start / stop a local Postgres in Docker |
| `make migrate` | Apply database migrations |
| `make run-mock-elk` | Run the stand-in receiver (port 5140) |
| `make generate ARGS="…"` | Send test alerts |
| `make check` | Style, format, and type checks |
| `make test` / `make test-cov` | Run the tests (with coverage) |
| `make security` | Scan the code and the libraries for known problems |

## Web API

The service has no web page of its own; it only offers an API, which the web page
in [`../frontend`](../frontend) calls.

| Path | What it gives you |
|---|---|
| `/` | A small status message (JSON) |
| `/docs` | Interactive API docs |
| `/health` | Is it up? Is the database reachable? |
| `/metrics` · `/api/stats` | Counts (received, kept, dropped, …) |
| `/api/rules` | Read and change the rules |
| `/api/dry-run` | Try an alert against the rules without forwarding it |
| `/api/events` · `/api/events/stream` | Recent decisions · live stream |
| `/api/events/history` | Older decisions, from the database |
| `/api/audit` | History of rule changes, from the database |

## Folder layout

```
app/
  cef/            reads the alert text into fields
  rules/          the rule model, the rule checker, and the store
  db/             database models and connection
  proxy/          the listener, the forwarder, and the pipeline
  observability/  counts, the recent-events list, and the database writer
  api/            the web API
  core/           settings and logging
tools/            a test alert sender and a stand-in receiver
config/           example rules and the rule format
migrations/       database migrations (Alembic)
tests/            the tests
```

The web page is in [`../frontend`](../frontend); the plain-language notes are in
[`../docs`](../docs).
