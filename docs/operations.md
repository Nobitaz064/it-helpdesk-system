# Deploying and operating Helpdesk

Use a persistent disk for the SQLite file and keep each environment in its own
database. Set `HELPDESK_DB_PATH` in the server or service environment before
launching Python. Relative paths are resolved from the current working
directory. Hosts that run several app replicas or regularly hit write
contention should evaluate a server database before scaling out.

## Set up or upgrade a company database

Use the same environment settings for initialization and the Streamlit service.

```powershell
$env:HELPDESK_DB_PATH = 'D:\HelpdeskData\helpdesk.db'
$env:HELPDESK_AUTH_MODE = 'oidc'
python -m pip install -r requirements.txt
python -m database.init_db --production
```

The initializer stores the schema version and applies upgrades in a single
transaction. A new production file contains categories and no demo users. The
production switch turns on OIDC for an existing database and preserves its
tickets, histories and users. A default initialization command does not turn
a production database back into a demo database. Existing demo user records
can be archived after reviewing which tickets reference them.

## Configure sign-in and enroll users

Register an OIDC client with your organization's identity provider. Register
the public HTTPS callback URL for this app. On the server, add these settings
to `.streamlit/secrets.toml` using the values from that registration.

```toml
[auth]
redirect_uri = "https://helpdesk.example.test/oauth2callback"
cookie_secret = "<deployment-specific random secret>"
client_id = "<registered client ID>"
client_secret = "<registered client secret>"
server_metadata_url = "<identity provider discovery URL>"
```

Store this file with the deployment. The server resolves a signed-in person
using the exact OIDC issuer and subject for this client. The application
reads the role from its own database on each run. Use a trusted source to
obtain the issuer and subject from your organization administrator.

```powershell
python -m database.manage_users create --issuer '<issuer>' --subject '<subject>' --name 'Helpdesk Admin' --email 'admin@example.test' --role admin
python -m streamlit run app.py
```

Use `--role employee` and `--role technician` to enroll the other pilot
roles. Use `database.manage_users link --user-id <id> --issuer <issuer> --subject <subject>`
to preserve an existing user's tickets. Use `database.manage_users unlink --issuer <issuer> --subject <subject>`
to revoke access while keeping the user's audit records. Run these operations
with the deployment's database settings and an authorized OS account.

For the local demo, configure `HELPDESK_AUTH_MODE=demo` and use a separately
initialized demo database. A company database rejects demo mode.

## Make and verify a backup

Use a new file name for each backup. The command uses the SQLite online backup
API, checks the snapshot with `PRAGMA quick_check`, and publishes it at the
specified path once the copy is complete. Use a directory on the server's local disk, then transfer the finished
snapshot to separate durable storage.

```powershell
python -m database.backup_db 'D:\HelpdeskBackups\helpdesk-before-upgrade.db'
```

Before upgrading a live app, take a backup and try the update against a copy.
For a restore drill, set `HELPDESK_DB_PATH` to a separate copy of the snapshot
and launch an isolated app instance. Verify login and role mappings, then check
an open ticket, a closed ticket, and both tickets' histories. Keep the original
production file while validating a restore. To recover, direct the stopped app
to the verified replacement file and restart it.

## Verify changes

Run `python -m unittest discover -s tests -v` against the checked-out code. The
CI workflow runs the same suite. Deployment checks should cover sign-in,
create → assign → resolve → close, read access under each role, concurrent
updates to one ticket, and recovery from a backup.
