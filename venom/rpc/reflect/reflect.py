from typing import Type, Set

from venom import Message
from venom.message import fields
from venom.rpc.method import Method
from venom.fields import Field, RepeatField
from venom.rpc import Service


class Reflect(object):
    services : Set[Type[Service]]
    methods : Set[Type[Method]]
    messages : Set[Type[Message]]

    def __init__(self):
        self.services = set()
        self.methods = set()
        self.messages = set()

    def _add_message(self, message: Message):
        for field in fields(message):
            if type(field) == Field:
                self._add_message(field.type)
        self.messages.add(message)

    def _add_method(self, method: Method):
        self._add_message(method.request)
        self._add_message(method.response)
        self.methods.add(method)

    def add(self, service: Service):
        for method in service.__methods__.values():
            self._add_method(method)
        self.services.add(service)
