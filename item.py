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
        state = self.state if self.used else ""
        return "{0.name} | {0.description} | {1}".format(self, state)
