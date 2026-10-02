#!/usr/bin/env python3

from papple2.util import hexaddr
from papple2.core.cpu import JSR, RTS, JMP_absolute, JMP_indirect

class Labels:
    def __init__(self) -> None:
        self.labels = {}
        self.passed_labels = {}
        self.add_standard_labels()


    def add_address( self, leap_from_opcode: int, leap_to_address: int, label: str | None = None ) -> str:
        if leap_to_address in self.labels:
            return self.labels[leap_to_address]

        if label is None:
            if leap_to_address in self.passed_labels:
                label = self.passed_labels[leap_to_address]
            else:
                if leap_from_opcode == JSR:
                    marker = 'S'
                elif leap_from_opcode == RTS:
                    marker = 'R'
                elif leap_from_opcode in [JMP_absolute, JMP_indirect]:
                    marker = 'J'
                else:
                    marker = 'L'
                # print(hexaddr(leap_to_address, show_dollar=False))
                label = marker + hexaddr(leap_to_address, show_dollar=False)
        self.labels[leap_to_address] = label
        return label

    def add_labels(self, labels: list[tuple[int, str]]) -> None:
        for address, label in labels:
            self.passed_labels[address] = label

    def add_standard_labels(self) -> None:
        self.add_labels([
            (0xC000, 'r:KBD w:CLR80COL'),
            (0xC010, 'r:KBDSTRB'),
            (0xC030, 'rw:SPKR'),
            (0xC050, 'rw:TXTCLR'),
            (0xC052, 'rw:MIXCLR'),

            (0xc054, 'rw:TXTPAGE1'),
            (0xc057, 'rw:HIRES'),
            (0xc061, 'r:BUTN0'),
            (0xc062, 'r:BUTN1'),

            (0xfb1e, 'F8ROM:PREAD'),
            (0xfca8, 'F8ROM:WAIT'),
        ])

    def label_at(self, address: int) -> str:
        """The name for address, or '' if it has none. Looks in the same
        order as replace_operand_address(): first the names add_address()
        made, then the names passed in."""
        if address in self.labels:
            return self.labels[address]
        return self.passed_labels.get(address, '')

    def replace_operand_address(self, operand: str, operand_address: int) -> str:
        # TODO: label replacement in operands must work for all addresses, including zero page
        if operand_address in self.labels:
            operand = operand.replace(hexaddr(operand_address), self.labels[operand_address])

        elif operand_address in self.passed_labels:
            # we never encountered the passed label for this particular address
            # if we had, the label would be in self.labels
            assert operand_address not in self.labels
            operand = operand.replace(hexaddr(operand_address), self.passed_labels[operand_address])

        return operand
