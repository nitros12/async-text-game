import asyncio
import inspect
import json
import sys
from commands import BaseCommands, Command
from concurrent import futures

from player import Player
from room import Room
from shared import CommandException, Status

async def ainput(prompt=None, *, loop=None, event=None):
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


class Game:
    """Class for game events and controlling"""
    __slots__ = [
        "rooms",
        "opening",
        "loop",
        "player",
        "start_room",
        "current_room",
        "running_event"
    ]

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
        """End game, quit event loop"""
        self.running_event.set()
        self.player_msg(reason)

    async def parse_command(self, string):
        """Parse a game command"""
        cmd, *rest = string.split(None, 1)  # split first word off
        func = self.commands.get(cmd)
        if func is None:
            raise CommandException("Command not found")
        await func.invoke(*rest)

    @classmethod
    def from_dict(cls, dic, *args, **kwargs):
        """Helper function to generate a game from a JSON file"""
        rooms = cls.gen_rooms(dic.pop("rooms", []))
        return cls(*args, rooms=rooms, **{**dic, **kwargs})

    @staticmethod
    def gen_rooms(rooms):
        """Helper function to generate rooms from a JSON file"""
        globaldict = {}
        for k, v in rooms.items():
            room = Room.from_dict(v)
            globaldict[k] = room
            room.global_rooms = globaldict
        return globaldict

    @staticmethod
    def player_msg(msg):
        print(msg)

    def to_dict(self):
        return {
            "rooms": {k: v.to_dict() for k, v in self.rooms.items()},
            "basehp": self.basehp,
            "opening": self.opening,
            "start_room": self.start_room
        }

    def use_item(self, item):
        """Apply an items effects"""
        for k, v in item.effects:
            self.player.add_effect(k, **v)

    def enter_room(self, room):
        """Enter a room, runs procedures for entering, will raise if player is slowed"""
        if Status.slow in self.player.status:
            raise CommandException("You are still locked inside this room.")
        self.current_room = self.rooms[room]
        print(self.current_room)
        print(self.current_room.exits)
        if Status.blind not in self.player.status:
            print(self.current_room.item_list)
        if self.current_room.ending_room:
            self.finish("You have reached the exit, You can leave the manor now")

    async def game_loop(self):
        """Main loop of game"""
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
        """Add a cog (collection of commands to the game"""
        #print("Registering cog: {.__class__.__name__}".format(cog))
        print("Use the commad `help` to list available commands!")
        for name, member in inspect.getmembers(cog):
            if isinstance(member, Command):
                member.parent = cog
                self.commands[name] = member


if __name__ == '__main__':

    with open("game.json") as fp:
        gdata = json.load(fp)

    loop = asyncio.get_event_loop()

    game = Game.from_dict(gdata)
    game.add_cog(BaseCommands(game))

    loop.run_until_complete(game.game_loop())
