#!/usr/bin/env python3
import sys
import os
import asyncio
from mfcauto import Client
import classes.config

conf = classes.config.Config(os.path.join(sys.path[0], "config.conf"))

async def main(loop):
    if len(sys.argv) != 2:
        print('Must include a models name. ie: add.py AspenRae')
        sys.exit(1)

    model_name = sys.argv[1]

    print("Querying MFC for {}".format(model_name))
    client = Client(loop)
    await client.connect(False)
    msg = await client.query_user(model_name)
    client.disconnect()
    print()

    if msg is None:
        print("User not found. Please check your spelling and try again")
    else:
        if msg['uid'] in conf.filter.wanted.dict.keys():
            print('{} is already in the wanted list. Models UID is {}'.format(model_name, msg['uid']))
        else:
            conf.filter.wanted.set_data(msg['uid'], custom_name=model_name)
            print("{} with UID {} has been added to the list".format(model_name, msg['uid']))
        print()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))
    loop.close()
