# Founder's Sim

A startup-founder simulator you play inside a **simulated bash shell**.

You are an 18-year-old solo founder. Your company is a folder: emails, customer interviews, term sheets
and metrics are files you read with real commands (`ls`, `cat`, `grep`, pipes). You build the product by
directing AI agents, find customers, raise money (or don't), and try not to run out of cash or energy.

It is a learning tool first and a game second. By the end of a few runs you will know:

- **the terminal**: about 50 real bash commands and shell features (pipes, redirection, wildcards,
  quoting, scripts, permissions) and how to combine them - 38 lessons in all
- **agentic AI**: specs, context, tool use, review, tests, evals, parallel agents, guardrails, technical debt
- **startups, venture capital and corporate finance**: 191 terms, each explained when it first matters,
  with your own company's numbers, and saved in an in-game notebook

Nothing you type in the game can touch your real computer: every command works on a virtual filesystem.

---

## Lesson 0: setting up (Windows) — your first real terminal commands

The game runs in Linux. On Windows you get Linux through **WSL** (Windows Subsystem for Linux): a real
Ubuntu running inside Windows. Everything below is typed, not clicked — that is the point. Each step
tells you what the command does, so by the end of the setup you will already have used `pwd`, `ls`,
`cd`, `python3`, `pip`, `venv` and `git clone`.

Budget about 30–45 minutes, most of it waiting for downloads. You need an internet connection and an
administrator account on the PC.

### 0. Check your Windows version

WSL 2 needs **Windows 11**, or **Windows 10 version 2004 (build 19041) or newer**.
Press `Win + R`, type `winver`, press Enter. The window that opens shows your version and build.
If it is older, run Windows Update first.

### 1. Install WSL with Ubuntu

1. Click Start, type `PowerShell`, right-click **Windows PowerShell**, choose **Run as administrator**,
   and click **Yes** when Windows asks for permission.
2. Type this and press Enter:

   ```powershell
   wsl --install
   ```

   This turns on WSL and downloads Ubuntu (a popular Linux). It can take several minutes and may look
   stuck at times — let it finish. **Restart the computer** when it asks.
3. After the restart an Ubuntu window opens by itself (if it doesn't, click Start and open **Ubuntu**).
   It finishes installing, then asks you to **create a username and password** for Linux.
   - Use lowercase letters only for the username, e.g. `sara`.
   - While you type the password **nothing appears on screen — not even dots**. That is normal in
     Linux. Type it, press Enter, type it again.
   - Write the password down: you will need it for `sudo` in step 4.

**If something goes wrong**

| What you see | What to do |
|---|---|
| `wsl` is "not recognized" | Your Windows is too old — see step 0. |
| Error `0x80370102`, or "Please enable the Virtual Machine Platform" | Virtualization is turned off in your PC's firmware (BIOS/UEFI). Search the web for your PC model + "enable virtualization" (the setting is called Intel VT-x, Intel Virtualization Technology, AMD-V or SVM), turn it on, restart, and run `wsl --install` again. |
| It only printed help text, or Ubuntu is missing | Run `wsl --install -d Ubuntu` in the administrator PowerShell. |
| You forgot the Linux password | In PowerShell: `wsl -u root`, then `passwd yourname` to set a new one, then `exit`. |

### 2. Install Windows Terminal

Windows 11 already has it. On Windows 10, open the **Microsoft Store**, search for **Windows Terminal**
and install it. Open it, click the small arrow `⌄` next to the tab, and choose **Ubuntu**.
(Tip: in Terminal's Settings → Startup → Default profile, choose Ubuntu so it always opens there.)

You now see a *prompt*, something like:

```
sara@PC:~$
```

`sara` is your user, `PC` is the machine, `~` is the folder you are in (`~` means "my home folder"),
and `$` means "ready for a command". The game's prompt looks the same on purpose.

**Four keys that work differently in a terminal** — learn them now, they will save you a lot of confusion:

| Key | In the terminal |
|---|---|
| `Ctrl+C` | **Stops** the running program (it does not copy!). Use it whenever something seems stuck. |
| `Ctrl+Shift+C` / `Ctrl+Shift+V` | Copy / paste. Right-clicking also pastes in Windows Terminal. |
| `↑` (up arrow) | Brings back the previous command, so you never retype a long one. |
| `Tab` | Completes a command or file name. Type `cd fou` and press Tab. |

### 3. Your first commands

Type each line, press Enter, and read what comes back.

```bash
pwd
```

**p**rint **w**orking **d**irectory: shows which folder you are in (`/home/sara`).

```bash
ls
```

**l**i**s**t: shows what is in this folder. A fresh home folder is empty, so it prints nothing —
in Linux, "no output" usually means "it worked".

```bash
python3 --version
```

Runs the program `python3` and asks for its version. `--version` is a *flag*: an option that changes what a
command does. The game needs **Python 3.10 or newer**; current Ubuntu has it (Ubuntu 22.04 has 3.10,
24.04 has 3.12). If you see 3.8 or older, your Ubuntu is old: run `wsl --install -d Ubuntu-24.04` in
PowerShell and use that one.

### 4. Install the tools the game needs

```bash
sudo apt update
```

`apt` is Ubuntu's app store for the terminal; `update` refreshes its catalogue. `sudo` means "do this as
administrator" — it asks for the Linux password you created (again, nothing appears while you type).

```bash
sudo apt install -y git python3-venv python3-pip
```

Installs three things: `git` (downloads and tracks code), `python3-venv` (private Python environments) and
`pip` (installs Python packages). `-y` answers "yes" to the confirmation. Lots of text scrolls past; it
is done when you get your `$` prompt back.

### 5. Download the game

```bash
cd ~
```

Makes sure you are in your Linux home folder (`~`). Keep projects here rather than under `/mnt/c/...`
(your Windows drive): it is much faster and avoids permission problems.

```bash
git clone https://github.com/warmdeath/founders-sim.git
```

`git clone` copies a project ("repository") from GitHub to your computer, into a new folder.
If it asks for a username and password, the repository is private: ask its owner for access, or
download it as a ZIP from GitHub instead.

```bash
ls
```

Now `ls` shows `founders-sim`.

```bash
cd founders-sim
```

**c**hange **d**irectory: step into the folder. Your prompt changes to `~/founders-sim$`.
(`cd ..` goes back up one level; `cd` alone goes home.)

```bash
ls
```

You should see `README.md`, `founders_sim`, `tests` and a few other files.

> If the folder only contains a README, the game is still on a development branch. Run
> `git switch claude/startup-founder-simulator-fe2mgp` and `ls` again.

Want to see these files in Windows? Type `explorer.exe .` (the dot means "this folder") and a normal
Explorer window opens on them.

### 6. Create a virtual environment and install the game's packages

```bash
python3 -m venv .venv
```

Creates a *virtual environment*: a private folder (`.venv`) for this project's Python packages, so they
don't mix with the rest of the system. Its name starts with a dot, which makes it hidden: `ls` won't show
it, `ls -a` will.

```bash
source .venv/bin/activate
```

Switches this terminal to that environment. Your prompt now starts with `(.venv)`.
**You need to run this line again every time you open a new terminal.**

```bash
pip install -r requirements.txt
```

`pip` installs the packages listed in the file `requirements.txt` (`-r` = "read the list from this file").

> If you see `error: externally-managed-environment`, the environment is not active: run the `source`
> line above and try again. New Ubuntu versions refuse `pip install` outside a virtual environment on
> purpose, to protect the system's own Python.

### 7. Play

Maximise the terminal window first: the game needs at least about 110 characters of width.

```bash
python3 -m founders_sim
```

The first run is a guided tutorial. `quit` saves and leaves; the game also saves every week.

Next time, the whole routine is three commands:

```bash
cd ~/founders-sim
```

```bash
source .venv/bin/activate
```

```bash
python3 -m founders_sim
```

To get the newest version of the game later, run `git pull` inside the folder.

## Playing

| Key / command | What it does |
|---|---|
| `tutor` | what to do or learn next (your best friend) |
| `help`, `man <command>` | list commands / manual for one command |
| `status`, `metrics`, `dash` | how the company is doing (`dash` is full screen, `q` to leave) |
| `goals` | the three ways to win this run, and how far you are |
| `growth` | where customers come from and why they leave |
| `next` | end the week |
| `notebook`, `glossary` | everything you have learned / the whole curriculum |
| `quit` | save and leave (the game also autosaves every week) |
| Tab | complete a command, path or name; press again for a menu |
| ↑ / Ctrl+R | previous commands / search your history |
| → | accept the grey suggestion |

A run is one company, 60–72 weeks, roughly 3–5 hours. You win by becoming **profitable**, closing a
**priced funding round**, or being **acquired**. You lose by running out of **cash** or **energy**.

After each run you get a debrief, and the next run becomes harder and steers you toward what you have not
practised yet (a different business model, debt, B2B sales, acquisitions...). Mastering the whole
curriculum takes about 4–6 runs.

Other ways to start:

```bash
python3 -m founders_sim --new
```

Abandon the saved run and start a new one.

```bash
python3 -m founders_sim --profile
```

Show your learner profile (curriculum progress across all runs).

Your profile, save file and command history live in `~/.founders_sim/` on your real disk — the only real
files the game writes.

## Running the tests

```bash
python3 -m pytest
```

## More

- `REVIEW.md` — how the code is organised, which files to read first, design decisions, simplifications,
  and the full curriculum.
- `SPEC.md` — the original brief.
- `CLAUDE.md` — notes for AI coding agents working on this repository.
