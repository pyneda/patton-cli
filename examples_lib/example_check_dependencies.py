from patton_client.client import PattonClient
import asyncio

queries = ['django:2.0.1', 'django:1.9 python:3.4 openssh:7.3.', ['celery:1.0', 'python:3.6'], 'python:2.7']


async def run():
    client = PattonClient()
    tasks = [asyncio.ensure_future(client.check_dependencies(q))
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
        print('  - DEPENDENCY: {}'.format(k))
        print('    - CPES: {}'.format(v['cpes']))
        print('    - CVES: {}'.format(v['cves']))


