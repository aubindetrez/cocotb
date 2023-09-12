# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import ctypes
import typing

from cocotb.types.array import Array
from cocotb.types.logic import Logic, LogicConstructibleT
from cocotb.types.range import Range

LogicT = typing.TypeVar("LogicT", bound=Logic)
S = typing.TypeVar("S")
Self = typing.TypeVar("Self", bound="LogicArray")


class LogicArray(Array[Logic]):
    r"""
    Fixed-sized, arbitrarily-indexed, array of :class:`cocotb.types.Logic`.

    .. currentmodule:: cocotb.types

    :class:`LogicArray`\ s can be constructed from either iterables of values
    constructible into :class:`Logic`: like :class:`bool`, :class:`str`, :class:`int`;
    or from integers.
    If constructed from a positive integer, an unsigned bit representation is used to
    construct the :class:`LogicArray`.
    If constructed from a negative integer, a two's complement bit representation is
    used.
    Like :class:`Array`, if no *range* argument is given, it is deduced from the length
    of the iterable or bit string used to initialize the variable.
    If a *range* argument is given, but no value,
    the array is filled with the default value of Logic().

    .. code-block:: python3

        >>> LogicArray("01XZ")
        LogicArray('01XZ', Range(3, 'downto', 0))

        >>> LogicArray([0, True, "X"])
        LogicArray('01X', Range(2, 'downto', 0))

        >>> LogicArray(0xA)  # picks smallest range that can fit the value
        LogicArray('1010', Range(3, 'downto', 0))

        >>> LogicArray(-4, Range(0, "to", 3))  # will sign-extend
        LogicArray('1100', Range(0, 'to', 3))

        >>> LogicArray(range=Range(0, "to", 3))  # default values
        LogicArray('XXXX', Range(0, 'to', 3))

    :class:`LogicArray`\ s support the same operations as :class:`Array`;
    however, it enforces the condition that all elements must be a :class:`Logic`.

    .. code-block:: python3

        >>> la = LogicArray("1010")
        >>> la[0]                               # is indexable
        Logic('0')

        >>> la[1:]                              # is slice-able
        LogicArray('10', Range(1, 'downto', 0))

        >>> Logic("0") in la                    # is a collection
        True

        >>> list(la)                            # is an iterable
        [Logic('1'), Logic('0'), Logic('1'), Logic('0')]

    When setting an element or slice, the *value* is first constructed into a
    :class:`Logic`.

    .. code-block:: python3

        >>> la = LogicArray("1010")
        >>> la[3] = "Z"
        >>> la[3]
        Logic('Z')

        >>> la[2:] = ['X', True, 0]
        >>> la
        LogicArray('ZX10', Range(3, 'downto', 0))

    :class:`LogicArray`\ s can be converted into :class:`str`\ s or :class:`int`\ s.

    .. code-block:: python3

        >>> la = LogicArray("1010")
        >>> la.binstr
        '1010'

        >>> la
        LogicArray('1010', Range(3, 'downto', 0))

        >>> la.reverse()
        LogicArray('0101', Range(0, 'to', 3))

        >>> la.integer          # uses unsigned representation
        10

        >>> la.signed_integer   # uses two's complement representation
        -6

    :class:`LogicArray`\ s also support element-wise logical operations: ``&``, ``|``,
    ``^``, and ``~``.

    .. code-block:: python3

        >>> def big_mux(a: LogicArray, b: LogicArray, sel: Logic) -> LogicArray:
        ...     s = LogicArray([sel] * len(a))
        ...     return (a & ~s) | (b & s)

        >>> la = LogicArray("0110")
        >>> p = LogicArray("1110")
        >>> sel = Logic('1')        # choose second option
        >>> big_mux(la, p, sel)
        LogicArray('1110', Range(3, 'downto', 0))

    Args:
        value: Initial value for the array.
        range: Indexing scheme of the array.

    Raises:
        ValueError: When argument values cannot be used to construct an array.
        TypeError: When invalid argument types are used.
    """

    __slots__ = ()

    @typing.overload
    def __init__(
        self,
        value: typing.Union[int, typing.Iterable[LogicConstructibleT]],
        range: typing.Optional[Range],
    ):
        ...

    @typing.overload
    def __init__(
        self,
        value: typing.Union[int, typing.Iterable[LogicConstructibleT], None],
        range: Range,
    ):
        ...

    def __init__(
        self,
        value: typing.Union[int, typing.Iterable[LogicConstructibleT], None] = None,
        range: typing.Optional[Range] = None,
    ) -> None:
        if value is None and range is None:
            raise ValueError(
                "at least one of the value and range input parameters must be given"
            )
        if value is None:
            self._value = [Logic() for _ in range]
        elif isinstance(value, int):
            if value < 0:
                bitlen = int.bit_length(value + 1) + 1
            else:
                bitlen = max(1, int.bit_length(value))
            if range is None:
                self._value = [Logic(v) for v in _int_to_bitstr(value, bitlen)]
            else:
                if bitlen > len(range):
                    raise ValueError(f"{value} will not fit in {range}")
                self._value = [Logic(v) for v in _int_to_bitstr(value, len(range))]
        elif isinstance(value, ctypes.Structure):
            # ctypes.Structure is also typing.Iterable, but it is not supported
            raise ValueError(
                f"{value} is an instance of ctypes.Structure which cannot be converted to LogicArray"
            )
        elif isinstance(value, typing.Iterable):
            self._value = [Logic(v) for v in value]
        else:
            raise TypeError(
                f"cannot construct {type(self).__qualname__} from value of type {type(value).__qualname__}"
            )
        if range is None:
            self._range = Range(len(self._value) - 1, "downto", 0)
        else:
            self._range = range
        if len(self._value) != len(self._range):
            raise ValueError(
                f"value of length {len(self._value)} will not fit in {self._range}"
            )

    def reverse(self: Self) -> Self:
        """
        Creates a new :class:`LogicArray` with bits reversed.
        000ZX1 <-> 1XZ000
        """
        return type(self)(reversed(self), range=self.range.reverse())

    @property
    def binstr(self) -> str:
        return "".join(str(bit) for bit in self)

    @property
    def is_resolvable(self) -> bool:
        return all(bit in (Logic(0), Logic(1)) for bit in self)

    @property
    def integer(self) -> int:
        """
        Raises ValueError if the values cannot be converted to binary ('X' or 'Z')
        """
        value = 0
        for bit in self:
            value = value << 1 | int(bit)
        return value

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
        if isinstance(other, int):
            return self.integer == other
        elif isinstance(other, str):
            return self == LogicArray(other)

        # Handle comparison with X and Z
        return self.binstr == other.binstr

    # __ne__ is not required for python3 because by default it negates __eq__

    @property
    def signed_integer(self) -> int:
        value = self.integer
        if value >= (1 << (len(self) - 1)):
            value -= 1 << len(self)
        return value

    @typing.overload
    def __setitem__(self, item: int, value: LogicConstructibleT) -> None:
        ...

    @typing.overload
    def __setitem__(
        self, item: slice, value: typing.Iterable[LogicConstructibleT]
    ) -> None:
        ...

    def __setitem__(
        self,
        item: typing.Union[int, slice],
        value: typing.Union[LogicConstructibleT, typing.Iterable[LogicConstructibleT]],
    ) -> None:
        if isinstance(item, int):
            super().__setitem__(item, Logic(typing.cast(LogicConstructibleT, value)))
        elif isinstance(item, slice):
            super().__setitem__(
                item,
                (
                    Logic(v)
                    for v in typing.cast(typing.Iterable[LogicConstructibleT], value)
                ),
            )
        else:
            raise TypeError(
                f"indexes must be ints or slices, not {type(item).__name__}"
            )

    def __repr__(self) -> str:
        return "{}({!r}, {!r})".format(type(self).__qualname__, self.binstr, self.range)

    def __and__(self: Self, other: Self) -> Self:
        if isinstance(other, type(self)):
            if len(self) != len(other):
                raise ValueError(
                    f"cannot perform bitwise & "
                    f"between {type(self).__qualname__} of length {len(self)} "
                    f"and {type(other).__qualname__} of length {len(other)}"
                )
            return type(self)(a & b for a, b in zip(self, other))  # type: ignore
        return NotImplemented

    def __rand__(self: Self, other: Self) -> Self:
        return self & other

    def __or__(self: Self, other: Self) -> Self:
        if isinstance(other, type(self)):
            if len(self) != len(other):
                raise ValueError(
                    f"cannot perform bitwise | "
                    f"between {type(self).__qualname__} of length {len(self)} "
                    f"and {type(other).__qualname__} of length {len(other)}"
                )
            return type(self)(a | b for a, b in zip(self, other))  # type: ignore
        return NotImplemented

    def __add__(self: Self, other: Self) -> Self:
        """
        >>> LogicArray("1110", Range(3, 'downto', 0)) + LogicArray("10", Range(1, 'downto', 0))
        LogicArray('10000', Range(4, 'downto', 0))

        >>> LogicArray("1110", Range(3, 'downto', 0)) + LogicArray("10", Range(0, 'to', 1))
        LogicArray('10000', Range(4, 'downto', 0))

        >>> LogicArray("1110", Range(0, 'to', 3)) + LogicArray("10", Range(1, 'downto', 0))
        LogicArray('10000', Range(0, 'to', 4))
        """
        if isinstance(other, type(self)):
            # The addition of two arrays produces an array of size
            # max(len(self), len(other)) + 1

            # Identify the largest range
            if len(self) > len(other):
                largest_range = self._range
            else:
                largest_range = other._range

            # Add 1 bit to the largest range (for the carry)
            if largest_range.direction == "downto":
                # Example: Range(8, 'downto', 1) becomes Range(9, 'downto', 1)
                range = Range(
                    largest_range.left + 1, largest_range.direction, largest_range.right
                )
            else:
                # Example: Range(1, 'to', 7) becomes Range(1, 'to', 8)
                range = Range(
                    largest_range.left, largest_range.direction, largest_range.right + 1
                )

            value = int(self) + int(other)
            return type(self)(value, range)
        return NotImplemented

    def __ror__(self: Self, other: Self) -> Self:
        return self | other

    def __xor__(self: Self, other: Self) -> Self:
        if isinstance(other, type(self)):
            if len(self) != len(other):
                raise ValueError(
                    f"cannot perform bitwise ^ "
                    f"between {type(self).__qualname__} of length {len(self)} "
                    f"and {type(other).__qualname__} of length {len(other)}"
                )
            return type(self)(a ^ b for a, b in zip(self, other))  # type: ignore
        return NotImplemented

    def __rxor__(self: Self, other: Self) -> Self:
        return self ^ other

    def __invert__(self: Self) -> Self:
        return type(self)(~v for v in self)

    def __mul__(self, other):
        if isinstance(other, type(self)):
            return self.integer * other.integer
        return self.integer * int(other)

    def __imul__(self, other):
        if isinstance(other, type(self)):
            return self.__mul__(other)
        self.integer = self.integer * int(other)
        return self

    def __rmul__(self, other):
        if isinstance(other, type(self)):
            return self.__mul__(other)
        return self.integer * other

    def __abs__(self):
        return abs(self.integer)

    def __bool__(self):
        """Provide boolean testing of a :attr:`binstr`.
        Returns True if at least one bit is high.

        Raises: ValueError if the array contains X or Z

        >>> val = LogicArray("0000")
        >>> if val: print("True")
        ... else:   print("False")
        False
        >>> val = 42
        >>> if val: print("True")
        ... else:   print("False")
        True

        >>> val = LogicArray("00X0")
        >>> if val: print("True")
        Traceback (most recent call last):
        ...
        ValueError: Array contains Uninitialized (Z) or Unknown (X) bits


        >>> val = LogicArray("00Z0")
        >>> if val: print("True")
        Traceback (most recent call last):
        ...
        ValueError: Array contains Uninitialized (Z) or Unknown (X) bits

        """
        for char in self.binstr:
            if char.upper() == "X" or char.upper() == "Z":
                raise ValueError("Array contains Uninitialized (Z) or Unknown (X) bits")
            elif char == "1":
                return True
        return False

    def __index__(self):
        """
        >>> val = LogicArray("00000001000011110100")
        >>> hex(val)
        '0x10f4'
        >>> oct(val)
        '0o10364'
        """
        return self.integer

    def __ior__(self, other):
        """
        >>> a = LogicArray("0011")
        >>> b = LogicArray("1001")
        >>> a |= b
        >>> bin(a)
        '0b1011'
        >>> bin(b)
        '0b1001'
        """
        result = self | other  # Already check type and length
        self._value = result._value
        return self

    def __ixor__(self, other):
        """
        >>> a = LogicArray("0011")
        >>> b = LogicArray("1001")
        >>> a ^= b
        >>> bin(a)
        '0b1010'
        >>> bin(b)
        '0b1001'
        """
        result = self ^ other  # Already check type and length
        self._value = result._value
        return self

    def __iand__(self, other):
        """
        >>> a = LogicArray("0011")
        >>> b = LogicArray("1001")
        >>> a &= b
        >>> bin(a)
        '0b1'
        >>> bin(b)
        '0b1001'
        """
        result = self & other  # Already check type and length
        self._value = result._value
        return self

    def __iadd__(self, other):
        """
        >>> a = LogicArray("0011")
        >>> b = LogicArray("01")
        >>> a += b
        >>> bin(b)
        '0b1'
        >>> bin(a)
        '0b100'
        """
        result = self + other  # Already check type and length
        self._value = result._value
        return self

    def __mod__(self, other):
        """
        >>> LogicArray("1110") % LogicArray("10")
        0
        >>> LogicArray("0001") % LogicArray("10")
        1
        >>> LogicArray("0001") % 2
        1
        >>> 3 % LogicArray("10")
        1
        >>> a = LogicArray("1011")
        >>> a %= 2
        >>> a
        1
        """
        return self.integer % int(other)

    def __rmod__(self, other):
        """
        >>> 3 % LogicArray("10")
        1
        """
        return int(other) % self.integer

    def __floordiv__(self, other):
        """
        >>> a = LogicArray("1110")
        >>> b = LogicArray("10")
        >>> a // b
        7
        >>> a // 2
        7
        >>> c = LogicArray("1110")
        >>> c //= 2
        >>> c
        7
        """
        return self.integer // int(other)

    def __rfloordiv__(self, other):
        """
        >>> b = LogicArray("10")
        >>> 14 // b
        7
        """
        return int(other) // self.integer

    def __truediv__(self, other):
        """
        >>> a = LogicArray("1110")
        >>> b = LogicArray("10")
        >>> a / b
        7.0
        >>> a / 2
        7.0
        >>> c = LogicArray("1110")
        >>> c /= 2
        >>> c
        7.0
        """
        return self.integer / int(other)

    def __rtruediv__(self, other):
        """
        >>> b = LogicArray("10")
        >>> 14 / b
        7.0
        """
        return int(other) / self.integer

    def __divmod__(self, other):
        """
        >>> divmod(LogicArray("1011"), LogicArray("10"))
        (5, 1)
        >>> divmod(LogicArray("1011"), 2)
        (5, 1)
        """
        return (self // other, self % other)

    def __rdivmod__(self, other):
        """
        >>> divmod(11, LogicArray("10"))
        (5, 1)
        """
        return (other // self, other % self)


def _int_to_bitstr(value: int, n_bits: int) -> str:
    if value < 0:
        value += 1 << n_bits
    return format(value, f"0{n_bits}b")
