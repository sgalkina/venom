import json
import os
from unittest import TestCase
from venom.fields import Int, String
from venom.message import Message
from venom.rpc import Service, http
from venom.rpc.reflect.reflect import Reflect
from venom.rpc.reflect.openapi import make_openapi_schema

TEST_DIR = os.path.dirname(__file__)


class PetSimple(Message):
    id = Int()


class Pet(Message):
    id = Int()
    name = String()
    tag = String()


class PetServiceSimple(Service):
    class Meta:
        name = 'PetService'

    @http.GET('./pet/{id}')
    def get_pet(self, request: PetSimple) -> PetSimple:
        return request

    @http.POST('./pet')
    def create_pet_body(self, request: PetSimple) -> PetSimple:
        return request


class PetServicePaths(Service):
    class Meta:
        name = 'PetService'

    @http.GET('./pet/{id}', description='Get the pet')
    def get_pet(self, request: Pet) -> Pet:
        return Pet(request.id, 'Berry', 'cat')

    @http.POST('./pet/{id}', description='Post the pet with path id')
    def create_pet(self, request: Pet) -> Pet:
        return request

    @http.POST('./pet', description='Post the pet with body params')
    def create_pet_body(self, request: Pet) -> Pet:
        return request

    @http.GET('./pet', description='Get the pet with query arguments')
    def query_pet(self, request: Pet) -> Pet:
        return request


class OpenAPITestCase(TestCase):

    def test_openapi_simple(self):
        reflect = Reflect()
        reflect.add(PetServiceSimple)
        schema = make_openapi_schema(reflect)
        with open(TEST_DIR + '/data/openapi_simple.json') as f:
            data = json.load(f)
            self.assertEqual(schema, data)

    def test_openapi_paths(self):
        reflect = Reflect()
        reflect.add(PetServicePaths)
        schema = make_openapi_schema(reflect)
        self.assertEqual(set(schema['paths'].keys()), {'/pet', '/pet/{id}'})
        self.assertEqual(set(schema['paths']['/pet'].keys()), {'post', 'get'})
        self.assertEqual(set(schema['paths']['/pet/{id}'].keys()), {'post', 'get'})
