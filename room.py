"""Module holding Room class for game."""
from item import Item
from shared import and_comma_list


class Room:
    """Class that represents a Room."""
    __slots__ = [
        "name",
        "rooms",
        "description",
        "items",
        "global_rooms",
        "ending_room"
    ]

    def __init__(self, *, name, description, rooms={}, items=[], global_rooms=None, ending_room=False, **kwargs):
        self.name = name
        self.rooms = rooms  # dict of north, south, east, west etc with hashes of other rooms
        self.items = items  # dict of item names -> item object
        self.description = description
        self.global_rooms = global_rooms  # dict of hashes to room objects
        self.ending_room = ending_room

    def __str__(self):
        return "{0.name:*^60}".format(self)

    @property
    def item_list(self):
        return "There are {} items: {}".format(len(self.items), and_comma_list(*map(str, self.items)))

    @property
    def exits(self):
        return "There are {} exits: {}".format(len(self.rooms), and_comma_list(*self.rooms))

    def to_dict(self):
        return {
            "name": self.name,
            "rooms": self.rooms,
            "description": self.description,
            "items": [(k, v.to_dict()) for k, v in self.items],
        }

    @classmethod
    def from_dict(cls, dic):
        items = [Item.from_dict(i) for i in dic.pop("items", [])]
        return cls(items=items, **dic)
