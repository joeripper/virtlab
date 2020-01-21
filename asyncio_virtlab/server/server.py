import asyncio
import threading
import concurrent.futures

from .modules.policy import Policy
from .modules.pool_manager import PoolManager
from .modules.api_server import ApiServer
from .modules.port_forwarder import ProxyServer

class Server:

    def __init__(self, config):
        self.config = config


    async def amain(self):
        
        loop = asyncio.get_running_loop()

        policy = Policy(self.config)
        pool_manager = PoolManager(policy, self.config)
        api_server = ApiServer(pool_manager, self.config)
        proxy_server = ProxyServer(self.config)
        
        proxy_thread = threading.Thread(target=proxy_server.main, args=(self.config,))
        proxy_thread.start()
        
                        
        

        tasks = []
        tasks.append(asyncio.ensure_future(api_server.amain()))
        tasks.append(asyncio.ensure_future(pool_manager.amain()))



        for f in asyncio.as_completed(tasks):
            await f
            
