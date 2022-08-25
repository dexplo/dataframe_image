# taken directly from asyncio runners.py module in python 3.7+
# needed for python 3.6

import asyncio


def _cancel_all_tasks(loop):
    to_cancel = asyncio.Task.all_tasks(loop)
    if not to_cancel:
        return

    for task in to_cancel:
        task.cancel()

    loop.run_until_complete(
        asyncio.tasks.gather(*to_cancel, loop=loop, return_exceptions=True)
    )

    for task in to_cancel:
        if task.cancelled():
            continue
        if task.exception() is not None:
            loop.call_exception_handler(
                {
                    "message": "unhandled exception during asyncio.run() shutdown",
                    "exception": task.exception(),
                    "task": task,
                }
            )


def run(main):
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.set_debug(False)
        return loop.run_until_complete(main)
    finally:
        asyncio.set_event_loop(None)
        loop.close()


# def run(main):
#     loop = asyncio.new_event_loop()
#     try:
#         asyncio.set_event_loop(loop)
#         loop.set_debug(False)
#         return loop.run_until_complete(main)
#     finally:
#         try:
#             _cancel_all_tasks(loop)
#             loop.run_until_complete(loop.shutdown_asyncgens())
#         finally:
#             asyncio.set_event_loop(None)
#             loop.close()
