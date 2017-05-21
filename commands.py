import inspect

from shared import CommandException, utils_get


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


class BaseCommands:

    def __init__(self, game):
        self.game = game
        self.player = game.player
        self.items = game.player.items

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
        item = utils_get(self.items, name=item)
        if item is None:
            raise CommandException("This item does not exist")
        item.apply(self.player)
        self.items.remove(item)

    @Command
    def collect(self, item):
        """Collect an item."""
        item = utils_get(self.game.current_room.items, name=item)
        if item is None:
            raise CommandException("This item does not exist")
        self.player.add_item(item)
        self.game.current_room.items.remove(item)

    @Command
    def list(self):
        """List your collected items."""
        self.game.player_msg("\nYou have the following items:")
        if not self.items:
            raise CommandException("You currently have no items")
        for i in self.items:
            self.game.player_msg(f"\t{i}")

    @Command
    def help(self):
        """Display the help."""
        format_str = "{0.name}: {0.desc}"
        print("Commands:")
        for i in self.game.commands.values():
            print(format_str.format(i))
