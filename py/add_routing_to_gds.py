#!/usr/bin/env python3
"""Add DEF routing wires to a GDS file.

KLayout's DEF->GDS stream-out may not export NETS routing wires
depending on the KLayout version. This script reads the DEF after
CustomRoute + DetailedRouting, extracts FIXED/ROUTED wire segments,
and adds them as polygons to the GDS top cell.
"""
import re
import sys

import click
import gdstk

# IHP SG13CMOS5L layer mapping
LAYER_MAP = {
    'Metal1': (8, 0),
    'Metal2': (10, 0),
    'Metal3': (30, 0),
    'Metal4': (50, 0),
    'TopMetal1': (126, 0),
}


def parse_def_routing(def_path):
    """Parse DEF NETS section for FIXED/ROUTED wire segments."""
    with open(def_path) as f:
        text = f.read()

    # Get DEF UNITS (database units per micron)
    units_match = re.search(r'UNITS DISTANCE MICRONS (\d+)', text)
    dbu_per_um = int(units_match.group(1)) if units_match else 1000

    nets_match = re.search(r'NETS \d+ ;(.*?)END NETS', text, re.DOTALL)
    if not nets_match:
        return [], dbu_per_um

    wires = []

    # Match routing: + FIXED|ROUTED <layer> [( width )] ( x1 y1 ) ( x2|* y2|* )
    for m in re.finditer(
        r'\+\s+(?:FIXED|ROUTED)\s+(\w+)\s*'
        r'(?:\(\s*(\d+)\s*\)\s*)?'
        r'\(\s*(-?\d+)\s+(-?\d+)\s*\)'
        r'\s*\(\s*(-?\d+|\*)\s+(-?\d+|\*)\s*\)',
        nets_match.group(1)
    ):
        layer = m.group(1)
        width = int(m.group(2)) if m.group(2) else None
        x1, y1 = int(m.group(3)), int(m.group(4))
        x2 = x1 if m.group(5) == '*' else int(m.group(5))
        y2 = y1 if m.group(6) == '*' else int(m.group(6))

        if layer in LAYER_MAP:
            wires.append((layer, x1, y1, x2, y2, width))

    return wires, dbu_per_um


@click.command()
@click.argument('gds_in')
@click.argument('def_in')
@click.argument('gds_out')
@click.option('--default-width', default=200, help='Default wire width in DEF units (nm)')
def main(gds_in, def_in, gds_out, default_width):
    lib = gdstk.read_gds(gds_in)

    top = None
    for c in lib.cells:
        if c.name == 'tt_ihp_wrapper':
            top = c
            break
    if top is None:
        top = max(lib.cells, key=lambda c: len(c.references))
        print(f"[add_routing] Using cell: {top.name}")

    wires, dbu_per_um = parse_def_routing(def_in)
    print(f"[add_routing] {len(wires)} routing segments, DEF units={dbu_per_um}/um")

    # DEF coordinates are in DEF units (nm if dbu_per_um=1000)
    # GDS coordinates are in um (gdstk default)
    scale = 1.0 / dbu_per_um  # DEF units to um

    added = 0
    for layer_name, x1, y1, x2, y2, width in wires:
        gds_layer, gds_dt = LAYER_MAP[layer_name]
        w = width if width else default_width
        hw = w / 2.0

        if x1 == x2:  # vertical
            rect = gdstk.rectangle(
                ((x1 - hw) * scale, min(y1, y2) * scale),
                ((x1 + hw) * scale, max(y1, y2) * scale),
                layer=gds_layer, datatype=gds_dt,
            )
        else:  # horizontal
            rect = gdstk.rectangle(
                (min(x1, x2) * scale, (y1 - hw) * scale),
                (max(x1, x2) * scale, (y1 + hw) * scale),
                layer=gds_layer, datatype=gds_dt,
            )
        top.add(rect)
        added += 1

    print(f"[add_routing] Added {added} shapes to {top.name}")
    lib.write_gds(gds_out)


if __name__ == '__main__':
    main()
