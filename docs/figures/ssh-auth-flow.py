#!/usr/bin/env python3
"""How Git, ssh, ~/.ssh/config, ssh-agent and the keys fit together.

Companion diagram for docs/github-ssh-setup.md. Run with:

    umldrawer build ssh-auth-flow.py

Layout notes, because the routing depends on them. `ssh` is the hub: every
consultation it makes fans out below it, and the one long horizontal at y=150
is the wire to GitHub, so the band around it is kept empty. Routing is direct
rather than orthogonal, so each pair that is linked has a clear straight line
between it and nothing parked in the way.
"""
import math
from pathlib import Path

from drawio_model import Diagram, Group

d = Diagram("SSH auth flow", page_w=1840, page_h=1100, route="direct")

INK    = "#1F3A5F"   # glyph line
WARM   = "#B3541E"   # glyph accent
# One colour per role, and no colour does two jobs. The files split into three
# groups because they answer different questions: what SSH is configured to do,
# what your identity is, and what your shell does at startup.
CMD      = "#E3F2FD"   # you run it
PROC     = "#E8F5E9"   # a running process
SSH_FILE = "#FFF8E1"   # a file the SSH client reads
KEY_FILE = "#EDE7F6"   # your key pair, the two halves of your identity
SH_FILE  = "#FFE0B2"   # a shell startup file
REMOTE   = "#FCE4EC"   # GitHub

# The marks are placed, never redrawn. See assets/README.md for where each comes from.
ASSETS = Path(__file__).resolve().parent / "assets"
GH_MARK = str(ASSETS / "github-mark.svg")
# Every box that is a file on disk carries this, whatever role its colour gives it.
FILE_MARK = str(ASSETS / "file-mark.svg")

def _poly(pid, pts, close=True, colour=INK, width=2.4):
    pts = list(pts) + ([pts[0]] if close else [])
    d.polyline(pid, pts, arrow=False, colour=colour, width=width)


def _line(pid, a, b, colour=INK, width=2.4):
    d.polyline(pid, [a, b], arrow=False, colour=colour, width=width)


def _arc(pid, cx, cy, rx, ry, a0, a1, n=28, colour=INK, width=2.4):
    pts = [(round(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n))),
            round(cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))))
           for i in range(n + 1)]
    d.polyline(pid, pts, arrow=False, colour=colour, width=width)


def agent_glyph(cx, cy, s=1.0):
    """The agent: hat, shades, earpiece, deliberately no face.

    Drawn rather than described, because the one thing this figure has to land is
    that the key goes in and never comes out, and a silhouette that is visibly
    keeping a secret says that before anybody reads a label. Built from polylines
    only, so it needs no shape type the rest of the diagram does not already use.
    """
    def p(x, y):
        return (round(cx + x * s), round(cy + y * s))

    _poly("g-brim", [p(-76, -44), p(76, -44), p(62, -30), p(-62, -30)])
    _poly("g-crown", [p(-42, -44), p(-36, -94), p(36, -94), p(42, -44)])
    _line("g-band", p(-40, -56), p(40, -56), width=1.8)
    _arc("g-face", cx, cy - 26 * s, 40 * s, 40 * s, 0, 180)
    _poly("g-lens-l", [p(-36, -20), p(-8, -20), p(-10, -2), p(-32, -2)], colour=WARM)
    _poly("g-lens-r", [p(8, -20), p(36, -20), p(32, -2), p(10, -2)], colour=WARM)
    _line("g-bridge", p(-8, -16), p(8, -16), colour=WARM, width=1.8)
    _line("g-coat-l", p(-46, 16), p(-14, 44))
    _line("g-coat-r", p(46, 16), p(14, 44))
    _poly("g-tie", [p(0, 22), p(9, 34), p(0, 62), p(-9, 34)])
    _arc("g-wire", cx + 46 * s, cy + 4 * s, 26 * s, 26 * s, 250, 340, colour=WARM, width=1.8)


# ------------------------------------------------- your machine, the top band
d.block("git", "git push\ngit clone / fetch", 60, 100, w=210, h=100, fill=CMD)
d.block("ssh", "ssh\n/usr/bin/ssh\nthe only one of these\nthat reads the config",
        430, 90, w=240, h=120, fill=PROC)

# What ssh consults, fanned out below it so no route shares a lane.
d.block("config", "\n~/.ssh/config\nHost github.com\n  IdentityFile ~/.ssh/id_ed25519\n"
                  "  IdentitiesOnly yes\n  AddKeysToAgent yes",
        120, 374, w=280, h=152, fill=SSH_FILE)
