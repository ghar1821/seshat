# Scheduling the weekly digest with launchd on macOS

`launchd` is macOS's native job scheduler. Unlike `cron`, it runs as your full user session (no Full Disk Access issues) and will run a missed job when the Mac wakes from sleep.

## 1. Make the script executable

```bash
chmod +x ~/projects/paper_digest/run_digest.sh
```

## 2. Create the LaunchAgent plist

LaunchAgents live in `~/Library/LaunchAgents/`. Create the file:

```bash
nano ~/Library/LaunchAgents/com.putri.seshat.plist
```

Paste the following (the schedule below is every Monday at 02:00):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.putri.seshat</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/putri.g/projects/paper_digest/run_digest.sh</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>1</integer>
        <key>Hour</key>
        <integer>2</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>/Users/putri.g/projects/paper_digest/output/logs/launchd-stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/putri.g/projects/paper_digest/output/logs/launchd-stderr.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>HOME</key>
        <string>/Users/putri.g</string>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
```

`StartCalendarInterval` weekday values: 1 = Monday, 5 = Friday, 7 = Sunday.

## 3. Load the agent

```bash
launchctl load ~/Library/LaunchAgents/com.putri.seshat.plist
launchctl start com.putri.seshat
```

This registers the job, persists across reboots, and runs it immediately so you can confirm it works.

## 4. Verify it is loaded

```bash
launchctl list | grep seshat
```

You should see a line like:

```
-    0    com.putri.seshat
```

The second column is the last exit code. `0` means success (or not yet run). A non-zero value means the last run failed — check the logs.

## 5. Applying changes to the plist

**Any time you edit the plist, you must unload and reload for the changes to take effect:**

```bash
launchctl unload ~/Library/LaunchAgents/com.putri.seshat.plist
launchctl load  ~/Library/LaunchAgents/com.putri.seshat.plist
```

To immediately test:

```bash
launchctl start com.putri.seshat
tail -f ~/projects/paper_digest/output/logs/launchd-stdout.log
```

> **Note:** Editing the plist on disk has no effect while the agent is loaded. Always unload first.

## Common commands

| Task | Command |
|------|---------|
| Load / register | `launchctl load ~/Library/LaunchAgents/com.putri.seshat.plist` |
| Unload / unregister | `launchctl unload ~/Library/LaunchAgents/com.putri.seshat.plist` |
| Apply plist changes | unload → load |
| Run now | `launchctl start com.putri.seshat` |
| Check status | `launchctl list \| grep seshat` |

## Troubleshooting

- **Job not in `launchctl list`** — plist has a syntax error. Validate: `plutil ~/Library/LaunchAgents/com.putri.seshat.plist`.
- **Non-zero exit code** — check `~/projects/paper_digest/output/logs/launchd-stderr.log`.
- **Ollama not starting** — confirm `ollama` is on the `PATH` in the plist (`which ollama` to find the right path).
- **Job skipped while Mac was asleep** — launchd runs it the next time the Mac is awake past the scheduled time.
