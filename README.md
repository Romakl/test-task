# CEF Filter Proxy

A small service that sits between your security tools and your log system. It
takes in alerts, keeps only the ones you care about, and passes those along —
so the log system isn't flooded with noise.

The project has three parts:

| Folder | What's inside |
|---|---|
| [`backend/`](backend/) | The service itself. It listens for alerts, checks them against your rules, and forwards the ones that match. It also has a small web API. |
| [`frontend/`](frontend/) | A web page where you manage the rules and watch alerts arrive in real time. |
| [`docs/`](docs/) | Short, plain-language notes about what the project does, how it is built, and how it is kept safe. |

## Getting started

1. Start the service — see [`backend/README.md`](backend/README.md). It runs at
   http://localhost:8080.
2. Start the web page — see [`frontend/README.md`](frontend/README.md). It runs
   at http://localhost:3000.

Open the web page in your browser to add rules and watch alerts flow through.
