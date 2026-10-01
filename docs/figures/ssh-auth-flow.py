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
CMD    = "#E3F2FD"   # things you run
PROC   = "#E8F5E9"   # running processes
FILE   = "#FFF8E1"   # files on disk
REMOTE = "#FCE4EC"   # the far end

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
d.block("config", "~/.ssh/config\nHost github.com\n  IdentityFile ~/.ssh/id_ed25519\n"
                  "  IdentitiesOnly yes\n  AddKeysToAgent yes",
        120, 380, w=280, h=130, fill=FILE)
# Two parts on purpose. The writer paints every block over every polyline, so a
# filled box would bury the glyph. The outer frame is therefore unfilled and carries
# the drawing, and the caption sits in a filled panel below it, which also keeps the
# green that the legend uses for a running process.
d.block("agent", "", 440, 370, w=270, h=200, fill="none")
agent_glyph(575, 424, s=0.46)
d.block("agent-panel", "ssh-agent\nholds the decrypted key in memory,\nreached over $SSH_AUTH_SOCK",
        450, 462, w=250, h=98, fill=PROC)
d.block("known", "~/.ssh/known_hosts\nhost keys this machine\nhas already trusted",
        790, 380, w=250, h=110, fill=FILE)

# How the key reaches the agent.
d.block("priv", "id_ed25519\nPRIVATE key\nnever leaves this machine",
        80, 650, w=250, h=110, fill=FILE)
d.block("sshadd", "ssh-add\ndecrypts the private key\nwith your passphrase",
        450, 650, w=250, h=110, fill=CMD)
d.block("bashrc", "~/.bashrc\nstarts one ssh-agent per\nlogin and loads the keys",
        450, 890, w=250, h=100, fill=FILE)

d.block("pub", "id_ed25519.pub\nPUBLIC key\nsafe to publish",
        790, 640, w=250, h=110, fill=FILE)

d.add(Group("machine", "Your machine, Git Bash on Windows",
            members=["git", "ssh", "config", "agent", "known",
                     "priv", "sshadd", "bashrc", "pub"], dashed=True))

# ------------------------------------------------------------------- the far end
d.block("sshd", "github.com:22\nSSH endpoint\n(or ssh.github.com:443)",
        1500, 90, w=250, h=120, fill=REMOTE)
d.block("hostkey", "GitHub host key\npublished at\napi.github.com/meta",
        1150, 380, w=240, h=110, fill=REMOTE)
d.block("acct", "Your GitHub account\nthe public keys you\nregistered in Settings",
        1150, 640, w=240, h=110, fill=REMOTE)
d.block("repo", "<owner>/<repo>.git\nthe remote repository",
        1500, 890, w=250, h=100, fill=REMOTE)

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
d.link("bashrc", "sshadd", "flow", "on first window")

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
d.text("t-pair", "Blue = you run it.   Green = a running process.   "
                 "Cream = a file on disk.   Pink = GitHub.", 60, 1068, size=12)

out = Path(__file__).with_suffix("")
d.save(out)
