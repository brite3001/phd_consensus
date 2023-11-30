from attrs import define
import asyncio
import aiozmq
import zmq


@define
class Node:
    id: str
    listen_addr: str

    # use aiozmq :)
