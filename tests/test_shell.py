"""The simulated shell must behave like real bash where implemented."""
from tests.helpers import make_session, run


def sh(*lines, s=None):
    s = s or make_session()
    return run(s, *lines)


def test_navigation_and_paths():
    out = sh("pwd", "cd product", "pwd", "cd ..", "cd ~", "pwd", "cd -", "cd /nope")
    assert out.splitlines()[:3] == ["/home/founder/company", "/home/founder/company/product", "/home/founder"]
    assert "/home/founder/company\n" in out
    assert "bash: cd: /nope: No such file or directory" in out


def test_ls_long_and_hidden():
    out = sh("cd ~", "ls", "ls -a", "ls -l")
    plain, all_, long_ = out.split("\n", 1)[0], out, out
    assert ".bashrc" not in plain and ".bashrc" in all_
    assert "-rw-r--r-- 1 founder founder" in long_ and "drwxr-xr-x" in long_


def test_real_error_messages():
    out = sh("cat nope", "ls nope", "rm inbox", "mkdir inbox", "cp a", "foo", "cat inbox", "rmdir inbox")
    for expected in ["cat: nope: No such file or directory", "ls: cannot access 'nope': No such file or directory",
                     "rm: cannot remove 'inbox': Is a directory", "mkdir: cannot create directory ‘inbox’: File exists",
                     "cp: missing destination file operand after 'a'", "bash: foo: command not found",
                     "cat: inbox: Is a directory", "rmdir: failed to remove 'inbox': Directory not empty"]:
        assert expected in out


def test_redirection_pipes_and_counting():
    out = sh("echo one > f.txt", "echo two >> f.txt", "echo three >> f.txt", "cat f.txt | wc -l",
             "grep -c t f.txt", "sort -r f.txt | head -n 1", "cat f.txt | grep -v two | tail -n 1", "wc -l < f.txt")
    assert out.split() == ["3", "2", "two", "three", "3"]


def test_quotes_variables_and_substitution():
    out = sh("X=5", 'echo "v=$X" \'$X\' $(echo hi) "$(echo \'a  b\')"', "export Y=1; env | grep ^Y=", "echo $?", "echo ${X}th")
    assert out.splitlines() == ["v=5 $X hi a  b", "Y=1", "0", "5th"]


def test_globs_and_find():
    out = sh("touch a1.md a2.md b.txt", "echo *.md", "ls a?.md | wc -l", "echo *.zip", "find . -maxdepth 1 -name 'a*' -type f")
    assert out.splitlines() == ["a1.md a2.md", "2", "*.zip", "./a1.md", "./a2.md"]


def test_grep_flags():
    s = make_session()
    out = sh("printf 'Pricing is high\\nno match\\nthe pricing page\\n' > n.txt", "grep -i pricing n.txt",
             "grep -n pricing n.txt", "grep -c -i PRICING n.txt", "grep -l pricing n.txt *.md", "grep zzz n.txt; echo $?", s=s)
    assert "Pricing is high\nthe pricing page\n3:the pricing page\n2\nn.txt\n" in out
    assert out.strip().endswith("1")


def test_sort_cut_uniq():
    out = sh("printf 'b,2\\na,10\\nc,1\\na,10\\n' > d.csv", "sort -t, -k2 -n d.csv | head -n 1", "cut -d, -f1 d.csv | sort | uniq -c | sort -nr | head -n 1",
             "sort -u d.csv | wc -l")
    assert out.splitlines()[0] == "c,1"
    assert out.splitlines()[1].split() == ["2", "a"]
    assert out.splitlines()[2] == "3"


def test_cp_mv_rm():
    out = sh("mkdir -p x/y", "echo hi > x/a", "cp x/a x/b", "mv x/b x/y/", "ls x/y", "cp x z", "cp -r x z", "ls z", "rm -r x z", "ls x")
    assert out.startswith("b") and "cp: -r not specified; omitting directory 'x'" in out
    assert "a  y" in out and "ls: cannot access 'x'" in out


def test_permissions_and_scripts():
    out = sh("echo 'echo arg=$1' > s.sh", "./s.sh z", "chmod +x s.sh", "./s.sh z", "ls -l s.sh", "bash s.sh q",
             "chmod 600 s.sh; ls -l s.sh", "chmod a-r s.sh; cat s.sh")
    assert "bash: ./s.sh: Permission denied" in out
    assert "arg=z" in out and "arg=q" in out and "-rwxr-xr-x" in out and "-rw-------" in out
    assert "cat: s.sh: Permission denied" in out


