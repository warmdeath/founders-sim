"""The bash curriculum: one lesson per command/concept, in teaching order.

Each lesson becomes a Notebook entry the first time the player uses the
command, and also provides the `man` page. `tip` is real-world advice for
working with coding agents in a terminal.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Lesson:
    id: str             # the command name, or a concept id like "pipe"
    title: str
    level: int          # 1..7 teaching stage
    what: str
    examples: list[tuple[str, str]]
    tip: str
    try_it: str         # a command worth typing right now in the game
    man: str = ""


LEVELS = {
    1: "Finding your way: pwd, ls, cd, cat",
    2: "Looking closer: ls flags, paths, less, head, tail",
    3: "Making and moving things: mkdir, touch, cp, mv, rm",
    4: "Writing text: echo and redirection",
    5: "Combining commands: pipes, grep, wc, sort",
    6: "Finding and remembering: find, history, Tab, man",
    7: "Power tools: variables, permissions, scripts",
}

LESSONS: dict[str, Lesson] = {}


def L(id, title, level, what, examples, tip, try_it, man=""):
    LESSONS[id] = Lesson(id, title, level, what, examples, tip, try_it, man)


def _man(name, synopsis, description, options=(), examples=()):
    out = [f"NAME\n       {name}", f"\nSYNOPSIS\n       {synopsis}", f"\nDESCRIPTION\n       {description}"]
    if options:
        out.append("\nOPTIONS")
        out += [f"       {flag}\n              {text}" for flag, text in options]
    if examples:
        out.append("\nEXAMPLES")
        out += [f"       $ {cmd}\n              {text}" for cmd, text in examples]
    return "\n".join(out)


# ------------------------------------------------------------------ level 1
L("pwd", "pwd - where am I?", 1,
  "Prints the 'working directory': the folder your shell is currently standing in. Every relative path starts from here.",
  [("pwd", "prints e.g. /home/founder/company")],
  "Coding agents also have a working directory. When an agent says a file is missing, the first question is: which directory was it in?",
  "pwd",
  _man("pwd - print name of current/working directory", "pwd",
       "Print the full filename of the current working directory."))
L("ls", "ls - what is here?", 1,
  "Lists the contents of a directory. Without arguments: the current directory.",
  [("ls", "list the current directory"), ("ls inbox", "list another directory"),
   ("ls inbox product", "list several")],
  "Before asking an agent to change a project, `ls` around yourself - you can only direct what you understand.",
  "ls",
  _man("ls - list directory contents", "ls [OPTION]... [FILE]...",
       "List information about the FILEs (the current directory by default). Entries are sorted alphabetically.",
       [("-l", "use a long listing format (permissions, size, date)"),
        ("-a", "do not ignore entries starting with . (hidden files)"),
        ("-h", "with -l, print sizes like 1.2K"), ("-t", "sort by time, newest first"),
        ("-r", "reverse order while sorting"), ("-R", "list subdirectories recursively"),
        ("-1", "list one file per line"), ("-S", "sort by file size, largest first")],
       [("ls -la", "long listing including hidden files"), ("ls -lt inbox", "newest emails first")]))
L("cd", "cd - move around", 1,
  "Changes the working directory. `cd` alone takes you home.",
  [("cd product", "go into product (relative to where you are)"), ("cd ..", "go up one level"),
   ("cd", "go to your home directory"), ("cd -", "go back to the previous directory")],
  "Agents work in the directory you start them in. Start them at the project root, not in a random subfolder.",
  "cd inbox",
  _man("cd - change the shell working directory", "cd [DIR]",
       "Change the current directory to DIR. The default DIR is the value of the HOME shell variable. "
       "`cd -` changes to the previous directory ($OLDPWD)."))
L("cat", "cat - read a file", 1,
  "Prints a file's contents to the screen. (The name comes from 'concatenate': it can join several files.)",
  [("cat inbox/001_welcome.txt", "read one file"), ("cat a.txt b.txt", "print both, one after another"),
   ("cat -n file", "with line numbers")],
  "Reading is free and safe. Before trusting an agent's summary of a file, `cat` the file itself.",
  "cat inbox/001_welcome.txt",
  _man("cat - concatenate files and print on the standard output", "cat [OPTION]... [FILE]...",
       "Concatenate FILE(s) to standard output. With no FILE, read standard input.",
       [("-n", "number all output lines")]))

# ------------------------------------------------------------------ level 2
L("ls_flags", "ls -l and ls -a - the details", 2,
  "Flags (options) change what a command does. `-l` = long format: permissions, owner, size, date. `-a` = all, including hidden 'dotfiles' whose names start with a dot. Flags combine: `ls -la`.",
  [("ls -l finance", "sizes and dates of the finance files"), ("ls -a ~", "reveals hidden files like .bashrc"),
   ("ls -lt inbox", "sorted by time, newest first")],
  "Project settings usually live in dotfiles (.env, .gitignore, .claude/). If an agent 'can't find the config', look with ls -a.",
  "ls -la ~")
L("paths", "Paths: ., .., ~, absolute and relative", 2,
  "A path says where a file is. Absolute paths start at the root `/` and work from anywhere. Relative paths start from your working directory. `.` = here, `..` = one level up, `~` = your home directory.",
  [("cd /home/founder/company", "absolute: works from anywhere"), ("cd ../finance", "relative: up one, then into finance"),
   ("cat ~/company/inbox/001_welcome.txt", "~ expands to /home/founder"), ("cat ./notes.txt", "./ = in the current directory")],
  "When you give an agent a file to read, a path relative to the project root (src/app.py) is clearest. Agents confuse themselves with wrong relative paths just like people do.",
  "cd ~ && pwd")
L("less", "less - read long files comfortably", 2,
  "Shows a file one screen at a time. In real less: Space = next page, b = back, /word = search, q = quit.",
  [("less finance/metrics.csv", "page through a long file"), ("man ls | less", "page through any long output")],
  "Agent logs get long. `less` (with /search) is how you read a 5,000-line log without drowning.",
  "less finance/metrics.csv",
  _man("less - display a file one screen at a time", "less [FILE]...",
       "Less is a pager: it shows text one screenful at a time. Space/Enter: forward. b: back. /pattern: search. q: quit. "
       "(Simulated here: Enter for the next page, q to quit.)"))
L("head", "head - the first lines", 2,
  "Prints the first 10 lines of a file. `-n 3` (or `-3`) chooses how many.",
  [("head finance/metrics.csv", "first 10 lines"), ("head -n 1 finance/metrics.csv", "just the header row")],
  "`head` is the quick way to see what kind of file something is before feeding the whole thing to an agent's limited context.",
  "head -n 3 finance/metrics.csv",
  _man("head - output the first part of files", "head [-n NUM] [FILE]...",
       "Print the first 10 lines of each FILE to standard output. With more than one FILE, precede each with a header.",
       [("-n NUM", "print the first NUM lines instead of the first 10")]))
L("tail", "tail - the last lines", 2,
  "Prints the last 10 lines. Since logs and CSVs grow at the bottom, the newest information is at the tail.",
  [("tail -n 4 finance/metrics.csv", "the last four weeks"), ("tail -n +2 file", "everything from line 2 on (skip a header)")],
  "The end of a test log is where the summary and the failures are. In a real terminal `tail -f log` follows a file live while an agent works.",
  "tail -n 4 finance/metrics.csv",
  _man("tail - output the last part of files", "tail [-n NUM] [FILE]...",
       "Print the last 10 lines of each FILE to standard output.",
       [("-n NUM", "output the last NUM lines"), ("-n +NUM", "output starting with line NUM")]))

# ------------------------------------------------------------------ level 3
L("mkdir", "mkdir - make a directory", 3,
  "Creates a new directory. `-p` also creates missing parents and doesn't complain if it exists.",
  [("mkdir reports", "one directory"), ("mkdir -p inbox/archive/2026", "nested directories in one go")],
  "A tidy folder structure is context for agents: they infer what goes where from names. Mess in, mess out.",
  "mkdir inbox/archive",
  _man("mkdir - make directories", "mkdir [-p] DIRECTORY...",
       "Create the DIRECTORY(ies), if they do not already exist.",
       [("-p", "no error if existing, make parent directories as needed")]))
L("touch", "touch - create an empty file", 3,
  "Creates an empty file (or updates the timestamp of an existing one).",
  [("touch notes.txt", "create an empty notes.txt")],
  "Handy for placeholder files. Many tools also react to special empty files simply existing.",
  "touch product/todo.txt",
  _man("touch - change file timestamps", "touch FILE...",
       "Update the modification time of each FILE to the current time. A FILE that does not exist is created empty."))
L("cp", "cp - copy", 3,
  "Copies a file: `cp SOURCE DESTINATION`. Use `-r` to copy a whole directory.",
  [("cp product/specs/a.md product/specs/b.md", "copy a spec as a starting point"),
   ("cp -r product backup", "copy a directory and everything inside")],
  "Before letting an agent rewrite something important, make a copy (in real projects: a git commit). Cheap insurance.",
  "cp investors/angel_rossi.txt ~/rossi_backup.txt",
  _man("cp - copy files and directories", "cp [-r] SOURCE... DEST",
       "Copy SOURCE to DEST, or multiple SOURCE(s) to directory DEST.",
       [("-r, -R", "copy directories recursively")]))
L("mv", "mv - move or rename", 3,
  "Moves a file to another place - or renames it (renaming IS moving to a new name).",
  [("mv inbox/001_welcome.txt inbox/archive/", "move into a directory"), ("mv draft.md final.md", "rename")],
  "Renames ripple: other files may refer to the old name. Agents are good at updating references if you tell them about the rename.",
  "mv inbox/001_welcome.txt inbox/archive/",
  _man("mv - move (rename) files", "mv SOURCE... DEST",
       "Rename SOURCE to DEST, or move SOURCE(s) to directory DEST."))
L("rm", "rm - remove (no undo!)", 3,
  "Deletes files. There is NO trash can in a shell: gone is gone. `-r` deletes directories recursively.",
  [("rm notes.txt", "delete a file"), ("rm -r old_stuff", "delete a directory and its contents")],
  "`rm -rf` is the most dangerous habit to give an agent. Real agent tools ask permission before destructive commands - read what you approve. Never approve an rm with a path you don't understand.",
  "rm product/todo.txt",
  _man("rm - remove files or directories", "rm [-r] [-f] FILE...",
       "Remove each FILE. By default, it does not remove directories.",
       [("-r, -R", "remove directories and their contents recursively"),
        ("-f", "ignore nonexistent files, never prompt")]))

# ------------------------------------------------------------------ level 4
L("echo", "echo - print text", 4,
  "Prints its arguments. Useful with variables and - above all - with redirection to write text into files.",
  [("echo hello", "prints hello"), ("echo \"Cash: $HOME\"", "double quotes: variables expand"),
   ("echo 'Cash: $HOME'", "single quotes: printed literally")],
  "Quoting matters whenever text contains spaces or $ signs. A surprising amount of 'the agent's command failed' is a quoting problem.",
  "echo \"I am $USER\"",
  _man("echo - display a line of text", "echo [-n] [-e] [STRING]...",
       "Echo the STRING(s) to standard output.",
       [("-n", "do not output the trailing newline"), ("-e", "enable interpretation of backslash escapes like \\n")]))
L("redirect", "> - send output into a file", 4,
  "`command > file` writes the command's output into a file instead of the screen. It REPLACES the file's contents.",
  [("echo '# Ideas' > product/notes.md", "create/overwrite a file with one line"),
   ("ls customers/notes > list.txt", "save any command's output")],
  "`>` silently overwrites. One wrong redirect can wipe a file - one more reason to keep work under version control.",
  "echo 'my first file' > ~/hello.txt")
L("redirect_append", ">> - append to a file", 4,
  "`command >> file` adds the output to the END of the file, keeping what is there.",
  [("echo '- sync must work offline' >> product/specs/offline.md", "add a line to a spec"),
   ("date >> log.txt", "keep a running log")],
  "Appending a line is the quickest way to add a rule to a project memory file like CLAUDE.md or AGENTS.md when an agent keeps making the same mistake.",
  "echo 'second line' >> ~/hello.txt")

# ------------------------------------------------------------------ level 5
L("pipe", "| - pipes: connect commands", 5,
  "`a | b` feeds the output of command a into command b as its input. Small tools, chained, answer big questions. This is THE idea of the unix shell.",
  [("ls inbox | wc -l", "how many emails?"), ("cat finance/metrics.csv | tail -n 3", "the last three rows"),
   ("grep -l pricing customers/notes/* | wc -l", "how many notes mention pricing?")],
  "Agents chain commands with pipes constantly. If you can read a pipeline, you can check what an agent is about to run before approving it.",
  "ls inbox | wc -l")
L("grep", "grep - search inside files", 5,
  "Prints the lines that match a pattern. The single most useful search tool there is.",
  [("grep pricing customers/notes/maria.md", "lines containing 'pricing'"),
   ("grep -i pricing customers/notes/*", "-i ignores upper/lower case; * = all files"),
   ("grep -r FAIL agents/runs", "-r searches a whole directory tree"),
   ("grep -c FAIL tests.log", "-c counts matching lines"), ("grep -l pricing customers/notes/*", "-l lists only file names"),
   ("grep -v PASS tests.log", "-v inverts: lines NOT matching"), ("grep -n TODO spec.md", "-n shows line numbers")],
  "grep is how agents find things in a codebase - and how you check their claims. 'All tests pass'? `grep -c FAIL tests.log` settles it in a second.",
  "grep -ri pricing customers/notes",
  _man("grep - print lines that match patterns", "grep [OPTION]... PATTERN [FILE]...",
       "Search for PATTERN in each FILE (or standard input). PATTERN is a basic regular expression.",
       [("-i", "ignore case"), ("-v", "select non-matching lines"), ("-c", "print only a count of matching lines"),
        ("-n", "prefix each line with its line number"), ("-l", "print only names of files with matches"),
        ("-r", "search directories recursively"), ("-w", "match whole words only"),
        ("-E", "PATTERN is an extended regular expression (a|b, x+)"), ("-o", "print only the matched parts")],
       [("grep -rn 'pricing' customers", "search a tree, show file and line"),
        ("grep -E 'FAIL|ERROR' tests.log", "either word")]))
L("wc", "wc - count lines, words, bytes", 5,
  "Counts. `wc -l` (lines) is the one you'll use daily, usually at the end of a pipe.",
  [("wc -l finance/metrics.csv", "lines in a file"), ("ls inbox | wc -l", "count things by counting lines"),
   ("wc -w product/specs/offline.md", "word count")],
  "Context windows are finite: `wc -l` tells you whether a file is 50 lines or 50,000 before you hand it to an agent.",
  "wc -l finance/metrics.csv",
  _man("wc - print newline, word, and byte counts", "wc [-l] [-w] [-c] [FILE]...",
       "Print newline, word, and byte counts for each FILE, and a total line if more than one FILE is specified.",
       [("-l", "print the newline counts"), ("-w", "print the word counts"), ("-c", "print the byte counts")]))
L("sort", "sort - put lines in order", 5,
  "Sorts lines alphabetically. `-n` sorts numerically, `-r` reverses, `-t, -k2` sorts a CSV by its 2nd column, `-u` drops duplicates.",
  [("sort names.txt", "alphabetical"), ("sort -t, -k3 -n finance/metrics.csv", "CSV by 3rd column, numerically"),
   ("sort -t, -k3 -nr finance/metrics.csv | head -n 1", "the row with the highest value in column 3")],
  "sort | uniq -c | sort -nr is the classic 'what occurs most often?' pipeline - great for summarising errors in a log.",
  "sort -t, -k3 -nr finance/metrics.csv | head -n 3",
  _man("sort - sort lines of text files", "sort [OPTION]... [FILE]...",
       "Write sorted concatenation of all FILE(s) to standard output.",
       [("-n", "compare according to string numerical value"), ("-r", "reverse the result of comparisons"),
        ("-u", "output only the first of equal lines"), ("-k N", "sort by field N"),
        ("-t SEP", "use SEP as the field separator")]))
L("uniq", "uniq - collapse repeated lines", 5,
  "Removes ADJACENT duplicate lines (so sort first). `-c` prefixes each line with how often it occurred.",
  [("sort list.txt | uniq", "unique lines"), ("grep -h '^Type:' investors/*.txt | sort | uniq -c", "count investors per type")],
  "Counting categories with sort | uniq -c is a one-line data analysis. No spreadsheet needed.",
  "grep -h '^Type:' investors/*.txt | sort | uniq -c",
  _man("uniq - report or omit repeated lines", "uniq [-c] [-d] [-u] [FILE]",
       "Filter adjacent matching lines from input, writing to output.",
       [("-c", "prefix lines by the number of occurrences"), ("-d", "only print duplicate lines"),
        ("-u", "only print unique lines")]))
L("cut", "cut - pick columns", 5,
  "Extracts columns from each line. `-d,` sets the delimiter, `-f2` picks field 2.",
  [("cut -d, -f1,3 finance/metrics.csv", "week and MRR columns"), ("cut -d, -f3 finance/metrics.csv | tail -n 1", "latest MRR")],
  "CSV in, one column out: a tiny, exact way to give an agent just the data it needs.",
  "cut -d, -f1,3 finance/metrics.csv | tail -n 5",
  _man("cut - remove sections from each line of files", "cut -d DELIM -f LIST [FILE]...",
       "Print selected parts of lines from each FILE to standard output.",
       [("-d DELIM", "use DELIM instead of TAB for field delimiter"),
        ("-f LIST", "select only these fields, e.g. 1,3 or 2-4")]))

# ------------------------------------------------------------------ level 6
L("find", "find - search for files", 6,
  "Walks a directory tree and prints files that match tests - by name, by type...",
  [("find . -name '*.md'", "all markdown files below here (quote the pattern!)"),
   ("find customers -type f", "only files"), ("find . -type d -name 'run_*'", "directories named run_*"),
   ("find product -name '*.md' | wc -l", "count them")],
  "grep searches INSIDE files; find searches for the files themselves. Agents use both to orient themselves in a big repository.",
  "find . -name '*.md' | wc -l",
  _man("find - search for files in a directory hierarchy", "find [PATH...] [EXPRESSION]",
       "Search the directory tree rooted at each PATH and print the files matching EXPRESSION.",
       [("-name PATTERN", "base of file name matches shell PATTERN (quote it)"), ("-iname PATTERN", "like -name, case-insensitive"),
        ("-type f|d", "file is a regular file (f) or directory (d)"), ("-maxdepth N", "descend at most N levels")]))
L("history", "history - what did I type?", 6,
  "Lists the commands you've typed, numbered. `!!` repeats the last one, `!42` repeats number 42. Ctrl+R searches history as you type.",
  [("history", "everything"), ("history 10", "the last 10"), ("history | grep agent", "every agent command you ran")],
  "Your history is a lab notebook: when something worked, the exact command is in there. Turn the good ones into scripts.",
  "history 10",
  _man("history - display the command history list", "history [N] | history -c",
       "Display the history list with line numbers. An argument of N lists only the last N lines. -c clears the list."))
L("tab", "Tab completion", 6,
  "Press Tab to complete a command or path. If several things match, press Tab again to see the choices. It is faster AND prevents typos.",
  [("cat inb<Tab>", "completes to inbox/"), ("pitch investors/a<Tab><Tab>", "shows the matching investors")],
  "Professionals type the first letters and Tab the rest. If Tab doesn't complete, the path is probably wrong - a free error check.",
  "cat inb<Tab>")
L("up_arrow", "Up arrow and history search", 6,
  "Up arrow recalls previous commands; edit and press Enter to run again. Ctrl+R searches old commands as you type. Right arrow accepts the grey suggestion.",
  [("<Up>", "the previous command"), ("Ctrl+R then 'agent'", "find the last command containing 'agent'")],
  "Never retype a long command. Recall, tweak, rerun - the same loop you use when iterating on an agent's task.",
  "<Up>")
L("man", "man and --help - built-in documentation", 6,
  "`man ls` opens the manual page for ls. Most commands also answer `--help`. Nobody memorises flags; everybody looks them up.",
  [("man grep", "the manual for grep"), ("ls --help", "short usage help"), ("man agent", "game commands have manual pages too")],
  "Agents read --help output too - it is how they learn tools they've never seen. Good CLI tools document themselves.",
  "man grep",
  _man("man - an interface to the system reference manuals", "man COMMAND",
       "Display the manual page for COMMAND. Game commands (agent, pitch, ...) have pages too."))

# ------------------------------------------------------------------ level 7
L("variables", "Environment variables", 7,
  "Named values the shell and programs can read. `$NAME` reads one; `export NAME=value` sets one for programs you start. `env` lists them. $HOME, $USER and $PATH are standard.",
  [("echo $HOME", "read a variable"), ("export AGENT_MODEL=smart", "set one (here: your default agent model)"),
   ("env | grep AGENT", "find variables"), ("NAME=value command", "set it for one command only")],
  "Configuration and secrets (like API keys) are passed to tools through environment variables - e.g. ANTHROPIC_API_KEY. Never paste keys into code or chat; keep them in the environment or a .env file that is NOT committed.",
  "export AGENT_MODEL=smart",
  _man("export - set an environment variable", "export NAME[=VALUE]...",
       "Mark each NAME for automatic export to the environment of subsequently executed commands. "
       "See also: env (list variables), unset NAME (remove one), echo $NAME (read one)."))
L("chmod", "chmod and permissions", 7,
  "Every file has permissions for the owner (u), the group (g) and others (o): r = read, w = write, x = execute. `ls -l` shows them like -rw-r--r--. `chmod` changes them.",
  [("chmod +x weekly.sh", "make a script executable"), ("chmod 644 file", "rw-r--r-- (6=rw, 4=r, 4=r)"),
   ("chmod a-w important.md", "make a file read-only for everyone")],
  "'Permission denied' when running a script almost always means it lacks x. Agent tools have their own permission systems too: you decide which commands they may run without asking.",
  "chmod +x reports/weekly.sh",
  _man("chmod - change file mode bits", "chmod MODE FILE...",
       "Change the permissions of each FILE. MODE is octal (644, 755) or symbolic: [ugoa][+-=][rwx].",
       [("-R", "change files and directories recursively")],
       [("chmod +x script.sh", "add execute permission for everyone"), ("chmod 600 secret.txt", "only the owner may read/write")]))
L("script", "Shell scripts", 7,
  "A script is a text file of commands, run top to bottom. Start it with `#!/bin/bash`, make it executable, run it with ./name.sh. `$1` is the first argument. Loops and ifs work too.",
  [("echo 'tail -n 1 finance/metrics.csv' > weekly.sh", "write a one-line script"),
   ("chmod +x weekly.sh && ./weekly.sh", "make it executable and run it"), ("bash weekly.sh", "run without the x permission"),
   ("for f in customers/notes/*.md; do grep -c pricing $f; done", "a loop, typed directly")],
  "Anything you do twice, script. Real agent workflows are built from scripts: a test script, a deploy script, hooks. Agents can write them - you should be able to read them.",
  "nano reports/weekly.sh",
  _man("bash - run a shell script", "bash FILE [ARG]...   |   ./FILE [ARG]...",
       "Run the commands in FILE. Inside the script, $1 $2 ... are the arguments and $# their count. "
       "Supported here: variables, pipes, redirection, && ||, `for x in ...; do ...; done`, `if ...; then ...; else ...; fi`, `[ -f file ]` tests."))
L("alias", "alias - your own shortcuts", 7,
  "Defines a short name for a longer command. Real shells load aliases from ~/.bashrc at startup.",
  [("alias m='metrics'", "now `m` runs metrics"), ("alias", "list all aliases"), ("cat ~/.bashrc", "where they normally live")],
  "Keep aliases for things YOU type. For agents, prefer scripts with clear names: an agent can read a script, it can't guess your aliases.",
  "alias",
  _man("alias - define or display aliases", "alias [NAME[='VALUE']]...",
       "Without arguments, print the list of aliases. Otherwise define an alias for each NAME whose VALUE is given."))
L("xargs", "xargs - output as arguments", 7,
  "Turns its input into arguments for another command. Pipes pass TEXT; xargs turns that text into FILE NAMES to work on.",
  [("find customers -name '*.md' | xargs grep -l pricing", "search inside all files that find found"),
   ("ls inbox | xargs echo", "all names on one line")],
  "find | xargs grep is the heavy-duty version of grep -r - you will see agents use it on large codebases.",
  "find customers -name '*.md' | xargs grep -l pricing",
  _man("xargs - build and execute command lines from standard input", "xargs [COMMAND [ARG]...]",
       "Read items from standard input and execute COMMAND with them appended as arguments."))

ORDER = list(LESSONS)

# Extra man pages for commands that have no lesson of their own.
EXTRA_MAN = {
    "tree": _man("tree - list contents of directories in a tree-like format", "tree [-a] [-d] [-L LEVEL] [DIR]...",
                 "Recursively list directories as an indented tree.",
                 [("-a", "show hidden files"), ("-d", "directories only"), ("-L N", "descend only N levels")]),
    "tee": _man("tee - read from standard input and write to standard output and files", "tee [-a] FILE...",
                "Copy standard input to each FILE, and also to standard output.", [("-a", "append to the FILEs")]),
    "rmdir": _man("rmdir - remove empty directories", "rmdir DIRECTORY...", "Remove the DIRECTORY(ies), if they are empty."),
    "env": _man("env - print the environment", "env", "Print all exported environment variables as NAME=value."),
    "nano": _man("nano - small text editor", "nano FILE",
                 "Edit FILE. (Simulated: a multi-line editor opens; Esc then Enter saves, Ctrl+C cancels. "
                 "In real nano: Ctrl+O saves, Ctrl+X exits.)"),
    "tr": _man("tr - translate or delete characters", "tr SET1 SET2  |  tr -d SET1",
               "Translate characters from standard input, e.g. `tr a-z A-Z`."),
    "which": _man("which - locate a command", "which COMMAND...", "Print the full path of the program that would run."),
    "test": _man("test - check file types and compare values", "test EXPRESSION   |   [ EXPRESSION ]",
                 "Exit with status 0 if EXPRESSION is true. -f FILE: is a file. -d DIR: is a directory. -e: exists. "
                 "-z STR: empty. A = B, A != B: strings. N -gt M, -lt, -eq, -ge, -le, -ne: numbers."),
}
