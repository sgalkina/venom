from typing import Type, Set

from venom import Message
from venom.rpc.method import Method
from venom.rpc import Service


class Reflect(object):
    services = Set[Type[Service]]
    methods = Set[Type[Method]]
    messages = Set[Type[Message]]

    def __init__(self):
        self.services = set()
        self.methods = set()
        self.messages = set()

    def _add_method(self, method: Method):
        self.messages.add(method.request)
        self.messages.add(method.response)
        self.methods.add(method)

    def add(self, service: Service):
        for method in service.__methods__.values():
            self._add_method(method)
        self.services.add(service)
