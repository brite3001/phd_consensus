import aiozmq
import zmq
import asyncio
from async_timeout import timeout


async def Client():
    # 1) Initialise the sockets
    sub_socket = await aiozmq.create_zmq_stream(zmq.SUB, connect="tcp://127.0.0.1:5555")
    req_socket = await aiozmq.create_zmq_stream(zmq.REQ, connect="tcp://127.0.0.1:5556")

    # 2) Write the Event loops to use the sockets
    async def sub_event_loop(sub_socket: zmq.SUB):
        sub_socket.transport.subscribe(b"cool_beans")

        while True:
            msg = await sub_socket.read()
            print(f"[CLIENT] Received message {msg}")

    async def req_event_loop(req_socket: zmq.REQ):
        while True:
            req_socket.write([b"Hello from the Client!"])

            # Wait for response, then timeout
            try:
                async with timeout(5):
                    msg = await req_socket.read()
                    print(f"[CLIENT] Received response: {msg}")
            except asyncio.TimeoutError as e:
                print(f"No response received: {e}")

            await asyncio.sleep(5)

    # 3) Write the starter function
    async def start_client():
        await asyncio.gather(sub_event_loop(sub_socket), req_event_loop(req_socket))

    # 4) Await the starter, and free the sockets on close.
    print("[SERVER] Starting...")
    await start_client()
    sub_socket.close()
    req_socket.close()


async def Server():
    # 1) Initialise the sockets
    pub_socket = await aiozmq.create_zmq_stream(zmq.PUB, bind="tcp://*:5555")
    rep_socket = await aiozmq.create_zmq_stream(zmq.REP, bind="tcp://*:5556")

    # 2) Write the event loops
    async def pub_event_loop(pub_socket: zmq.PUB):
        while True:
            pub_socket.write([b"cool_beans", b"Message from publisher A"])
            await asyncio.sleep(3)

    async def rep_event_loop(rep_socket: zmq.REP):
        while True:
            msg = await rep_socket.read()
            print(f"[SERVER] Received message: {msg}")

            rep_socket.write([b"Hello Client!"])

    # 3) Write the starter function
    async def start_server():
        await asyncio.gather(pub_event_loop(pub_socket), rep_event_loop(rep_socket))

    # 4) Await starter and close sockets
    print("[CLIENT] Starting...")
    await start_server()
    pub_socket.close()
    rep_socket.close()


async def main():
    print("Starting Server")

    s1 = asyncio.create_task(Server())
    c1 = asyncio.create_task(Client())

    await asyncio.gather(s1, c1)


if __name__ == "__main__":
    asyncio.run(main())
