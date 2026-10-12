# HabitFlow deployment and data storage

When `server.py` starts, it creates `habitflow.db` in this folder. It is a SQLite database containing saved habits and journal entries.

Start locally with:

```powershell
py server.py
```

Then open `http://127.0.0.1:8000`.

HabitFlow accounts and journal entries are intentionally local to the browser profile. Signing into the same account again on the same device restores the same dated journal entries. Use the app's `Export My Data` and `Restore Backup` controls before moving to another browser or device; this is not a cloud authentication system.

The included Render configuration makes the app deployable, but Render's free web service can sleep and its local filesystem is not a reliable permanent database. It cannot honestly guarantee free 24/7 uptime or permanent data storage.

For reliable production deployment, use a hosted Python service plus a managed PostgreSQL database such as Supabase or Neon. Do not use free local SQLite storage for important production data unless the host provides persistent disk backups.

## Google sign-in

1. Create a Web client in Google Cloud Console under APIs & Services → Credentials.
2. Add your deployed site origin to the authorized JavaScript origins.
3. Start the server with `GOOGLE_CLIENT_ID` set to that Web client ID.

PowerShell example:

```powershell
$env:GOOGLE_CLIENT_ID = "your-client-id.apps.googleusercontent.com"
py server.py
```

The app reads this through `/api/config`. Never put a Google client secret in frontend JavaScript.
