from typing import Type, Set

from venom import Message
from venom.message import fields
from venom.rpc.method import Method
from venom.fields import Field, RepeatField, MapField
from venom.rpc import Service


class Reflect(object):
    services : Set[Service]
    methods : Set[Type[Method]]
    messages : Set[Type[Message]]

    def __init__(self):
        self.services = set()
        self.methods = set()
        self.messages = set()

    def _add_field(self, field: Field):
        if type(field) == Field:
            self._add_message(field.type)
        if type(field) == RepeatField:
            self._add_field(field.items)
        if type(field) == MapField:
            self._add_field(field.values)

    def _add_message(self, message: Message):
        if message not in self.messages:
            self.messages.add(message)
            for field in fields(message):
                self._add_field(field)

    def _add_method(self, method: Method):
        self._add_message(method.request)
        self._add_message(method.response)
        self.methods.add(method)

    def add(self, service: Service):
        # if service.__meta__.name == 'reflect':
        #     return
        for method in service.__methods__.values():
            self._add_method(method)
        self.services.add(service)
