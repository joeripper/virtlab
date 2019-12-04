import sys
import os
import asyncio

import argparse
import configparser
import pathlib

from .server import Server

def main(argv):

    ap = argparse.ArgumentParser()
    ap.add_argument('CONFIG', type=pathlib.Path)
    args = ap.parse_args(argv)

    config_path = args.CONFIG

    config = configparser.ConfigParser()
    config.read(config_path)
    config = config['DEFAULT']
    

    server = Server(config)
    loop = asyncio.get_event_loop()

    try:
        try:
            loop.run_until_complete(server.amain())
        except KeyboardInterrupt:
            pass

    finally:

        tasks = asyncio.Task.all_tasks()

        for task in tasks:
            task.cancel()

        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))

    return 0

if __name__ == '__main__':

    sys.exit(main(sys.argv[1:]))