def test_loops_conditionals_and_logic():
    out = sh("for n in 1 2 3; do echo n$n; done", "if [ -d inbox ]; then echo yes; else echo no; fi",
             "false || echo or", "true && echo and", "false && echo never", "[ 3 -gt 2 ] && echo gt")
    assert out.split() == ["n1", "n2", "n3", "yes", "or", "and", "gt"]


def test_history_alias_man_help():
    s = make_session()
    out = sh("echo first", "history", "!!", "alias hi='echo hello'", "hi there", "man grep | head -n 2", "ls --help | head -n 1",
             "type ll", "which ls", s=s)
    assert "    1  echo first" in out and "hello there" in out
    assert "grep - print lines that match patterns" in out and "NAME" in out
    assert "ll is aliased to `ls -l'" in out and "/usr/bin/ls" in out


def test_syntax_errors_and_hints():
    out = sh("echo x |", "echo 'unterminated", "vim file", "pwdd")
    assert "syntax error near unexpected token `newline'" in out
    assert "unexpected EOF while looking for matching" in out
    assert "nano" in out and "did you mean `pwd`" in out


def test_sandbox_never_touches_real_disk(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sh("echo x > leak.txt", "mkdir leakdir", "touch /tmp/founders_leak_test")
    import os
    assert os.listdir(tmp_path) in ([], ["home"])
    assert not os.path.exists("/tmp/founders_leak_test")


def test_game_commands_pipe_like_real_ones():
    s = make_session()
    out = sh("metrics | grep -i runway", "ls inbox | wc -l", "help | grep -c interview", s=s)
    assert "Runway" in out and "months" in out
    assert "2\n" in out


def test_tab_completion_candidates():
    from founders_sim.shell.completion import ShellCompleter
    s = make_session()
    comp = ShellCompleter(s.shell)
    assert "interview " in comp.candidates("inter")[1]
    assert comp.candidates("cat inb")[1] == ["inbox/"]
    assert "investors/angel_rossi.txt" in comp.candidates("pitch ")[1]
    assert "customers/leads/maria.txt" in comp.candidates("interview customers/leads/m")[1]
    assert "wc " in comp.candidates("ls | w")[1]


def test_sed_like_the_real_thing():
    out = sh("printf 'TODO one\\nkeep cat cat\\nTODO two\\n' > f.md", "sed 's/cat/dog/' f.md", "sed -n '2p' f.md",
             "sed -i '/^TODO/d' f.md", "cat f.md", "sed -i 's/cat/dog/g; s/keep/kept/' f.md", "cat f.md",
             "echo hello | sed 's/l/L/g'", "echo a-b | sed -E 's/(a)-(b)/\\2-\\1/'", "sed 's/x' f.md", "sed 's/a/b/' nope")
    lines = out.splitlines()
    assert lines[:3] == ["TODO one", "keep dog cat", "TODO two"]
    assert lines[3:7] == ["keep cat cat", "keep cat cat", "kept dog dog", "heLLo"]
    assert lines[7] == "b-a"
    assert "unterminated `s' command" in out and "sed: can't read nope: No such file or directory" in out


def test_spec_reuse_must_be_adapted():
    from tests.helpers import GOOD_SPEC
    from founders_sim.vfs import COMPANY
    s = make_session()
    s.game.idea = 0
    run(s, "interview maria luca", "spec new flashcards")
    s.fs.write(f"{COMPANY}/product/specs/flashcards.md",
               GOOD_SPEC.format(title="Auto-flashcards", key="flashcards", note="customers/notes/maria.md"))
    out = run(s, "spec check product/specs/flashcards.md", "spec new offline --from product/specs/flashcards.md",
              "head -n 2 product/specs/offline.md", "spec check product/specs/offline.md")
    assert "Score: 100/100" in out and "feature: offline" in out and "Copy:" in out and "Score: 35/100" in out
    out = run(s, "sed -i 's/flashcards/offline/g; s/maria.md/luca.md/; s/data model/local cache/; s/user-facing screen/sync queue/; "
                 "s/onboarding and settings/the reader/; s/main flow in under two minutes/reader with wifi off/; "
                 "s/Invalid input shows a clear error/Edits made offline sync later/; s/one thousand records/a full course/' "
                 "product/specs/offline.md", "spec check product/specs/offline.md")
    assert "Copy:" not in out and "Score: 100/100" in out
