import json
import os
from unittest import TestCase
from venom.fields import Int, String, Repeat, Field
from venom.message import Message
from venom.rpc import Service, http
from venom.protocol import JSON
from venom.rpc.reflect.reflect import Reflect
from venom.rpc.reflect.service import ReflectService
from venom.rpc.reflect.openapi import make_openapi_schema, OpenAPISchema

TEST_DIR = os.path.dirname(__file__)


class OpenAPITestCase(TestCase):
    def test_openapi_simple(self):
        class PetSimple(Message):
            id = Int()

        class PetServiceSimple(Service):
            class Meta:
                name = 'PetService'

            @http.GET('./pet/{id}')
            def get_pet(self, request: PetSimple) -> PetSimple:
                return request

            @http.POST('./pet')
            def create_pet_body(self, request: PetSimple) -> PetSimple:
                return request

        reflect = Reflect()
        reflect.add(PetServiceSimple)
        schema = make_openapi_schema(reflect)
        protocol = JSON(OpenAPISchema)
        schema_dict = protocol.encode(schema)
        with open(TEST_DIR + '/data/openapi_simple.json') as f:
            data = json.load(f)
            self.assertEqual(schema_dict['paths'], data['paths'])
            self.assertEqual(schema_dict['definitions'], data['definitions'])

    def test_openapi_paths(self):
        class Pet(Message):
            id = Int()
            name = String()
            tag = String()

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

        reflect = Reflect()
        reflect.add(PetServicePaths)
        schema = make_openapi_schema(reflect)
        protocol = JSON(OpenAPISchema)
        schema_dict = protocol.encode(schema)
        self.assertEqual(set(schema_dict['paths'].keys()), {'/petservice/pet', '/petservice/pet/{id}'})
        self.assertEqual(set(schema_dict['paths']['/petservice/pet'].keys()), {'post', 'get'})
        self.assertEqual(set(schema_dict['paths']['/petservice/pet/{id}'].keys()), {'post', 'get'})

    def test_repeat_field(self):
        class Gene(Message):
            gene_id = String()

        class QueryResponse(Message):
            ids = Repeat(Gene)
            gene = Field(Gene)
            repeat = Repeat(String)

        class IDMapping(Service):
            class Meta:
                version = '0.0.1b'
                name = 'ID Mapper'

            @http.GET('./query')
            def query(self) -> QueryResponse:
                return QueryResponse(ids=['1', '2', '3'])

        reflect = Reflect()
        reflect.add(IDMapping)
        reflect.add(ReflectService)
        schema = make_openapi_schema(reflect)
        protocol = JSON(OpenAPISchema)
        schema_dict = protocol.encode(schema)
        response = {
            "type": "object",
            "properties": {
                "ids": {
                    "type": "array",
                    "items": {
                        "$ref": "#/definitions/Gene"
                    }
                },
                "gene": {
                    "$ref": "#/definitions/Gene"
                },
                "repeat": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            }
        }
        self.assertEqual(schema_dict['definitions']['QueryResponse'], response)

