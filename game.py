import asyncio
import inspect
import json
import sys
from concurrent import futures

import enum


class CommandException(Exception):
    pass


async def ainput(prompt=None, *,  loop=None, event=None):
    """Get input from prompt asynchronously."""
    loop = asyncio.get_event_loop() if loop is None else loop
    line = '' if prompt is None else prompt

    print(line)

    tasks = [loop.run_in_executor(None, sys.stdin.readline)]
    if event is not None:
        tasks.append(event.wait())

    results, _ = await asyncio.wait(tasks, return_when=futures.FIRST_COMPLETED)
    result = [i.result() for i in results][0]
    if isinstance(result, str):
        return result.strip(" \n\r")


def utils_get(iter, **kwargs):
    def check(val):
        return all(getattr(val, k) == v for k, v in kwargs.items())

    for i in iter:
        if check(i):
            return i


class Status(enum.IntFlag):
    blind = 1
    bleed = 2
    slow = 4


def and_comma_list(*items):
    """Join a list into format `a, b, c and d`."""
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

    def __init__(self, name, description, effects, consumed_state="used"):
        self.name = name  # string
        self.description = description  # string
        self.effects = effects  # [{name=name, effect_args=stuff)]
        self.used = False
        self.state = consumed_state

    def apply(self, player):
        player.add_effect(*self.effects)
        self.used = True

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "effects": self.effects,
            "consumed_state": self.state
        }

    @classmethod
    def from_dict(cls, dic):
        return cls(**dic)

    def __str__(self):
        return self.name


class Player:

    def __init__(self, basehp, game, loop):
        self.loop = loop
        self._hp = basehp
        self.status = Status(0)
        self.game = game
        self.is_active = True

    #  TODO: refactor status effects into modules
    async def bleed(self, *, damage_tick, tick_length, timeout):
        """Apply a bleeding effect to the player.
        damage_tick <- Damage taken every tick.
        tick_length <- Time between each damage tick (seconds).
        timeout     <- Max time to bleed for (seconds).
        """
        def cut_type(damage_tick):
            if 0 <= damage_tick <= 3:
                return "small cut"
            if 3 < damage_tick <= 8:
                return "moderate gash"
            return "large wound"

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

    @property
    def hp(self):
        return self._hp

    @hp.setter
    def hp(self, other):
        self._hp = other
        if self.hp < 0:
            self.game.finish("You died")

    def add_effect(self, *effects):
        for i in effects:
            type = i.pop("type")
            if type == "bleed":
                self.loop.create_task(self.bleed(**i))
            elif type == "blind":
                self.blind(**i)
            elif type == "slow":
                self.slow(**i)
            elif type == "hurt":
                self.hurt(**i)

    def notify(self, msg):
        self.game.player_msg(msg)


class Command:

    def __init__(self, func):
        self.name = func.__name__
        self.func = func
        doc = "" if func.__doc__ is None else func.__doc__
        self.desc = doc.split("\n")[0]
        self.parent = None

    async def invoke(self, *args):
        res = self.func(self.parent, *args)
        if inspect.isawaitable(res):
            await res


class Game:

    commands = {}

    def __init__(self, *, rooms, opening, start_room, basehp=100, loop=None):
        self.rooms = rooms
        self.opening = opening
        self.loop = asyncio.get_event_loop() if loop is None else loop
        self.player = Player(basehp, self, self.loop)
        self.start_room = start_room

        self.current_room = None
        self.running_event = asyncio.Event()

    def finish(self, reason):
        self.running_event.set()
        self.player_msg(reason)

    async def parse_command(self, string):
        cmd, *rest = string.split()  # split first word off
        func = self.commands.get(cmd)
        if func is None:
            raise Exception("Command not found")
        await func.invoke(*rest)

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
        while not self.running_event.is_set():
            uinput = await ainput("Make your choice", event=self.running_event)
            if not uinput:
                continue

            try:
                await self.parse_command(uinput)
            except CommandException as e:
                print(e)

    def add_cog(self, cog):
        print("Registering cog: {.__class__.__name__}".format(cog))
        for name, member in inspect.getmembers(cog):
            if isinstance(member, Command):
                member.parent = cog
                self.commands[name] = member


class Cog:

    def __init__(self, game):
        self.game = game

    @Command
    def move(self, direction):
        """Move to a location. use: move <direction>."""
        room = self.game.current_room.rooms.get(direction)
        if room is None:
            raise CommandException("Cannot move in this direction")

        self.game.enter_room(room)

    @Command
    def use(self, item):
        """Use an item. use: use <item>."""
        item = utils_get(self.game.current_room.items, name=item)
        if item is None:
            raise CommandException("This item does not exist")
        if item.used:
            raise CommandException("Item has been {0.state}.".format(item))
        item.apply(self.game.player)

    @Command
    def help(self):
        """Display the help."""
        format_str = "{0.name}: {0.desc}"
        print("Commands:")
        for i in self.game.commands.values():
            print(format_str.format(i))


if __name__ == '__main__':

    with open("game.json") as fp:
        gdata = json.load(fp)

    loop = asyncio.get_event_loop()

    game = Game.from_dict(gdata)
    game.add_cog(Cog(game))
    print(game.commands)

    loop.run_until_complete(game.game_loop())
