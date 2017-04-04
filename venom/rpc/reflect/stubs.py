from venom import Message
from venom.rpc import Stub
from venom.rpc import http
from venom.fields import Field, Repeat, String, Map, Bool


class TypeMessage(Message):
    type = String()  # TODO: enum
    items = Field('venom.rpc.reflect.openapi.TypeMessage')
    ref = String(name='$ref')
    additionalProperties = Field('venom.rpc.reflect.openapi.TypeMessage')


class FieldsMessage(Message):
    type = String()
    properties = Map(Field(TypeMessage))
    ref = String(name='$ref')


class ParameterMessage(Message):
    is_in = String(name='in')  # TODO: enum
    required = Bool()
    name = String()
    type = String()
    items = Field(TypeMessage)
    schema = Field(FieldsMessage)


class ResponseMessage(Message):
    description = String()
    schema = Field(FieldsMessage)


class ResponsesMessage(Message):
    default = Field(ResponseMessage)  # TODO: error codes


class MethodMessage(Message):
    produces = Repeat(String())  # TODO: default value for RepeatField
    responses = Field(ResponsesMessage)
    parameters = Repeat(ParameterMessage)


class InfoMessage(Message):
    version = String(default='0.0.1')  # TODO: version
    title = String()


class OpenAPISchema(Message):
    swagger = String(default='2.0')
    schemes = Repeat(String())  # TODO: default value for RepeatField
    consumes = Repeat(String())  # TODO: default value for RepeatField
    produces = Repeat(String())  # TODO: default value for RepeatField
    info = Field(InfoMessage)
    paths = Map(Map(Field(MethodMessage)))
    definitions = Map(Field(FieldsMessage))


class ReflectStub(Stub):

    @http.GET('/openapi.json')
    def get_openapi_schema(self) -> OpenAPISchema:
        raise NotImplementedError()
