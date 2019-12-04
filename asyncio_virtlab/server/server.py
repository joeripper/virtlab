import asyncio

from .modules.policy import Policy
from .modules.pool_manager import PoolManager
from .modules.api_server import ApiServer

class Server:

    def __init__(self, config):
        self.config = config


    async def amain(self):

        policy = Policy(self.config)
        pool_manager = PoolManager(policy, self.config)
        api_server = ApiServer(pool_manager, self.config)

        tasks = []
        tasks.append(asyncio.ensure_future(api_server.amain()))
        tasks.append(asyncio.ensure_future(pool_manager.amain()))


        for f in asyncio.as_completed(tasks):
            await f
