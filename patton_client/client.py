from aiohttp import ClientSession
import aiohttp
import asyncio
import json
import logging
from typing import List, Dict
from .libraries_parsers import parse_dependencies
from patton_client import PattonRunningConfig, PCServerResponseException, PCException, PCInvalidFormatException, \
    check_dependencies, get_data_from_sources
from patton_client.api_queries import _prepare_query
from patton_client.banners_services import parse_banners

log = logging.getLogger("patton-cli")


class PattonClient:
    def __init__(self, patton_host: str='patton.owaspmadrid.org:8000', aiohttp_session: ClientSession=None, loop=None,
                 skip_on_fail: bool=False, quiet_mode: bool=True):
        self._patton_host = patton_host
        self._skip_on_fail = skip_on_fail
        self._quiet_mode = quiet_mode
        self._loop = loop or asyncio.get_event_loop()
        self._session = aiohttp_session
        if not isinstance(self._session, ClientSession):
            self._session = ClientSession(loop=self._loop)

    def get_config(self, _input: (List[str], str), source_type: str, banner_type: str=False,
                   follow_checking: bool=False):
        """ Returns a PattonRunningConfig instance """
        return PattonRunningConfig(nargs_input=_input,
                                   patton_host=self._patton_host,
                                   skip_on_fail=self._skip_on_fail,
                                   display_format='table',
                                   follow_checking=follow_checking,
                                   quiet_mode=self._quiet_mode,
                                   data_from_file=None,
                                   banner_type=banner_type,
                                   source_type=source_type,
                                   output_file=None
                                   )

    async def check_banners(self, _input: List[str], source_type:str='auto', banner_type: str='auto',
                            follow_checking: bool=False):
        #if not isinstance(_input, list):
        #    raise PCInvalidFormatException('Input should be a list of banners')
        patton_config = self.get_config(_input=_input,
                                        source_type=source_type,
                                        banner_type=banner_type,
                                        follow_checking=follow_checking)
        if patton_config.follow_checking:
            # dependencies = get_data_from_sources(patton_config)
            pass
        else:
            input_banners = get_data_from_sources(patton_config,
                                                  dependency_or_banner="banner")
            # Select the banner type parser and get dependencies
            parsed_banners = list(parse_banners(input_banners, patton_config)) # set to list
            return await self._check_banners_in_patton(parsed_banners, patton_config)

    async def check_dependencies(self, _input: (str, List), source_type: str='auto'):
        if isinstance(_input, list):
            nargs_input = _input
        elif isinstance(_input, str):
            nargs_input = _input.split(' ')
        else:
            raise PCInvalidFormatException('Invalid input, should be a list or a space separated string')
        patton_config = self.get_config(_input=nargs_input,
                                        source_type=source_type)

        dependencies = get_data_from_sources(patton_config,
                                             dependency_or_banner="banner")

        dependencies = parse_dependencies(dependencies, patton_config)

        if len(dependencies) > 300:
            log.error(f"You're trying to test '{len(dependencies)}' dependencies. "
                      f"Patton server is limited (by default) to the first 300 "
                      f"libraries. Only first 300 will be tested. ")

        if len(dependencies) > 100:
            log.error("Patton server has less accuracy when you try more than 100"
                      "libraries per request. It's advisable to not exceed this "
                      "limit if you want more accurate results")
        return await self._check_dependencies_in_patton(dependencies, patton_config)

    async def do_api_query(self, dep_list: Dict, patton_url: str, patton_config: PattonRunningConfig) -> Dict:
        """ Performs the api query using the current ClientSession """
        if not patton_url.startswith("http"):
            patton_url = f"http://{patton_url}"

        logging.warning('dep_list in do_apy_query: {} to {}'.format(dep_list, patton_url))
        async with self._session.post(
                patton_url,
                data=json.dumps(dep_list),
                headers={'content-type': 'application/json'}) as resp:
            if resp.status == 200:
                server_response = await resp.json()
            else:
                server_response = await resp.text()
                raise PCServerResponseException(
                    f"Server error: {server_response}")

        return server_response

    async def _check_dependencies_in_patton(self, dep_list: List[str],
                                            patton_config: PattonRunningConfig) \
            -> Dict:

        patton_url = f'{patton_config.patton_host}/api/v1/' \
                     f'check-dependencies?cpeDetailed=1'

        query_data = _prepare_query(dep_list, patton_config)
        query_data["source"] = patton_config.source_type

        try:
            return await self.do_api_query(query_data, patton_url, patton_config)
        except (aiohttp.client_exceptions.ServerDisconnectedError,
                aiohttp.client_exceptions.ClientConnectorError):
            raise PCException("Can't connect to Patton Server")

    async def _check_banners_in_patton(self, dep_list: List[str], patton_config: PattonRunningConfig) -> Dict:
        patton_url = f'{patton_config.patton_host}/api/v1/check-banners'

        try:
            return await self.do_api_query(dep_list, patton_url, patton_config)
        except aiohttp.client_exceptions.ServerDisconnectedError:
            raise PCException("Can't connect to Patton Server")

    async def close_session(self):
        await self._session.close()
        log.debug('AioHTTP Client Session has been closed')

