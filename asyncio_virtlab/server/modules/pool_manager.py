import sys
import asyncio
import os
import time
from uuid import uuid4

from aiohttp import web


class Instance:
    def __init__(self, pool, vnc_port):
        self.id = str(uuid4())
        self.process = None
        self.vnc_port = vnc_port
        self.pool = pool

        self.config = self.pool.config
        self.backing_file = self.config['backing_file']
        self.qemu_dir = self.config['qemu_dir']

        self.ready = False
        self.in_use = False

        self._stop = asyncio.Future()

    def stop(self):
        self._stop.set_result(0)

    async def create_snapshot(self):
        name = f'instance_{self.id}'
        program = 'qemu-img'
        command = f'create -f qcow2 -o backing_file={self.backing_file} {self.qemu_dir}{name}.qcow2'.split(' ')
        process = await asyncio.create_subprocess_exec(
            program,
            *command,
        )
        await process.wait()
        print('process was created')

    async def run_machine(self):

        name = f'instance_{self.id}'
        port = self.vnc_port

        program = 'qemu-system-x86_64'
        command = f'-enable-kvm -m 1024 -smp 2 -vga vmware -hda {self.qemu_dir}{name}.qcow2 -vnc 0.0.0.0:{port}'.split(' ')

        process = await asyncio.create_subprocess_exec(
            program,
            *command,
        )

        try:
            await asyncio.wait_for(process.wait(), timeout=3)

        except asyncio.TimeoutError:
            return(process)

        else:
            return(None)

    async def amain(self):

        earlest_result = None

        try:
            await self.create_snapshot()
            print(f'snapshot {self.id} created')
            self.process = await self.run_machine()
            print(f'machine {self.id} is running')

            if self.process.pid is None:
                return
            else:
                self.ready = True
#                self.pool.append(process)
                print(f'process pid: {self.process.pid}')

            try:
                while True:
                    try:

                        for f in asyncio.as_completed(
                        [self.process.wait(), self._stop],
                        timeout = 10):
                                earlest_result = await f

                    except asyncio.TimeoutError:
                        print(self.id, self.ready, self.in_use, self.vnc_port)

                    if earlest_result != None:
                        print(f'{self.id} is dead')

#                        self.pool.instances.remove(self)

                        try:
                            print(f'try to terminate {self.process.pid}')
                            self.process.terminate()
                            await asyncio.wait_for(self.process.wait(), timeout=3)

                        except asyncio.TimeoutError:
                            print(f'try to kill {self.process.pid}')
                            self.process.kill()
                            await asyncio.wait(self.process.wait())

                        self.pool.vacant_vnc_ports.append(self.vnc_port)

                        break
#                            break
#                        if task2 in done:
                            #убить процесс
#                            break
            finally:
                self.ready = False
#                self.pool.remove(process)
                # проверить статус процесса

        finally:
            os.remove(f'{self.qemu_dir}instance_{self.id}.qcow2')
            print('deleting snapshot')

class PoolManager:
    def __init__(self, policy, config):
        self.policy = policy
        self.pool = []
        self.instances = []
        self.queue = asyncio.Queue()

        self.config = config
        self.start_vnc_port = int(self.config['start_vnc_port'])

        self.lock = asyncio.Lock()

        self.vacant_vnc_ports = list(range(self.start_vnc_port + self.policy.const + 10))


    async def take(self):
        result = asyncio.Future()
        self.queue.put_nowait(('TAKE', result, None))
        return(await result)


    async def put(self, instance_id):
        result = asyncio.Future()
        self.queue.put_nowait(('PUT', result, { 'instance_id': instance_id }))
        return(await result)

    async def status(self):
        result = asyncio.Future()
        self.queue.put_nowait(('STATUS', result, None))
        return(await result)

    def apply_policy(self):
        num = self.policy.decision(self.instances)

        for i in range(num):

            vnc_port = self.vacant_vnc_ports[0]
            self.vacant_vnc_ports = self.vacant_vnc_ports[1:]

            inst = Instance(self, vnc_port)
            print('ints_created')
            asyncio.ensure_future(inst.amain())
            self.instances.append(inst)



    async def amain(self):

        async with self.lock:
            self.apply_policy()

        await asyncio.sleep(5)

        while True:

            msg_type = msg_result = msg_args = None

            try:
                msg_type, msg_result, msg_args = await asyncio.wait_for(
                                                        self.queue.get(),
                                                        timeout = 5)

            except asyncio.TimeoutError:
                pass

            if msg_type == 'TAKE':
                for inst in self.instances:
                    if inst.ready and not inst.in_use:
                        try:

                            msg_result.set_result({
                                'instance_id' : inst.id,
                                'vnc_port' : inst.vnc_port,
                            })
                            inst.in_use = True
                            break
                        except asyncio.base_futures.InvalidStateError:
                            pass

                else:
                    msg_result.set_result(None)

            elif msg_type == 'PUT':
                for inst in self.instances:
                     if inst.ready and inst.in_use and inst.id == msg_args['instance_id']:

                         inst.stop()
                         inst.ready = inst.in_use = False
                         self.vacant_vnc_ports.append(inst.vnc_port)
                         self.instances.remove(inst)
                         break

                msg_result.set_result({
                    'instance_id' : msg_args['instance_id'],
                    'status' : 'deleted',
                })

            elif msg_type == 'STATUS':
                status = []

                for inst in self.instances:
                    status.append({
                        'instance_id' : inst.id,
                        'vnc_port' : inst.vnc_port,
                        'ready' : inst.ready,
                        'in_use' : inst.in_use,
                    })

                msg_result.set_result(status)


            async with self.lock:
                self.apply_policy()
