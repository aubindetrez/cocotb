# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import ctypes
import typing

from cocotb.types.logic import Logic, LogicConstructibleT

LogicT = typing.TypeVar("LogicT", bound=Logic)
S = typing.TypeVar("S")
Self = typing.TypeVar("Self", bound="LogicArray")


class LogicArray:
    __slots__ = (
        "_int_impl",
        "_int_impl_valid",
        "_int_impl_byteorder",
        "_str_impl",
        "_str_impl_valid",
        "_list_impl",
        "_list_impl_valid",
    )

    @typing.overload
    def __init__(self, value: str) -> None:
        ...

    @typing.overload
    def __init__(self, value: int, *, byteorder: str) -> None:
        ...

    @typing.overload
    def __init__(self, value: typing.Iterable[LogicConstructibleT]) -> None:
        ...

    def __init__(self, value, *, byteorder: str = "big") -> None:
        self._str_impl_valid = False
        self._list_impl_valid = False
        self._int_impl_valid = False
        self._int_impl_byteorder = "big"

        if value is None and range is None:
            raise ValueError(
                "at least one of the value and range input parameters must be given"
            )
        if value is None:
            self._int_impl = 0
            self._int_impl_valid = True

        if isinstance(value, str):
            self._str_impl = value
            self._str_impl_valid = True
        elif isinstance(value, int):
            self._int_impl = value
            self._int_impl_byteorder = byteorder
            self._int_impl_valid = True
        elif isinstance(value, ctypes.Structure):
            # ctypes.Structure is also typing.typing.Iterable, but it is not supported
            raise ValueError(
                f"{value} is an instance of ctypes.Structure which cannot be converted to LogicArray"
            )
        elif isinstance(value, typing.typing.Iterable):
            self._list_impl = list(value)
            # Validate and set _list_impl_valid to True
            self._list_impl_valid = True
        else:
            raise TypeError(
                f"cannot construct {type(self).__qualname__} from value of type {type(value).__qualname__}"
            )

    def __str__(self) -> str:
        if self._str_impl_valid:
            return self._str_impl
        elif self._int_impl_valid:
            # Construct from the integer representation
            return bin(self._int_impl)[2:]
        elif self._list_impl_valid:
            # Construct from the list representation
            return "".join(map(str, self._list_impl))
        else:
            raise ValueError("Invalid internal state")

    def as_int(self, *, byteorder: str = "big", signed: bool = False) -> int:
        if self._int_impl_valid and self._int_impl_byteorder == byteorder:
            res_int = self._int_impl
        elif self._str_impl_valid:
            # Construct from the string representation
            res_int = int(self._str_impl, 2)
        elif self._list_impl_valid:
            # Construct from the list representation
            res_int = int("".join(map(str, self._list_impl)), 2)
        else:
            raise ValueError("Invalid internal state")

        if signed:
            _twos_comp(res_int, int.bit_length(res_int))

        return res_int

    def as_array(self) -> typing.List[Logic]:
        if self._list_impl_valid:
            return self._list_impl
        elif self._str_impl_valid:
            # Construct from the string representation
            try:
                return [Logic(bit) for bit in self._str_impl]
            except TypeError:
                raise ValueError("Invalid internal state")
        elif self._int_impl_valid:
            # Construct from the integer representation
            binary_str = bin(self._int_impl)[2:]
            return [Logic(bit) for bit in binary_str]
        else:
            raise ValueError("Invalid internal state")

    @property
    def array(self) -> typing.List[Logic]:
        return self.as_array()

    @property
    def binstr(self) -> str:
        if self._str_impl_valid:
            return self._str_impl
        return str(self)

    def is_resolvable(self) -> bool:
        if self._int_impl_valid:
            return True
        elif self._str_impl_valid:
            return all(bit in ("0", "1") for bit in self._str_impl)
        elif self._list_impl_valid:
            return all(
                bit in (True, False, Logic(0), Logic(1)) for bit in self._list_impl
            )
        else:
            ValueError("Invalid internal state")

    def __iter__(self) -> typing.Iterable[Logic]:
        return iter(self.as_array())

    def __reversed__(self) -> typing.Iterable[Logic]:
        return reversed(self.as_array())

    def __setitem__(self, index: int, value: bool) -> None:
        self._int_impl_valid = False
        self._str_impl_valid = False
        self._list_impl[index] = value

    def __eq__(self, other):
        """
        Overrides the default implementation to enable comparision
        with integers and strings (case insensitive)

        .. code-block:: python3

            >>> la = LogicArray(10,Range(3, 'downto', 0))
            >>> la == 10
            True
            >>> la == "1010"
            True

            >>> la = LogicArray("10X1Z0")
            >>> la == "10X1Z0"
            True
            >>> la == "1001Z0" # Try replace X with 0
            False
            >>> la == "1011Z0" # Try replace X with 1
            False
            >>> la == "10X100" # Try replace Z with 0
            False
            >>> la == "10X110" # Try replace Z with 1
            False

        :class:`LogicArray` supports comparison with integers and strings

        .. code-block:: python3
            >>> a = LogicArray("0")
            >>> if a == 0: print("Pass")
            ... else: print("Fail")
            Pass
            >>> if a[0] == 0: print("Pass")
            ... else: print("Fail")
            Pass

        :class:`Logic` supports comparison with integers

        """
        if isinstance(other, int) and self._int_impl_valid:
            return self._int_impl_valid == other
        elif isinstance(other, int):
            return self.as_int() == other
        if isinstance(other, str) and self._str_impl_valid:
            return self._str_impl_valid == other
        elif isinstance(other, str):
            return str(self) == other

        # Handle comparison with X and Z
        return self.binstr == other.binstr

    def __repr__(self) -> str:
        return "{}({!r})".format(type(self).__qualname__, self.binstr)

    def __int__(self):
        # Required for Python 3.7 or earlier
        # Python 3.8+ uses index()
        return self.as_int()

    def __mul__(self, other):
        if isinstance(other, type(self)):
            if self._int_impl_valid:
                return self._int_impl * int(other)
        return int(self) * int(other)


def _twos_comp(val: int, bits: int):
    """compute the 2's complement of int value val"""
    if (val & (1 << (bits - 1))) != 0:
        val = val - (1 << bits)
    return val
