from typing import Type

import aiohttp

from venom.exceptions import Error, ErrorResponse
from venom.rpc.comms import BaseClient
from venom.rpc.method import Method, HTTPVerb, HTTPFieldLocation
from venom.protocol import JSON, Protocol, string_decoder

try:
    from aiohttp import web, ClientSession
except ImportError:
    raise RuntimeError("You must install the 'aiohttp' package to use the AioHTTP features of Venom RPC")


def _route_handler(venom: 'venom.rpc.Venom',
                   service: Type['venom.rpc.Service'],
                   rpc: Method,
                   protocol_factory: Type[Protocol]):
    rpc_request = protocol_factory(rpc.request)
    rpc_response = protocol_factory(rpc.response)
    rpc_error_response = protocol_factory(ErrorResponse)

    http_status = rpc.http_status

    http_field_locations = rpc.http_field_locations()
    http_request_body = http_field_locations[HTTPFieldLocation.BODY]
    http_request_query = [(name, string_decoder(rpc.request.__fields__[name], protocol_factory))
                          for name in http_field_locations[HTTPFieldLocation.QUERY]]

    http_request_path = [(name, string_decoder(rpc.request.__fields__[name], protocol_factory))
                         for name in http_field_locations[HTTPFieldLocation.PATH]]

    async def handler(http_request):
        try:
            if http_request_body:
                request = rpc_request.unpack(await http_request.read(), include=http_request_body)
            else:
                request = rpc.request()
                for name, decode in http_request_query:
                    try:
                        request[name] = decode(http_request.url.query[name])
                    except KeyError:
                        pass

            for name, decode in http_request_path:
                try:
                    request[name] = decode(http_request.match_info[name])
                except KeyError:
                    pass

            instance = venom.get_instance(service)
            response = await rpc.invoke(instance, request)
            return web.Response(body=rpc_response.pack(response),
                                content_type=rpc_response.mime,
                                status=http_status)
        except Error as e:
            return web.Response(body=rpc_error_response.pack(e.format()),
                                content_type=rpc_error_response.mime,
                                status=e.http_status)
    return handler


def create_app(venom: 'venom.rpc.Venom',
               app: web.Application = None,
               protocol_factory: Type[Protocol] = JSON,
               loop=None):
    if app is None:
        app = web.Application(loop=loop)

    for service, rpc in venom.iter_methods():
        http_rule = rpc.http_rule(service)
        app.router.add_route(rpc.http_verb.value, http_rule, _route_handler(venom, service, rpc, protocol_factory))

    return app


class Client(BaseClient):
    def __init__(self,
                 stub: Type['venom.rpc.Service'],
                 base_url: str,
                 *,
                 protocol_factory: Type[Protocol] = None,
                 session: aiohttp.ClientSession = None,
                 **session_kwargs):
        super().__init__(stub, protocol_factory=protocol_factory)
        self._base_url = base_url
        if session is None:
            self._session = aiohttp.ClientSession(**session_kwargs)
        else:
            self._session = session

    async def invoke(self,
                     stub: 'venom.rpc.Service',
                     rpc: 'venom.rpc.stub.RPC',
                     request: 'venom.message.Message',
                     *,
                     context: 'venom.RequestContext' = None,
                     loop: 'asyncio.BaseEventLoop' = None,
                     timeout: int = None):

        # TODO optional timeouts

        if rpc.http_path_params():
            url = self._base_url + rpc.http_rule(stub).format(**request)
        else:
            url = self._base_url + rpc.http_rule(stub)

        # TODO support fields in query string

        headers = None
        if rpc.http_verb in (HTTPVerb.POST, HTTPVerb.PUT, HTTPVerb.PATCH):
            headers = {'content-type': self._protocol_factory.mime}

        body = self._protocol_factory(rpc.request).pack(request)

        async with self._session.request(rpc.http_verb.value.lower(), url, headers=headers, data=body) as response:
            if 200 <= response.status < 400:
                return self._protocol_factory(rpc.response).unpack(await response.read())
            else:
                self._protocol_factory(ErrorResponse).unpack(await response.read()).raise_()

    # XXX not sure if session should be opened for each request, and why an unclosed session is such a bad thing.
    def __del__(self):
        if self._session:
            self._session.close()
