"""Connectivity + value check of a generated schematic against its intended netlist (LTspice netlister)."""
import asccheck, sim


def verify(asc_text, intended, name, keep=("0",)):
    net = sim.netlist(asc_text, name)
    rep = asccheck.compare(intended, net, keep=keep) + asccheck.value_check(intended, net)
    bodies = [l for l in net.splitlines() if l[:1] in "MQ"]
    return rep, net, bodies
