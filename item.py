class Item:
    __slots__ = [
        "name",
        "description",
        "effects"
    ]

    def __init__(self, name, description, effects=[]):
        self.name = name  # string
        self.description = description  # string
        self.effects = effects  # [{name=name, effect_args=stuff)]

    def apply(self, player):
        player.add_effect(*self.effects)

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
        return "{0.name} | {0.description}".format(self)
