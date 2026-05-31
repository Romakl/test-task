# Keeping it safe

This project handles messages that arrive over the network from outside, so we
take care to keep both the **code** and the **running service** safe. Here is
how, in plain words.

## Keeping the code safe

Before any code is saved, a set of automatic checks runs (these live in
[`../backend/.pre-commit-config.yaml`](../backend/.pre-commit-config.yaml) and run
again in the cloud):

- **Style and mistakes** — a tool called Ruff checks the code is tidy and spots
  common errors.
- **Types** — a tool called MyPy checks the code uses the right kinds of values.
- **Known weaknesses** — a tool called Bandit looks for risky code patterns.
- **Secrets** — a tool called Gitleaks makes sure no passwords or keys get saved
  by accident.
- **Tests** — the test suite runs and must pass, covering at least 80% of the code.

We also pin every outside library to an exact version (in
[`../backend/uv.lock`](../backend/uv.lock)) so builds are repeatable, and we scan
those libraries for known problems on every change and once a week.

The cloud checks live in [`../.github/workflows`](../.github/workflows).

## Keeping the running service safe

The riskiest part is the code that reads messages from the network, because
anyone could send a broken or nasty message. So:

- The message reader **never crashes** on a bad message. It just counts it and
  moves on.
- There is a **limit on message size** and a **limit on how many** messages one
  sender can send per second.
- You can set an **allow-list** of senders. (Senders can fake their address, so
  this is a helper, not a lock — use a firewall for real protection.)
- Changing the rules can require a **secret token**. In production the service
  **refuses to start** without one.
- The web page talks to the service over the network, and the service only
  accepts the web page's address (this is called CORS).

When packaged for production, the service runs inside a container as a normal
(non-admin) user, on a read-only disk, with extra powers dropped. The container
image is also scanned for known problems before it ships.

## What is not covered yet

This is a working prototype, so a few production extras are noted but not done:
encryption on the wire to the big alert system, signed build records, and
locking down which senders are allowed at the network level. These are listed so
no one assumes they are already in place.
