"""Shared function for the entire game."""
import enum


def utils_get(iter_, **kwargs):
    """Find item with specified properties in an iterable."""
    def check(val):
        return all(getattr(val, k) == v for k, v in kwargs.items())

    for i in iter_:
        if check(i):
            return i


class Status(enum.IntFlag):
    """Possible statuses of the player."""

    blind = 1
    slow = 2


def and_comma_list(*items):
    """Join a list into format `a, b, c and d`."""
    if not items:
        return ""
    comma_lst = ", ".join(items[:-1])
    return " and ".join(filter(None, (comma_lst, items[-1])))


class CommandException(Exception):
    pass
