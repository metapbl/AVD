# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""gaindb - lossless MP3 gain analysis and adjustment (core package).

Single source of truth for the program name and version. The CLI
(gaindb_cli.py) and the GUI About dialog both read these constants, so a
version bump only needs to change __version__ here (pyproject.toml is build
metadata and is updated separately).
"""

__version__ = "0.5.1"
PROGNAME = "Gain dB"