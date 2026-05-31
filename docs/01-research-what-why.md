# What it does and why

## The short version

Security tools watch computers and networks. When they see something that might
be a problem, they send out a small message called an **alert**. All these
alerts go to a big system that stores them and shows them on screens, so people
can look for trouble. A common one is called **ELK**.

The trouble: there are **too many** alerts. Most are boring and not worth
keeping. The important ones get buried, and storing everything costs money.

This project is a small helper that sits **in the middle**:

```
[ the tool that finds problems ]  ->  [ this helper ]  ->  [ the big alert system ]
```

You give the helper simple **rules**, like "throw away the heartbeat messages"
or "always keep anything marked serious". For every alert that comes in, the
helper checks your rules and only passes on the ones you want. The rest are
dropped. This cuts the noise without changing the tool that sends the alerts or
the system that stores them.

It also saves your rules, a record of every rule change, and a copy of what it
decided in a database, so nothing is lost if it restarts.

## How an alert looks

The alerts use a text format called **CEF**. It is one line of text with a few
parts separated by `|`, then a list of `name=value` pairs. Here is one:

```
CEF:0|Acme|FilterEngine|1.0|100|Port scan detected|8|filtertype=ids filteripaddress=10.0.0.5
```

The alerts arrive as small network messages (this style is called **syslog over
UDP**). Each message is one alert. UDP is fast but does not promise delivery, so
the helper is careful: it never crashes on a broken message, and it keeps a
count of anything it had to drop.

## The fields this helper works with

Each alert from this source has these ten fields:

```
eventid  filterhostname  filterid  filteripaddress  filternodename
filterpriority  filtertype  notificationtime  name  severity
```

`name` and `severity` are part of the fixed header. The other eight come as
`name=value` pairs. Your rules can test any of them — for example, "drop it when
`filtertype` is `heartbeat`", or "keep it when `severity` is 9 or higher".

## Why build it instead of using something else

Tools like rsyslog, syslog-ng, Logstash, Vector, and Cribl can also filter and
forward messages. They are powerful, but they are general-purpose and heavier to
set up. We built a small, focused helper because we wanted:

- a simple web page built around these exact ten fields,
- a tiny, easy-to-read service, and
- a clear record, saved in a database, of what it did.

If you mainly need broad features and do not want to run your own service, one
of the tools above may be a better fit. For a small, focused job, this helper is
simpler.

## One thing to remember

Because the helper sits in the middle, the big alert system sees the **helper's**
network address as the sender, not the original machine. The original machine is
still named inside the alert (in `filteripaddress`, `filterhostname`, and
`filternodename`), so no information is lost.
