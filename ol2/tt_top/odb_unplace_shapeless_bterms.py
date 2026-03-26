#
# OpenDB script to unplace BTerms that have no shapes.
# This prevents DPL-0386 errors in newer OpenROAD versions.
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
    for bterm in block.getBTerms():
        net = bterm.getNet()
        # Skip supply nets (they're already handled)
        if not net or net.getSigType() == "POWER" or net.getSigType() == "GROUND":
            continue
        # Check if BTerm has shapes
        pins = bterm.getBPins()
        has_shapes = False
        for pin in pins:
            if len(pin.getBoxes()) > 0:
                has_shapes = True
                break
        if not has_shapes:
            # Mark as unplaced to avoid DPL-0386
            for pin in pins:
                pin.setPlacementStatus("UNPLACED")
            if len(pins) == 0:
                # No BPins at all - BTerm has no geometry
                pass  # getBBox().isInverted() will be true, but we can't change it without a pin
            count += 1
            print(f"  Unplaced shapeless BTerm: {bterm.getName()}")

    print(f"Unplaced {count} shapeless BTerms")


if __name__ == "__main__":
    unplace_shapeless_bterms()
