from item import Item
from shared import and_comma_list


class Room:
    __slots__ = [
        "name",
        "rooms",
        "description",
        "items",
        "global_rooms"
    ]

    def __init__(self, *, name, rooms, items, description, global_rooms=None, **kwargs):
        self.name = name
        self.rooms = rooms  # dict of north, south, east, west etc with hashes of other rooms
        self.items = items  # dict of item names -> item object
        self.description = description
        self.global_rooms = global_rooms  # dict of hashes to room objects

    def __str__(self):
        return "{0.name:*^60}".format(self)

    @property
    def item_list(self):
        return "There are {} items: {}.".format(len(self.items), and_comma_list(*map(str, self.items)))

    @property
    def exits(self):
        return "There are {} exits: {}.".format(len(self.rooms), and_comma_list(*self.rooms))

    def to_dict(self):
        return {
            "name": self.name,
            "rooms": self.rooms,
            "description": self.description,
            "items": [(k, v.to_dict()) for k, v in self.items],
        }

    @classmethod
    def from_dict(cls, dic):
        items = [Item.from_dict(i) for i in dic.pop("items")]
        return cls(items=items, **dic)
