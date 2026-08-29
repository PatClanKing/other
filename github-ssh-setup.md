# GitHub SSH Setup, Start to Finish (Git Bash)

Practical runbook for creating an SSH (Secure Shell) key, loading it into the SSH agent, registering it with GitHub, and proving the whole chain works.

Everything here stays inside Git Bash. The commands are plain POSIX (Portable Operating System Interface) shell, so the same lines also work on macOS and Linux.

Every command is copy pasteable.

---

<!-- toc -->

## Contents

* [1. Git Bash specifics you need to know first](#1-git-bash-specifics-you-need-to-know-first)
* [2. Quick path (if you just want it working)](#2-quick-path-if-you-just-want-it-working)
* [3. The full procedure](#3-the-full-procedure)
  * [3.1 See what you already have](#31-see-what-you-already-have)
  * [3.2 Choose a key type (ranked)](#32-choose-a-key-type-ranked)
  * [3.3 Generate the key](#33-generate-the-key)
  * [3.4 Get the ssh-agent running](#34-get-the-ssh-agent-running)
  * [3.5 Load the key into the agent](#35-load-the-key-into-the-agent)
  * [3.6 Verify the agent and the loaded keys](#36-verify-the-agent-and-the-loaded-keys)
  * [3.7 Register the public key with GitHub (ranked)](#37-register-the-public-key-with-github-ranked)
  * [3.8 Test the connection to GitHub manually](#38-test-the-connection-to-github-manually)
  * [3.9 Verify you are talking to the real GitHub](#39-verify-you-are-talking-to-the-real-github)
  * [3.10 The ~/.ssh/config file](#310-the-sshconfig-file)
  * [3.11 Make Git actually use the key](#311-make-git-actually-use-the-key)
* [4. Multiple GitHub accounts or keys](#4-multiple-github-accounts-or-keys)
* [5. Optional: sign commits with the same SSH key](#5-optional-sign-commits-with-the-same-ssh-key)
* [6. File permissions](#6-file-permissions)
* [7. Troubleshooting matrix](#7-troubleshooting-matrix)
* [8. Full verification checklist](#8-full-verification-checklist)
* [9. Cheat sheet](#9-cheat-sheet)
* [10. Terminology](#10-terminology)
* [11. References (every link checked, HTTP 200)](#11-references-every-link-checked-http-200)

<!-- /toc -->

---

## 1. Git Bash specifics you need to know first

1. `~` is your home directory and `~/.ssh` is where every key lives. Confirm where you are:
   ```bash
   echo "$HOME" && pwd
   ```
2. Git Bash ships its own OpenSSH at `/usr/bin/ssh`, and Git calls it by default. Leave `core.sshCommand` unset so `git`, `ssh` and `ssh-add` all use that one client and therefore one agent. Verify with:
   ```bash
   which -a ssh && git config --global --get core.sshCommand
   ```
   You want `/usr/bin/ssh` and empty output.
3. Drive letters are mounted under a single slash, so a folder like `C:\git\misc` is `/c/git/misc`.
4. Paths starting with `/` are sometimes rewritten by MSYS2, the Unix compatibility layer Git Bash is built on. If an argument gets mangled, prefix the command with `MSYS_NO_PATHCONV=1`.
5. If an interactive prompt hangs or you see `the input device is not a TTY`, prefix the command with `winpty`, for example `winpty ssh -T git@github.com`.
6. `clip.exe` is the clipboard helper Git Bash gives you, used in section 3.7.
7. **Every step below starts with a "Run from" line** telling you which directory to be in. Most steps work from anywhere because the paths are absolute, but the Git steps genuinely need you to be inside a repository. Check where you are at any time:
   ```bash
   pwd
   ```

---

## 2. Quick path (if you just want it working)

**Run from:** anywhere. Every path below is absolute (`~/.ssh/...`), so the current directory does not matter. If you want to be certain, start at your home directory:

```bash
cd ~ && pwd
```

Generate the key pair:

```bash
ssh-keygen -t ed25519 -C "<email>" -f ~/.ssh/id_ed25519
```

Start an agent in this shell:

```bash
eval "$(ssh-agent -s)"
```

Load the key into it, typing the passphrase once:

```bash
ssh-add ~/.ssh/id_ed25519
```

Copy the **public** key to the clipboard:

```bash
cat ~/.ssh/id_ed25519.pub | clip.exe
```

Paste the clipboard into <https://github.com/settings/keys>, then verify:

```bash
ssh -T git@github.com
```

Expected: `Hi <username>! You've successfully authenticated, but GitHub does not provide shell access.`

Make the agent survive new Git Bash windows with the `~/.bashrc` block in section 3.4.2. The rest of this document explains each step and every verification command.

---

## 3. The full procedure

Eleven steps, in order. Each step is numbered so you can jump straight back to it: step 4 is section 3.4, and its sub steps are 3.4.1 onward. If you followed the quick path above and it worked, you only need the steps that failed.

---

### 3.1 See what you already have

**Run from:** `~/.ssh`, so the listing below shows what you expect. Create the directory if it is not there yet:

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh && cd ~/.ssh && pwd
```

Expected output: `/c/Users/<you>/.ssh`

#### 3.1.1 Which SSH client is this shell using?

A machine can carry several OpenSSH installations, and mixing them is the cause of most "it works in one terminal but not the other" confusion. List every one on the path:

```bash
which -a ssh ssh-add ssh-keygen
```

Then check the version of the one that wins:

```bash
ssh -V
```

1. `/usr/bin/ssh` is the Git Bash OpenSSH and the assumption of this whole guide.
2. Check which client Git itself will call:
   ```bash
   git config --global --get core.sshCommand
   ```
   Empty output means Git uses `/usr/bin/ssh`, which is what you want. If it prints a path, clear it:
   ```bash
   git config --global --unset core.sshCommand
   ```

#### 3.1.2 Do keys already exist?

Look before you generate, because a new key with a default name overwrites an old one without asking twice. The `-a` flag matters here, since most of these files are hidden:

```bash
ls -la ~/.ssh
```

1. Files with no extension (`id_ed25519`, `id_rsa`) are **private** keys. Never share or paste these.
2. Files ending `.pub` are **public** keys. These are what GitHub wants.
3. `known_hosts`, `config`, `authorized_keys` are not keys.

#### 3.1.3 Fingerprint every key you already have

A fingerprint is how you tell which local file corresponds to which key registered on GitHub. Print one for every public key in the directory:

```bash
for f in ~/.ssh/*.pub; do ssh-keygen -l -f "$f"; done
```

Output format: `256 SHA256:<fingerprint> <comment> (ED25519)`. Compare that fingerprint against what GitHub lists at <https://github.com/settings/keys> to know which local key matches which registered key.

---

### 3.2 Choose a key type (ranked)

Four types worth considering, and one group to avoid outright:

| Rank | Option | Flag | Why / why not |
|------|--------|------|---------------|
| 1 | **Ed25519** | `-t ed25519` | Best default. Small, fast, strong, supported by GitHub and every OpenSSH 7.0+ (2015 onward). |
| 2 | **Ed25519 on a hardware key (FIDO2, Fast IDentity Online v2)** | `-t ed25519-sk` | Highest security, the private key cannot be copied off the device. Needs OpenSSH 8.2+ and the physical key present at every use. |
| 3 | **ECDSA (Elliptic Curve Digital Signature Algorithm) on a hardware key** | `-t ecdsa-sk` | Same hardware benefit, use only if your security key predates `ed25519-sk` support. |
| 4 | **RSA (Rivest Shamir Adleman) 4096** | `-t rsa -b 4096` | Only for old servers or tooling that cannot parse Ed25519. Bigger and slower. |
| x | **DSA (Digital Signature Algorithm), RSA 1024/2048** | n/a | Do not use. DSA is removed from modern OpenSSH, small RSA is deprecated. |

Recommendation: **option 1**, unless you own a security key, in which case **option 2**. Hardware backed keys need OpenSSH 8.2 or newer, so check `ssh -V` first.

---

### 3.3 Generate the key

**Run from:** `~/.ssh`. This is where Git Bash and `gh` look by default, so keys kept anywhere else need extra configuration for no benefit.

```bash
cd ~/.ssh && pwd
```

The `-f ~/.ssh/...` argument in each command below is absolute, so the key lands in the right place even if you forget to `cd`. Being in `~/.ssh` just means `ls` immediately shows you the result.

#### 3.3.1 Ed25519 (recommended)

Generate the pair. The flags are explained immediately below, so you can read them before running anything:

```bash
ssh-keygen -t ed25519 -C "<email>" -f ~/.ssh/id_ed25519
```

1. `-t` = key type.
2. `-C` = comment, conventionally your email. Purely a label to help you identify the key later.
3. `-f` = output file. Naming per purpose (for example `~/.ssh/id_ed25519_work`) keeps multi account setups sane.
4. You are prompted for a passphrase. **Use one.** The agent means you only type it once per session.

#### 3.3.2 RSA fallback

Use this only when something in your toolchain cannot parse Ed25519. The `-b 4096` is not optional in practice, because shorter RSA keys are deprecated:

```bash
ssh-keygen -t rsa -b 4096 -C "<email>" -f ~/.ssh/id_rsa
```

#### 3.3.3 Hardware backed key

This needs OpenSSH 8.2 or newer and the security key physically present, both when you create it and every time you use it:

```bash
ssh-keygen -t ed25519-sk -C "<email>" -f ~/.ssh/id_ed25519_sk
```

Touch the security key when it blinks.

#### 3.3.4 Confirm the pair was written

Both halves must exist, and the public half must be readable as a key rather than as whatever a mistyped redirect left behind:

```bash
ls -l ~/.ssh/id_ed25519 ~/.ssh/id_ed25519.pub && ssh-keygen -l -f ~/.ssh/id_ed25519.pub
```

#### 3.3.5 Change or add a passphrase later

The passphrase protects the file, not the identity, so changing it leaves the key itself untouched and nothing needs re registering with GitHub:

```bash
ssh-keygen -p -f ~/.ssh/id_ed25519
```

#### 3.3.6 Rebuild a lost public key from the private key

Deleting a `.pub` file is recoverable, because the public half can always be derived again from the private half. Losing the private key is not:

```bash
ssh-keygen -y -f ~/.ssh/id_ed25519 > ~/.ssh/id_ed25519.pub
```

---

### 3.4 Get the `ssh-agent` running

**Run from:** anywhere, `cd ~` is a fine default. An agent belongs to a shell session, not to a directory, so your current location has no effect on it.

#### 3.4.1 Options (ranked)

Three ways to have an agent available when you need one:

| Rank | Option | Best for | Trade off |
|------|--------|----------|-----------|
| 1 | **Agent auto started from `~/.bashrc`** | Everyday use | Passphrase once per reboot, and every Git Bash window shares the one agent |
| 2 | **1Password or Bitwarden SSH agent** | Teams already using that password manager | Biometric unlock instead of a passphrase, but adds a dependency and an `IdentityAgent` line in `~/.ssh/config` |
| 3 | **`eval "$(ssh-agent -s)"` typed per shell** | One off work, CI (Continuous Integration) | Dies with the shell, and each new window starts a fresh empty agent |

Recommendation: **option 1**. It is option 3 plus five lines of `~/.bashrc`, and it removes the most common daily annoyance, which is a new terminal window that has forgotten your key.

#### 3.4.2 Option 1, start it now and make it persistent

Start it in the current shell:

```bash
eval "$(ssh-agent -s)"
```

Then append this block to `~/.bashrc` so every new Git Bash window reuses one agent instead of spawning a new one:

```bash
cat >> ~/.bashrc <<'EOF'

# Reuse a single ssh-agent across Git Bash sessions
SSH_ENV="$HOME/.ssh/agent.env"
agent_load_env() { test -f "$SSH_ENV" && . "$SSH_ENV" >/dev/null; }
agent_start() { (umask 077; ssh-agent >"$SSH_ENV"); . "$SSH_ENV" >/dev/null; }
agent_load_env
ssh-add -l >/dev/null 2>&1
if [ $? -eq 2 ]; then agent_start; ssh-add ~/.ssh/id_ed25519; fi
EOF
```

Apply it without opening a new window:

```bash
source ~/.bashrc
```

`~/.bashrc` is the file Git Bash reads. If you only have `~/.bash_profile`, make sure it sources `~/.bashrc`:

```bash
grep -q 'bashrc' ~/.bash_profile 2>/dev/null || echo '[ -f ~/.bashrc ] && . ~/.bashrc' >> ~/.bash_profile
```

#### 3.4.3 Option 3, ad hoc for one shell

Start an agent that lives only as long as this window. The `eval` matters: `ssh-agent -s` only prints the environment variables, so without it the agent starts but this shell never learns how to reach it.

```bash
eval "$(ssh-agent -s)"
```

Kill it when you are done:

```bash
ssh-agent -k
```

---

### 3.5 Load the key into the agent

**Run from:** anywhere. The key paths are absolute.

```bash
ssh-add ~/.ssh/id_ed25519
```

Add with a lifetime, the agent forgets it after 8 hours:

```bash
ssh-add -t 8h ~/.ssh/id_ed25519
```

On macOS, store the passphrase in the Keychain so it survives reboots:

```bash
ssh-add --apple-use-keychain ~/.ssh/id_ed25519
```

---

### 3.6 Verify the agent and the loaded keys

**Run from:** anywhere. Nothing here touches the current directory.

Four independent checks.

#### 3.6.1 Is an agent running, and is *this* shell talking to it?

These are two separate questions, and confusing them wastes a lot of time. First, is a process running anywhere on the machine?

```bash
ps aux | grep -i "[s]sh-agent"
```

Second, does this particular shell know how to reach one?

```bash
echo "SSH_AUTH_SOCK=$SSH_AUTH_SOCK"
echo "SSH_AGENT_PID=$SSH_AGENT_PID"
```

An empty `SSH_AUTH_SOCK` means this shell is **not** talking to any agent, even if one is running in another window. That is the number one Git Bash gotcha, and section 3.4.2 fixes it permanently.

#### 3.6.2 Which keys does the agent currently hold?

Fingerprints only:

```bash
ssh-add -l
```

Full public keys, the exact text GitHub stores:

```bash
ssh-add -L
```

How to read the result:

| Output | Meaning | Fix |
|--------|---------|-----|
| `256 SHA256:... comment (ED25519)` | Key is loaded and usable | Nothing to do |
| `The agent has no identities.` | Agent runs, no key loaded | `ssh-add ~/.ssh/id_ed25519` |
| `Could not open a connection to your authentication agent.` | No agent reachable from this shell | `eval "$(ssh-agent -s)"`, then section 3.4.2 |
| `Error connecting to agent: No such file or directory` | Stale `SSH_AUTH_SOCK` pointing at a dead agent | `unset SSH_AUTH_SOCK` then start a fresh agent |

Exit codes of `ssh-add -l`: **0** = keys present, **1** = agent reachable but empty, **2** = no agent reachable.

```bash
ssh-add -l; echo "exit code: $?"
```

One line health check:

```bash
ssh-add -l >/dev/null 2>&1; case $? in 0) echo "agent up, keys loaded"; ssh-add -l;; 1) echo "agent up, no identities";; 2) echo "no agent reachable from this shell";; esac
```

Reusable function, drop it in `~/.bashrc`:

```bash
cat >> ~/.bashrc <<'EOF'
sshcheck() {
  echo "client:  $(command -v ssh)  $(ssh -V 2>&1)"
  echo "socket:  ${SSH_AUTH_SOCK:-<none>}"
  ssh-add -l >/dev/null 2>&1
  case $? in
    0) echo "agent:   up, keys loaded"; ssh-add -l ;;
    1) echo "agent:   up, no identities" ;;
    2) echo "agent:   NOT reachable" ;;
  esac
  echo "github:  $(ssh -o BatchMode=yes -T git@github.com 2>&1 | head -1)"
}
EOF
```

Then run `sshcheck` any time you want the full picture.

#### 3.6.3 Does the agent key match the key on disk and the key on GitHub?

Print both fingerprints side by side so you can compare them in one glance rather than from memory:

```bash
ssh-add -l && ssh-keygen -l -f ~/.ssh/id_ed25519.pub
```

Both must print the same `SHA256:...` value, and that value must appear next to the key listed at <https://github.com/settings/keys>.

#### 3.6.4 Removing keys from the agent

An agent holds a key until you remove it or the process dies, which matters when you are switching between accounts. To drop a single key:

```bash
ssh-add -d ~/.ssh/id_ed25519
```

To empty the agent completely:

```bash
ssh-add -D
```

1. `-d` removes one key.
2. `-D` removes every key.
3. `ssh-add -x` and `ssh-add -X` lock and unlock the agent with a password.

---

### 3.7 Register the public key with GitHub (ranked)

**Run from:** anywhere. `~/.ssh` is convenient if you want to `cat id_ed25519.pub` by short name.

```bash
cd ~/.ssh && pwd
```

Never upload the private key. Only the `.pub` file.

Print it:

```bash
cat ~/.ssh/id_ed25519.pub
```

Copy it to the clipboard:

```bash
cat ~/.ssh/id_ed25519.pub | clip.exe
```

The same thing on macOS:

```bash
pbcopy < ~/.ssh/id_ed25519.pub
```

And on Linux running X11:

```bash
xclip -sel clip < ~/.ssh/id_ed25519.pub
```

Three ways to hand that key to GitHub, ranked:

| Rank | Option | How | Notes |
|------|--------|-----|-------|
| 1 | GitHub CLI (Command Line Interface) | `gh ssh-key add ~/.ssh/id_ed25519.pub --title "gitbash-laptop"` | Fastest and scriptable, needs `gh auth login` first. Manual: <https://cli.github.com/manual/gh_ssh-key_add> |
| 2 | Web interface | <https://github.com/settings/keys> then "New SSH key" | No extra tooling, works everywhere |
| 3 | Signing key upload | `gh ssh-key add ~/.ssh/id_ed25519.pub --type signing --title "sign-laptop"` | Only needed if you also sign commits, section 5 |

Concrete CLI commands:

```bash
gh auth login
```

Upload the public key, with a title you will still recognise in a year:

```bash
gh ssh-key add ~/.ssh/id_ed25519.pub --title "gitbash-laptop"
```

Confirm GitHub actually has it:

```bash
gh ssh-key list
```

---

### 3.8 Test the connection to GitHub manually

**Run from:** anywhere. Section 3.8.4 uses `git ls-remote` with a full remote address, so even that works outside a repository.

#### 3.8.1 The canonical test

Ask GitHub who it thinks you are. The `-T` skips the pseudo terminal, which GitHub does not grant anyway:

```bash
ssh -T git@github.com
```

1. Success looks like `Hi <username>! You've successfully authenticated, but GitHub does not provide shell access.`
2. The exit code is **1** even on success, because GitHub closes the shell. That is expected, not a failure.
3. `Permission denied (publickey).` means the key GitHub saw is not one it recognises.

Capture just the greeting:

```bash
ssh -T git@github.com 2>&1 | grep "^Hi"
```

Non interactive test that fails fast instead of prompting:

```bash
ssh -o BatchMode=yes -T git@github.com
```

#### 3.8.2 Test one specific key, ignoring the agent

When you hold several keys, this proves which one GitHub accepts rather than leaving it to whichever the agent happens to offer first:

```bash
ssh -T -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes git@github.com
```

`IdentitiesOnly=yes` stops SSH offering every other key first. GitHub authenticates you as the owner of the **first** key it accepts, so without this flag you can silently connect as the wrong account.

#### 3.8.3 Verbose test, to see which key was offered and accepted

Ask SSH to narrate every key it tries. The output is long, so the filtered version below is usually the one you want:

```bash
ssh -vT git@github.com
```

Filter the output down to the interesting lines:

```bash
ssh -vT git@github.com 2>&1 | grep -Ei "offering|server accepts|authenticated|identity file"
```

1. `Offering public key: ... ED25519 SHA256:<fp> agent` shows what was tried and where it came from.
2. `Server accepts key: ...` shows the one that worked.
3. `Authenticated to github.com` confirms success.
4. Add more `v` for more detail, up to `ssh -vvvT git@github.com`.

#### 3.8.4 Test the real Git path end to end

`ssh -T` proves SSH works. This proves Git works, which is a longer chain and the one that actually fails in practice:

```bash
git ls-remote git@github.com:<owner>/<repo>.git | head -3
```

This exercises Git plus SSH plus your key without cloning anything.

#### 3.8.5 If port 22 is blocked (corporate network, hotel WiFi)

Test the GitHub fallback endpoint on port 443:

```bash
ssh -T -p 443 git@ssh.github.com
```

If that works, make it permanent in `~/.ssh/config`:

```sshconfig
Host github.com
  HostName ssh.github.com
  Port 443
  User git
```

Raw reachability check using the bash TCP (Transmission Control Protocol) pseudo device:

```bash
timeout 5 bash -c 'cat < /dev/null > /dev/tcp/github.com/22' && echo "port 22 open" || echo "port 22 blocked"
```

Fallback if `/dev/tcp` is unavailable:

```bash
curl -sv --max-time 5 telnet://github.com:22 2>&1 | head -3
```

---

### 3.9 Verify you are talking to the real GitHub

**Run from:** anywhere. `~/.ssh` is convenient because `known_hosts` lives there.

On first connect SSH asks you to trust a host key (TOFU, Trust On First Use). Verify the fingerprint instead of typing `yes` blindly.

GitHub published host key fingerprints:

1. **Ed25519**: `SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU`
2. **RSA**: `SHA256:uNiVztksCsDhcc0u9e8BujQXVUpKZIDTMczCvj3tD2s`
3. **ECDSA**: `SHA256:p2QAMXNIC1TJYWeIOttrVc98/R1BUFWu3/LiyKgUfQM`

Confirm the live values yourself from the GitHub metadata API (Application Programming Interface):

```bash
curl -s https://api.github.com/meta | jq '.ssh_key_fingerprints'
```

Without `jq` installed, which is the default in Git Bash:

```bash
curl -s https://api.github.com/meta | grep -A4 ssh_key_fingerprints
```

Fingerprint the host key your machine actually sees, and compare it to the list above:

```bash
ssh-keyscan github.com 2>/dev/null | ssh-keygen -lf -
```

Inspect what is already pinned in `known_hosts`:

```bash
ssh-keygen -F github.com
```

Remove a stale or suspicious entry so it can be trusted again:

```bash
ssh-keygen -R github.com
```

Reference: <https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints>

---

### 3.10 The `~/.ssh/config` file

**Run from:** `~/.ssh`, since that is where the file belongs.

```bash
cd ~/.ssh && pwd
```

#### 3.10.1 What this file is and who reads it

`~/.ssh/config` is a per user settings file for the **SSH client**. It maps a host you type on the command line to the options SSH should use for it, so that `ssh -T -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes git@github.com` collapses down to `ssh -T git@github.com`. Nothing else changes: the file only stores flags you would otherwise type every time.

The part worth being precise about is who actually reads it, because the name invites the wrong guess:

| Program | Reads `~/.ssh/config`? | What it does |
|---------|------------------------|--------------|
| `ssh` | **Yes** | The only program here that parses the file. `scp` and `sftp` inherit it because they run `ssh`. |
| `ssh-agent` | **No** | It is a key store with no idea what a host is. It holds decrypted keys and answers requests from `ssh`. |
| `ssh-add` | **No** | It talks to the agent over `SSH_AUTH_SOCK`. Its manual lists only the default key files, no config file. |
| `git` | **Indirectly** | Git does not speak SSH itself, it runs `ssh`, so whatever the file says applies to `git push` too. |

This explains a line that otherwise looks contradictory. `AddKeysToAgent yes` sits in the client config, yet the agent never reads it. What happens is that `ssh` reads the directive and then pushes the key into the agent on your behalf. Every interaction with the agent goes through `ssh`, never the other way round.

Two behaviours will eventually catch you out, so they are worth knowing now rather than debugging later:

1. **First match wins, not last.** SSH takes its settings from the command line first, then this file, then `/etc/ssh/ssh_config`, and for any keyword the **first** value it obtains is the one used. This is the opposite of most configuration formats. A `Host *` block placed at the top of the file therefore silences every more specific block below it, so keep general blocks at the bottom.
2. **Permissions are enforced.** The file must be readable and writable by you and not writable by anyone else, which is why `chmod 600` appears below. SSH refuses to use a config it considers too open.

Full option reference, one entry per keyword: <https://man.openbsd.org/ssh_config.5>. The client that reads it is documented at <https://man.openbsd.org/ssh.1>, and the agent it hands keys to at <https://man.openbsd.org/ssh-agent.1>.

#### 3.10.2 Create the file

Write the whole block in one go:

```bash
cat >> ~/.ssh/config <<'EOF'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
  AddKeysToAgent yes
  ServerAliveInterval 60
EOF
chmod 600 ~/.ssh/config
```

Or edit it by hand:

```bash
nano ~/.ssh/config
```

What each line in that block is doing:

1. `Host github.com` opens the block. Everything indented under it applies when the address you typed matches this pattern.
2. `HostName github.com` is the address SSH actually connects to. It is the same here, but it is what makes host aliases possible in section 4.
3. `User git` is the SSH username, which for GitHub is always the literal word `git`. Your GitHub account is identified by the key, not by this name.
4. `IdentityFile` picks the key.
5. `IdentitiesOnly yes` offers only that key, avoiding wrong account logins and `Too many authentication failures`.
6. `AddKeysToAgent yes` loads the key into the agent on first use, so you stop running `ssh-add` by hand.
7. `ServerAliveInterval 60` keeps long pushes from being dropped by a firewall.

#### 3.10.3 Confirm SSH agrees with you

Reading the file back tells you what you wrote, not what SSH concluded, and those differ whenever a `Host *` block matched first. Ask SSH to resolve the settings without connecting to anything:

```bash
ssh -G github.com | grep -E "^(hostname|port|user|identityfile|identitiesonly|addkeystoagent)"
```

That prints the fully resolved settings SSH will use, including which `identityfile` wins. If a value here is not the one you just wrote, something earlier in the file matched first.

---

### 3.11 Make Git actually use the key

**Run from: inside the repository you want to change.** This is the one section where the directory genuinely matters, because `git remote` only works inside a work tree. For example:

```bash
cd /c/git/misc && pwd
```

Confirm you really are in a repository before running anything else here:

```bash
git rev-parse --show-toplevel
```

An error saying `not a git repository` means you are in the wrong directory. Two commands are exceptions. Anything using `git config --global` works from anywhere, because it writes to `~/.gitconfig`. And `git clone` in section 3.11.2 is run from the parent directory where you want the new repository to appear, for example:

```bash
cd /c/git && pwd
```

#### 3.11.1 Point an existing repository at SSH instead of HTTPS

A repository cloned over HTTPS (HyperText Transfer Protocol Secure) keeps using HTTPS forever, no matter how well your key works. Check what the remote is set to:

```bash
git remote -v
```

If it starts with `https://`, switch it to the SSH address:

```bash
git remote set-url origin git@github.com:<owner>/<repo>.git
```

#### 3.11.2 Clone with SSH from the start

Copying the SSH address rather than the HTTPS one avoids the previous step entirely:

```bash
git clone git@github.com:<owner>/<repo>.git
```

#### 3.11.3 Force a specific key for one repository only

Run this inside the repository and without `--global`, so it is written to that repository's own config and cannot affect anything else:

```bash
git config core.sshCommand "ssh -i ~/.ssh/id_ed25519_work -o IdentitiesOnly=yes"
```

#### 3.11.4 See exactly what Git does over SSH

Wrap one invocation so SSH reports what it offered, without changing any stored setting:

```bash
GIT_SSH_COMMAND="ssh -v" git ls-remote git@github.com:<owner>/<repo>.git 2>&1 | grep -Ei "offering|accepts|authenticated"
```

`GIT_SSH_COMMAND` is the cleanest way to debug, because it changes only that one command instead of your global config.

---

## 4. Multiple GitHub accounts or keys

**Run from:** `~/.ssh` to edit the config, then from wherever you keep your repositories to clone.

```bash
cd ~/.ssh && pwd
```

A single key cannot be attached to two GitHub accounts, so use one key per account plus a host alias in `~/.ssh/config`:

```sshconfig
Host github-personal
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_personal
  IdentitiesOnly yes

Host github-work
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_work
  IdentitiesOnly yes
```

Use the alias in place of the hostname:

```bash
ssh -T git@github-personal
```

Then the other one:

```bash
ssh -T git@github-work
```

Clone through the alias so the right key is used from the first command:

```bash
git clone git@github-work:<org>/<repo>.git
```

Each test should greet you with the matching username.

---

## 5. Optional: sign commits with the same SSH key

**Run from:** anywhere for the `git config --global` lines, then inside a repository for the `git log` verification at the end.

```bash
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub
git config --global commit.gpgsign true
```

Upload the same public key a second time, this time as a signing key:

```bash
gh ssh-key add ~/.ssh/id_ed25519.pub --type signing --title "sign-laptop"
```

Verify the most recent commit is signed:

```bash
git log --show-signature -1
```

Reference: <https://docs.github.com/en/authentication/managing-commit-signature-verification/telling-git-about-your-signing-key>

---

## 6. File permissions

**Run from:** `~/.ssh`.

```bash
cd ~/.ssh && pwd
```

SSH refuses to use a private key that other users can read:

```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_ed25519 ~/.ssh/config
chmod 644 ~/.ssh/id_ed25519.pub ~/.ssh/known_hosts
```

Check the result:

```bash
ls -l ~/.ssh
```

Symptom of wrong permissions: `WARNING: UNPROTECTED PRIVATE KEY FILE!` followed by the key being ignored. If `chmod` does not settle it, the simplest cure is to generate a fresh key directly in `~/.ssh` rather than copying one in from elsewhere.

---

## 7. Troubleshooting matrix

Find the symptom in the first column, run the command in the third to confirm the cause, then apply the fix. The symptoms are written as the error text you will actually see:

| Symptom | Likely cause | Command that confirms it | Fix |
|---------|--------------|--------------------------|-----|
| `Permission denied (publickey)` | Key not offered, or not registered | `ssh -vT git@github.com` | Check `ssh-add -l`, compare the fingerprint with <https://github.com/settings/keys> |
| `The agent has no identities.` | Agent is empty | `ssh-add -l` | `ssh-add ~/.ssh/id_ed25519` |
| `Could not open a connection to your authentication agent.` | No agent in this shell | `echo $SSH_AUTH_SOCK` | `eval "$(ssh-agent -s)"`, then section 3.4.2 |
| Agent forgotten in every new Git Bash window | Each window spawns its own agent | `ps aux \| grep [s]sh-agent` shows several | The `~/.bashrc` block, section 3.4.2 |
| Passphrase prompted on every `git push` | Git is calling a different ssh client than the one your agent belongs to | `git config --global --get core.sshCommand` | `git config --global --unset core.sshCommand` |
| `Too many authentication failures` | Agent offers many keys, the server cuts you off | `ssh -vT git@github.com` | Add `IdentitiesOnly yes` to `~/.ssh/config` |
| Greeted as the wrong username | Wrong key matched first | `ssh -T git@github.com` | Host aliases, section 4 |
| `Host key verification failed` | Host key changed or `known_hosts` is stale | `ssh-keygen -F github.com` | Verify the fingerprint (section 3.9), then `ssh-keygen -R github.com` |
| `Connection timed out` on port 22 | Network blocks SSH | The `/dev/tcp` check in section 3.8.5 | Use port 443, section 3.8.5 |
| `UNPROTECTED PRIVATE KEY FILE` | Permissions too open | `ls -l ~/.ssh/id_ed25519` | Section 6 |
| `ssh-add` reports `Invalid format` | Key file mangled by an editor, or it is a PuTTY `.ppk` | `ssh-keygen -l -f ~/.ssh/id_ed25519` | Regenerate, or convert the `.ppk` with PuTTYgen |
| Command hangs with no prompt | Git Bash TTY (TeleTYpe) issue | n/a | Prefix with `winpty` |
| A path argument gets rewritten oddly | MSYS2 path conversion | n/a | Prefix with `MSYS_NO_PATHCONV=1` |
| `git push` fails but `ssh -T` works | The remote is still HTTPS | `git remote -v` | Section 3.11.1 |

---

## 8. Full verification checklist

**Run from:** anywhere, `cd ~` is a fine default.

Paste the whole block into Git Bash. Every line should pass before you call it done.

```bash
ssh -V
command -v ssh
echo "SSH_AUTH_SOCK=${SSH_AUTH_SOCK:-<none>}"
ps aux | grep -i "[s]sh-agent"
ssh-add -l; echo "ssh-add exit: $?"
ssh-keygen -l -f ~/.ssh/id_ed25519.pub
ssh -G github.com | grep -E "^(hostname|port|identityfile|identitiesonly)"
ssh-keygen -F github.com | head -1
ssh-keyscan github.com 2>/dev/null | ssh-keygen -lf -
ssh -T git@github.com
git config --global --get core.sshCommand
```

---

## 9. Cheat sheet

Once the setup works, this is the only section you should need again:

| Task | Command |
|------|---------|
| Generate key | `ssh-keygen -t ed25519 -C "email"` |
| Show public key | `cat ~/.ssh/id_ed25519.pub` |
| Copy public key | `cat ~/.ssh/id_ed25519.pub \| clip.exe` |
| Fingerprint of a key file | `ssh-keygen -l -f ~/.ssh/id_ed25519.pub` |
| Start agent | `eval "$(ssh-agent -s)"` |
| Stop agent | `ssh-agent -k` |
| Is this shell agent aware | `echo $SSH_AUTH_SOCK` |
| Is an agent process alive | `ps aux \| grep [s]sh-agent` |
| Add key | `ssh-add ~/.ssh/id_ed25519` |
| Add key for 8 hours | `ssh-add -t 8h ~/.ssh/id_ed25519` |
| List loaded fingerprints | `ssh-add -l` |
| List loaded public keys | `ssh-add -L` |
| Remove one key / all keys | `ssh-add -d ~/.ssh/id_ed25519` / `ssh-add -D` |
| Test GitHub auth | `ssh -T git@github.com` |
| Verbose test | `ssh -vT git@github.com` |
| Test one specific key | `ssh -T -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes git@github.com` |
| Test port 443 fallback | `ssh -T -p 443 git@ssh.github.com` |
| Debug what Git does | `GIT_SSH_COMMAND="ssh -v" git ls-remote git@github.com:o/r.git` |
| Resolved SSH config | `ssh -G github.com` |
| Host key fingerprint seen | `ssh-keyscan github.com \| ssh-keygen -lf -` |
| Forget a host key | `ssh-keygen -R github.com` |
| Change passphrase | `ssh-keygen -p -f ~/.ssh/id_ed25519` |
| Rebuild `.pub` from private | `ssh-keygen -y -f ~/.ssh/id_ed25519 > ~/.ssh/id_ed25519.pub` |
| Keys registered on GitHub | `gh ssh-key list` |
| Upload key to GitHub | `gh ssh-key add ~/.ssh/id_ed25519.pub --title "name"` |
| Switch remote to SSH | `git remote set-url origin git@github.com:<owner>/<repo>.git` |
| Where am I | `pwd` |

---

## 10. Terminology

Every acronym is also expanded where it first appears, so you can read straight through without coming here. This section is for looking one up later.


1. **SSH** = Secure Shell, the protocol Git uses over port 22 for authenticated pushes and pulls.
2. **Key pair** = a private key (secret, stays on your machine) and a public key (`.pub`, safe to publish).
3. **`ssh-agent`** = a background process that holds your decrypted private key in memory so you type the passphrase once per session.
4. **Ed25519** = Edwards curve Digital Signature Algorithm, 255 bit curve. Modern default key type.
5. **RSA** = Rivest Shamir Adleman, the legacy key type, still accepted at 4096 bits.
6. **FIDO2** = Fast IDentity Online v2, the standard behind hardware security keys such as YubiKey.
7. **CLI** = Command Line Interface. **`gh`** = the official GitHub CLI.
8. **PAT** = Personal Access Token, the HTTPS (HyperText Transfer Protocol Secure) alternative to SSH keys.
9. **TOFU** = Trust On First Use, the model where SSH remembers a server host key the first time you connect.
10. **known_hosts** = `~/.ssh/known_hosts`, the local record of server host keys SSH has accepted.
11. **MSYS2** = the Unix compatibility layer Git Bash is built on. It is why `~` and `/c/...` paths work.

---

## 11. References (every link checked, HTTP 200)

Every link below was fetched and returned HTTP (HyperText Transfer Protocol) status 200.

1. Generating a new SSH key and adding it to the `ssh-agent`: <https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent>
2. Testing your SSH connection: <https://docs.github.com/en/authentication/connecting-to-github-with-ssh/testing-your-ssh-connection>
3. GitHub SSH key fingerprints: <https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints>
4. Working with SSH key passphrases: <https://docs.github.com/en/authentication/connecting-to-github-with-ssh/working-with-ssh-key-passphrases>
5. Telling Git about your signing key: <https://docs.github.com/en/authentication/managing-commit-signature-verification/telling-git-about-your-signing-key>
6. `gh ssh-key add` manual: <https://cli.github.com/manual/gh_ssh-key_add>
7. Your registered SSH keys: <https://github.com/settings/keys>
8. GitHub metadata API, live fingerprints and IP (Internet Protocol) ranges: <https://api.github.com/meta>
9. `ssh_config` manual, every option for `~/.ssh/config`: <https://man.openbsd.org/ssh_config.5>
10. `ssh` manual, the client that reads that file: <https://man.openbsd.org/ssh.1>
11. `ssh-agent` manual, the key store it hands keys to: <https://man.openbsd.org/ssh-agent.1>
