# SharePack installation

Install the SharePack wheel in your Python environment. Extract the SharePack
Skill ZIP independently. From the extracted bundle, run:

    python scripts/install_sharepack.py install --skills-dir PATH_TO_ONE_HOST_SKILLS

Choose either Codex or WorkBuddy explicitly. Repeat separately for another host
if desired. Keep the versioned wheel and Skill ZIP together. Restart the host
to discover paper-figure-story-sharepack.

The installer manages only paper-figure-story-sharepack and its sibling backup
store sharepack-skill-backups. For removal run the same command with uninstall.
To restore a backup, use rollback and --backup BACKUP_ID on the same host.
Installation and rollback copy only the selected SharePack Skill files.
Wheel installation and removal use pip and are independent of Skill backups.

Standalone reads a paper and reviewed editorial inputs. It requires no PFS.
For PFS-assisted, [install PFS independently from its official repository](https://github.com/Lu18835713910/paper-figure-story).
Ask the host which PFS Skill directory it loaded and inspect that version and
the installation receipt or source revision. Version 1.2.0 alone does not
identify a Git revision. An absent revision receipt means revision unverified.
Use reviewed M1 Schema 1.1, pfs-research-logic-1 and matching verified Figure
artifacts. SharePack validates those file contracts and source hashes directly.
It has no fallback PFS implementation and invokes no PFS installer.

Run python scripts/check_pfs_compatibility.py --loaded-skill PATH for the host-selected PFS directory. Its tree SHA distinguishes installations even when VERSION matches. Match the tree to an independent PFS receipt to establish a Git revision. The bridge also checks each artifact contract when it is used.

Maintainers: see docs/RELEASE_DEPLOYMENT.md in the source repository.

Use the v1.0.1 wheel and v1.0.1 Skill ZIP together. Experimental simplified PFS A handoff is not supported.
