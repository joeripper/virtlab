class Policy:
    def __init__(self, config):
        self.config = config
        self.const = int(self.config['policy_const'])

    def decision(self, instances):
        # Статичная политика
        in_use = 0
        ready = 0

        for inst in instances:
            in_use += inst.in_use
            ready += inst.ready

        return(self.const - ready)
