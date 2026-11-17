# Founder's Sim

A startup-founder simulator you play inside a **simulated bash shell**.

You are an 18-year-old solo founder. Your company is a folder: emails, customer interviews, term sheets
and metrics are files you read with real commands (`ls`, `cat`, `grep`, pipes). You build the product by
directing AI agents, find customers, raise money (or don't), and try not to run out of cash or energy.

It is a learning tool first and a game second. By the end of a few runs you will know:

- **the terminal**: about 30 real bash commands and how to combine them
- **agentic AI**: specs, context, review, tests, parallel agents, technical debt
- **startups, venture capital and corporate finance**: 176 terms, each explained when it first matters,
  with your own company's numbers, and saved in an in-game notebook

Nothing you type in the game can touch your real computer: every command works on a virtual filesystem.

---

## Lesson 0: setting up (Windows) — your first real terminal commands

The game runs in Linux. On Windows you get Linux through **WSL** (Windows Subsystem for Linux).
Everything below is typed, not clicked — that is the point. Each step tells you what the command does.

### 1. Install WSL with Ubuntu

1. Click Start, type `PowerShell`, right-click **Windows PowerShell**, choose **Run as administrator**.
2. Type this and press Enter:

   ```powershell
   wsl --install
   ```

   This installs WSL and Ubuntu (a popular Linux). Restart the computer when it asks.
3. After the restart an Ubuntu window opens and asks you to **create a username and password**.
   Pick something short. While you type the password nothing appears on screen — that is normal.

### 2. Install Windows Terminal

Open the **Microsoft Store**, search for **Windows Terminal**, install it. (On Windows 11 it is already there.)
Open it, click the small arrow `v` next to the tab, and choose **Ubuntu**.

You now see a *prompt*, something like:

```
yourname@PC:~$
```

`yourname` is your user, `PC` is the machine, `~` is the folder you are in (`~` means "my home folder"),
and `$` means "ready for a command". The game's prompt looks the same on purpose.

### 3. Your first commands

Type each line, press Enter, and read what comes back.

```bash
pwd
```

**p**rint **w**orking **d**irectory: shows which folder you are in (`/home/yourname`).

```bash
ls
```

**l**i**s**t: shows what is in this folder. A fresh home folder is empty, so it prints nothing.

```bash
python3 --version
```

Runs the program `python3` and asks for its version. `--version` is a *flag*: an option that changes what a
command does. You need 3.10 or newer. Ubuntu comes with it.

### 4. Install the tools the game needs

```bash
sudo apt update
```

`apt` is Ubuntu's app store for the terminal; `update` refreshes its catalogue. `sudo` means "do this as
administrator" — it asks for the password you created.

```bash
sudo apt install -y git python3-venv python3-pip
```

Installs three things: `git` (downloads and tracks code), `python3-venv` (isolated Python environments) and
`pip` (installs Python packages). `-y` answers "yes" to the confirmation.

### 5. Download the game

```bash
git clone https://github.com/warmdeath/founders-sim.git
```

`git clone` copies a project ("repository") from GitHub to your computer, into a new folder.

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

### 7. Play

```bash
python3 -m founders_sim
```

Make the terminal window large (at least 110 columns wide). The first run is a guided tutorial.

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

---

## Playing

| Key / command | What it does |
|---|---|
| `tutor` | what to do or learn next (your best friend) |
| `help`, `man <command>` | list commands / manual for one command |
| `status`, `metrics`, `dash` | how the company is doing (`dash` is full screen, `q` to leave) |
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
