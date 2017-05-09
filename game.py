import asyncio
import json
import sys

import enum

async def ainput(prompt=None, *,  loop=None):
    loop = asyncio.get_event_loop() if loop is None else loop
    line = '' if prompt is None else prompt
    print(line)
    return await loop.run_in_executor(None, sys.stdin.readline)


class Status(enum.IntFlag):
    blind = 1
    bleed = 2
    slow = 4


def and_comma_list(*items):
    if not items:
        return ""
    comma_lst = ", ".join(items[:-1])
    return " and ".join(filter(None, (comma_lst, items[-1])))


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

    @property
    def entrance(self):
        dirs = "There are {} exits: {}.".format(len(self.rooms), and_comma_list(*self.rooms))
        items = "There are {} items: {}.".format(len(self.items), and_comma_list(*map(str, self.items)))
        return "{0.name:*^60}\n{0.description}\n{1}\n{2}".format(self, dirs, items)

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


class Item:

    def __init__(self, name, description, effects):
        self.name = name  # string
        self.description = description  # string
        self.effects = effects  # (type, {effect_args=stuff})

    def apply(self, player):
        player.apply(*self.effects)

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "effects": self.effects
        }

    @classmethod
    def from_dict(cls, dic):
        return cls(**dic)

    def __str__(self):
        return self.name


class Player:

    async def bleed(self, *, damage_tick, tick_length, timeout):
        """Apply a bleeding effect to the player.
        damage_tick <- Damage taken every tick.
        tick_length <- Time between each damage tick (seconds).
        timeout     <- Max time to bleed for (seconds).
        """
        def cut_type(damage_tick):
            if 0 <= damage_tick <= 3:
                return "small"
            if 3 < damage_tick <= 8:
                return "moderate"
            return "largs"

        self.notify("A {} appears on your body and starts to bleed,"
                    " you'll take {} damage every {}s for the next {}s".format(cut_type(damage_tick), damage_tick,
                                                                               tick_length,
                                                                               timeout))
        for _ in range(timeout // tick_length):
            self.hp -= damage_tick
            await asyncio.sleep(tick_length)
            if not self.is_active:
                break

    def blind(self, *, timeout):
        """Blind the player for timeout amount of time."""
        def release():
            self.status &= ~Status.blind
            self.notify("Your blindness disappears and you regain your sight.")

        if Status.blind not in self.status:
            self.status |= Status.blind
            self.notify("You become blinded for the next {} seconds. Traps and items will"
                        " not be described as you enter rooms, only exits.".format(timeout))
            self.loop.call_later(timeout, release)

    def slow(self, *, timeout):

        def release():
            self.status &= ~Status.slow
            self.notify("Your muscles unfreeze and you regain your movement.")

        if Status.slow not in self.status:
            self.status |= Status.slow
            self.notify("You become frozen for the next {} seconds."
                        " You will not be able to exit this room until unfrozen.".format(timeout))
            self.loop.call_later(timeout, release)

    def hurt(self, *, damage):
        self.notify("You took {} damage!".format(damage))
        self.hp -= damage

    def __init__(self, basehp, game, loop):
        self.loop = loop
        self.hp = basehp
        self.status = Status(0)
        self.game = game
        self.is_active = True

    def add_effect(self, type, **kwargs):
        if type == "slow":
            self.loop.create_task(self.bleed(**kwargs))
        elif type == "blind":
            self.blind(**kwargs)
        elif type == "slow":
            self.slow(**kwargs)
        elif type == "hurt":
            self.hurt(**kwargs)

    def notify(self, msg):
        self.game.player_msg(msg)


class Game:

    def __init__(self, *, rooms, opening, start_room, basehp=100, loop=None):
        self.rooms = rooms
        self.opening = opening
        self.loop = asyncio.get_event_loop() if loop is None else loop
        self.player = Player(basehp, self, self.loop)
        self.start_room = start_room

        self.current_room = None

    @classmethod
    def from_dict(cls, dic):
        rooms = cls.gen_rooms(dic.pop("rooms"))
        return cls(rooms=rooms, **dic)

    @staticmethod
    def gen_rooms(rooms):
        globaldict = {}
        for k, v in rooms.items():
            room = Room.from_dict(v)
            globaldict[k] = room
            room.global_rooms = globaldict
        return globaldict

    def player_msg(self, msg):
        print(msg)
        # TODO: async this

    def to_dict(self):
        return {
            "rooms": {k: v.to_dict() for k, v in self.rooms.items()},
            "basehp": self.basehp,
            "opening": self.opening,
            "start_room": self.start_room
        }

    def use_item(self, item):
        for k, v in item.effects:
            self.player.add_effect(k, **v)

    def enter_room(self, room):
        self.current_room = self.rooms[room]
        print(self.current_room.entrance)

    async def game_loop(self):
        print(self.opening)
        self.enter_room(self.start_room)
        while True:
            uinput = await ainput("Make your choice")
            print("your choice was", uinput, end="")


if __name__ == '__main__':

    with open("game.json") as fp:
        gdata = json.load(fp)

    loop = asyncio.get_event_loop()

    game = Game.from_dict(gdata)

    loop.run_until_complete(game.game_loop())
