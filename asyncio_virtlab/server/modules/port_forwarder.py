import sys
import os
import asyncio
import argparse
import requests
import aiohttp
import urllib.request

class ForwardedConnection(asyncio.Protocol):

    def __init__(self, peer):
        self.peer = peer
        self.transport = None
        self.buff = list()


    def connection_made(self, transport):
        self.transport = transport
        if len(self.buff) > 0:
            self.transport.writelines(self.buff)
            self.buff = list()

    def data_received(self, data):
        self.peer.write(data)

    def connection_lost(self, exc):
        self.peer.close()


class PortForwarder(asyncio.Protocol):
    def __init__(self, config):
        self.config = config
    
    
    def connection_made(self, transport):

        self.transport = transport
        loop = asyncio.get_event_loop()
        self.fcon = ForwardedConnection(self.transport)
        
        self.api_host = self.config['api_ip_addr']
        self.api_port = self.config['api_server_port']
        
        url = f'http://{self.api_host}:{self.api_port}/api/take'
        resp = requests.get(url).json()
        
        self.dsthost = '0.0.0.0'
        self.dstport = int(resp['vnc_port'])
        
        self.instance_id = resp['instance_id']
        
        print(self.dsthost, self.dstport, self.instance_id)
        asyncio.ensure_future(loop.create_connection(
            lambda: self.fcon,
            self.dsthost,
            5900 + self.dstport))


    def data_received(self, data):
        if self.fcon.transport is None:
            self.fcon.buff.append(data)
        else:
            self.fcon.transport.write(data)

    def connection_lost(self, exc):
        url = f'http://{self.api_host}:{self.api_port}/api/put?instance_id={self.instance_id}'
        requests.get(url)
        self.fcon.transport.close()


class ProxyServer:
    def __init__(self, config):
        self.config = config

    async def amain(self):
        self.loop = asyncio.get_running_loop()
        server = await self.loop.create_server(
                lambda: PortForwarder(self.config),
                self.config['vnc_proxy_host'],
                self.config['vnc_proxy_port']
                )
        print('VNC Proxy start')

        try:
            async with server:
                await server.serve_forever()
        
        except KeyboardInterrupt:
            print('vnc proxy stopped')
            
    def main(self, config):
        self.config = config
        asyncio.run(self.amain())




if __name__ == '__main__':
    asyncio.run(amain()) 



