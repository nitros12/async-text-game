from shared import Status


class Player:
    """Base class for a player, holds health, items and status."""

    __slots__ = [
        "loop",
        "_hp",
        "status",
        "game",
        "is_active",
        "items"
    ]

    def __init__(self, basehp, game, loop):
        self.loop = loop
        self._hp = basehp
        self.status = Status(0)
        self.game = game
        self.is_active = True
        self.items = []

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
        """Slow a player, preventing them from changing rooms."""
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
        self.status_display.set_stat("hp", self.hp)
        if self.hp < 0:
            self.game.finish("You died")

    def add_effect(self, *effects):
        for i in effects:
            type_ = i.pop("type")
            if type_ == "blind":
                self.blind(**i)
            elif type_ == "slow":
                self.slow(**i)
            elif type_ == "hurt":
                self.hurt(**i)

    def notify(self, msg):
        self.game.player_msg(msg)

    def add_item(self, item):
        self.items.append(item)
        self.notify(f"You picked up a {item.name}!")
