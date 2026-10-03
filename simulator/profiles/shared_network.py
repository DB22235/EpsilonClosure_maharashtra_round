"""Shared-network user profile.

Represents a legitimate participant who happens to share an IP address
with many others (CGNAT, corporate NAT, university network, etc.).

This is a marker subclass of NormalHuman — the behaviour is identical
but the client_class label is different so the analyzer can:
  - Confirm that shared-IP users are NOT disproportionately rejected.
  - Measure false-positive rate for IP-based controls.

No extra bot behaviour is added here.
"""

from __future__ import annotations

from simulator.profiles.normal_human import NormalHuman


class SharedNetworkUser(NormalHuman):
    """Legitimate user on a shared NAT/IP — same flow as NormalHuman."""

    client_class = "shared_network"
