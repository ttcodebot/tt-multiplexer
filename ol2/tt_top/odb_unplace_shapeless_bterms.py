#
# OpenDB script to remove BTerms that have no shapes.
# This prevents DPL-0386 errors in newer OpenROAD versions.
#
# In the TT IHP wrapper, pad_raw[] BTerms are top-level ports that connect
# internally to GPIO pad instances. Some of these BTerms (e.g., power pads)
# end up without physical pin shapes after pad ring creation, which causes
# OpenROAD DetailedPlacement to error with DPL-0386.
#
# Copyright (c) 2026 TinyTapeout contributors
# SPDX-License-Identifier: Apache-2.0
#

import odb
import click

from reader import click_odb


@click.command()
@click_odb
def unplace_shapeless_bterms(reader):
    block = reader.block
    count = 0

    # Collect BTerms to destroy (can't modify while iterating)
    to_destroy = []
    for bterm in block.getBTerms():
        net = bterm.getNet()
        # Skip supply nets (they're already handled by DPL)
        if not net or net.getSigType() in ("POWER", "GROUND"):
            continue
        # Check if BTerm has any shapes
        pins = bterm.getBPins()
        has_shapes = False
        for pin in pins:
            if len(pin.getBoxes()) > 0:
                has_shapes = True
                break
        if not has_shapes:
            to_destroy.append(bterm)

    for bterm in to_destroy:
        name = bterm.getName()
        odb.dbBTerm.destroy(bterm)
        count += 1
        print(f"  Destroyed shapeless BTerm: {name}")

    print(f"Destroyed {count} shapeless BTerms")


if __name__ == "__main__":
    unplace_shapeless_bterms()
