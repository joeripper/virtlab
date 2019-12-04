import sys
import asyncio
import os
import time
from uuid import uuid4

from aiohttp import web

class ApiServer:

    def __init__(self, pool_manager, config):

        self.config = config
        self.tcp_port = int(self.config['api_server_port'])

        self.pool_manager = pool_manager
        self.lock = asyncio.Lock()


    async def take(self, request):

        resp = await self.pool_manager.take()
        return web.json_response(resp)

    async def put(self, request):

        data = dict(request.query)

        try:
            resp = await self.pool_manager.put(data['instance_id'])
#            resp = {
#                'instance_id' : 'deleted',
#            }
            return web.json_response(resp)

        except KeyError:
            return web.Response(text='unknown keys', status=400)

    async def status(self, request):
        resp = await self.pool_manager.status()
        return web.json_response(resp)

    async def app(self):

        app = web.Application()
        app.add_routes([
            web.get('/api/take', self.take),
            web.get('/api/put', self.put),
            web.get('/api/status', self.status),
        ])

        return(app)

    async def amain(self):

        app = await self.app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.tcp_port)
        await site.start()
        print('site is running')
