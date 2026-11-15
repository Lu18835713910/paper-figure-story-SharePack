# Release deployment boundary

The 2026-11-15 publish-run command that iterated over Codex and WorkBuddy and
installed both PFS and SharePack is retired and must not be replayed from
shell history or a runbook. The installation log and recovery backups are
forensic evidence. Keep them outside release assets. The command was issued
interactively and is not a tracked installer.

Build only the SharePack wheel, source distribution and SharePack Skill ZIP.
Use the single-host SharePack installer for installation, upgrade and rollback.
Do not distribute PFS executable files or call a PFS installer. For assisted
mode the user independently installs PFS and supplies its verified artifacts.
The legacy RC workflow now has read-only permissions and a notice-only job.
