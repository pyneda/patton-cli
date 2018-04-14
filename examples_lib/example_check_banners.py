from patton_client.client import PattonClient
import asyncio

queries = [['Apache httpd extrainfo: SSL-only mode'], ['SSH-2.0-OpenSSH_7.4p1 Debian-10+deb9u3']]


async def run():
    client = PattonClient()
    tasks = [asyncio.ensure_future(client.check_banners(q))
             for q in queries
             ]
    results = await asyncio.gather(*tasks)
    await client.close_session()
    return results


loop = asyncio.get_event_loop()
results = loop.run_until_complete(run())
for i, query in enumerate(results):
    print('QUERY {}'.format(i))
    for k, v in query.items():
        print('  - BANNER: {}'.format(k))
        print(v)