d.image("config-mark", FILE_MARK, 260, 400, w=24)
# Two parts on purpose. The writer paints every block over every polyline, so a
# filled box would bury the glyph. The outer frame is therefore unfilled and carries
# the drawing, and the caption sits in a filled panel below it, which also keeps the
# green that the legend uses for a running process.
d.block("agent", "", 440, 370, w=270, h=200, fill="none")
agent_glyph(575, 424, s=0.46)
d.block("agent-panel", "ssh-agent\nholds the decrypted key in memory,\nreached over $SSH_AUTH_SOCK",
        450, 462, w=250, h=98, fill=PROC)
d.block("known", "\n~/.ssh/known_hosts\nhost keys this machine\nhas already trusted",
        790, 374, w=250, h=132, fill=SSH_FILE)
d.image("known-mark", FILE_MARK, 915, 400, w=24)

# How the key reaches the agent.
d.block("priv", "\nid_ed25519\nPRIVATE key\nnever leaves this machine",
        760, 592, w=240, h=120, fill=KEY_FILE)
d.image("priv-mark", FILE_MARK, 880, 616, w=24)
d.block("sshadd", "ssh-add\ndecrypts the private key\nwith your passphrase",
        450, 650, w=250, h=110, fill=CMD)
# Moved left of ssh-add so both of its arrows have a clear line. It does two
# separate things, and drawing only the second made the agent appear from nowhere.
d.block("bashrc", "\n~/.bashrc\nread by every Git Bash\nwindow at startup",
        80, 880, w=250, h=120, fill=SH_FILE)
d.image("bashrc-mark", FILE_MARK, 205, 904, w=24)

d.block("pub", "\nid_ed25519.pub\nPUBLIC key\nsafe to publish",
        760, 730, w=240, h=120, fill=KEY_FILE)
d.image("pub-mark", FILE_MARK, 880, 754, w=24)

d.add(Group("keypair", "your key pair, generated together", members=["priv", "pub"]))
d.add(Group("machine", "Your machine, Git Bash on Windows",
            members=["git", "ssh", "config", "agent", "known",
                     "keypair", "sshadd", "bashrc"], dashed=True))

# ------------------------------------------------------------------- the far end
d.block("sshd", "\ngithub.com:22\nSSH endpoint\n(or ssh.github.com:443)",
        1500, 90, w=250, h=130, fill=REMOTE)
d.image("sshd-mark", GH_MARK, 1625, 116, w=30)
d.block("hostkey", "\nGitHub host key\npublished at\napi.github.com/meta",
        1150, 380, w=240, h=120, fill=REMOTE)
d.image("hostkey-mark", GH_MARK, 1270, 406, w=26)
d.block("acct", "\nYour GitHub account\nthe public keys you\nregistered in Settings",
        1150, 640, w=240, h=120, fill=REMOTE)
d.image("acct-mark", GH_MARK, 1270, 666, w=26)
d.block("repo", "\n<owner>/<repo>.git\nthe remote repository",
        1500, 890, w=250, h=110, fill=REMOTE)
d.image("repo-mark", GH_MARK, 1625, 916, w=26)

d.add(Group("github", "GitHub",
            members=["sshd", "hostkey", "acct", "repo"], dashed=True))

# ------------------------------------------------------------------- the flows
# Git never speaks SSH itself. It runs the client.
d.link("git", "ssh", "flow", "runs")

# ssh works out which key and which host from the config.
d.link("ssh", "config", "dependency", "reads")

# ssh never reads the private key: it asks the agent to sign a challenge.
d.link("ssh", "agent", "flow", "asks to sign")

# The agent got that key from ssh-add, which read it off disk.
d.link("priv", "sshadd", "dependency", "reads")
d.link("sshadd", "agent", "flow", "adds key")
# Two arrows, because the startup block does two things: it starts the agent
# itself, and separately it runs ssh-add to put the keys in it.
d.link("bashrc", "agent", "flow", "starts one per login")
d.link("bashrc", "sshadd", "flow", "then runs this to load the keys")

# The server is identified before anything is sent.
d.link("ssh", "known", "dependency", "checks host key")
d.link("hostkey", "known", "association", "must match")

# The public half was handed over once, by hand.
d.link("pub", "acct", "flow", "uploaded once")

# The authenticated connection, and what rides over it.
d.link("ssh", "sshd", "flow", "signed challenge")
d.link("sshd", "acct", "dependency", "verifies against")
d.link("sshd", "repo", "flow", "git protocol")

# ----------------------------------------------------------------------- note
d.text("t-key", "The private key never travels. ssh proves you hold it by having "
                "the agent sign a challenge with it.", 60, 1040, size=14, bold=True)
d.text("t-pair", "Blue = you run it.   Green = a running process.   Yellow = a file SSH reads.   "
                 "Purple = your key pair.   Orange = a shell startup file.   Pink = GitHub.   A page glyph marks every box that is a file on disk.",
       60, 1068, size=12)

out = Path(__file__).with_suffix("")
d.save(out)
