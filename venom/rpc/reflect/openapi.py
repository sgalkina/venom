from itertools import groupby
from collections import defaultdict
from venom.rpc.reflect.reflect import Reflect
from venom.protocol import JSON
from venom.fields import Field, Repeat, RepeatField, String, Map, Bool
from venom import Message
from venom.message import field_names, fields
from venom.rpc.method import Method, HTTPFieldLocation


DEFINITIONS = 'definitions'
MESSAGE = 'message'
ARRAY = 'array'


# TODO: other types
TYPES = {
    'str': 'string',
    'int': 'integer',
    'float': 'double',
    'bool': 'boolean',
}

PATH_PARAMETER = {
    'is_in': 'path',
    'required': True
}

BODY_PARAMETER = {
    'is_in': 'body',
}

QUERY_PARAMETER = {
    'is_in': 'query',
}


class TypeMessage(Message):
    type = String()  # TODO: enum
    items = Field('venom.rpc.reflect.openapi.TypeMessage')
    ref = String(name='$ref')


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


def field_type(field: Field) -> str:
    if isinstance(field, RepeatField):
        return ARRAY
    return TYPES.get(field.type.__name__, MESSAGE)


def type_message(field: Field) -> TypeMessage:
    f_type = field_type(field)
    if f_type == MESSAGE:
        return TypeMessage(ref=reference_string(field.type))
    if f_type == ARRAY:
        return TypeMessage(type=f_type, items=type_message(field.items))
    return TypeMessage(type=f_type)


def reference_string(message: Message) -> str:
    name = message.__meta__.name
    if name == 'Empty':
        return ''
    return '#/{}/{}'.format(DEFINITIONS, name)


def parameter_common(field: Field) -> dict:
    result = {'name': field.name}
    f_type = type_message(field)
    protocol = JSON(type(f_type))
    result.update(protocol.encode(f_type))
    return result


def parameters_path(method: Method) -> list:
    fields = [getattr(method.request, f) for f in method.http_path_parameters()]
    return [{**PATH_PARAMETER, **parameter_common(f)} for f in fields]


def parameters_query(method: Method) -> list:
    fields = [getattr(method.request, f)
              for f in method.http_field_locations()[HTTPFieldLocation.QUERY]]
    return [{**QUERY_PARAMETER, **parameter_common(f)} for f in fields]


def parameters_body(method: Method) -> list:
    body_fields = method.http_field_locations()[HTTPFieldLocation.BODY]
    if not body_fields:
        return []
    fields = {f: getattr(method.request, f) for f in body_fields}
    if fields == method.request.__fields__:
        param = dict(
            name=method.request.__meta__.name,
            schema=TypeMessage(ref=reference_string(method.response))
        )
    else:
        param = dict(
            name=method.name + '_body',
            schema=fields_message(fields.values())
        )
    return [{**BODY_PARAMETER, **param}]


def to_message(param_data: dict) -> ParameterMessage:
    return ParameterMessage(
        **{k: param_data[k] for k in field_names(ParameterMessage) if k in param_data}
    )


def parameters_messages(m: Method) -> list:
    return list(map(to_message, parameters_body(m) + parameters_path(m) + parameters_query(m)))


def response_message(method: Method) -> ResponseMessage:
    return ResponseMessage(
        description=method.options.get('description', ''),
        schema=FieldsMessage(ref=reference_string(method.response))
    )


def method_message(method: Method) -> MethodMessage:
    return MethodMessage(
        produces=['application/json'],  # TODO: other formats
        responses=ResponsesMessage(default=response_message(method)),
        parameters=parameters_messages(method)
    )


def methods_messages_map(reflect: Reflect) -> dict:
    result = defaultdict(dict)
    for k, group in groupby(reflect.methods, key=lambda a: a.http_path):
        for m in group:
            result[k.strip('.')][m.http_method.value.lower()] = method_message(m)
    return result


def fields_message(fields) -> FieldsMessage:
    return FieldsMessage(
        type='object',
        properties={
            v.name: type_message(v) for v in fields
        }
    )


def field_types_message(message: Message) -> FieldsMessage:
    return fields_message(fields(message))


def messages(reflect: Reflect) -> dict:
    return {
        m.__meta__.name: field_types_message(m) for m in reflect.messages
        if not m.__meta__.name == 'Empty'
        }


def service_collection_name(services: set()) -> str:
    return '; '.join([s.__meta__.name for s in services])


def make_openapi_schema(reflect: Reflect) -> OpenAPISchema:
    return OpenAPISchema(
        swagger='2.0',
        schemes=['http'],
        consumes=['application/json'],
        produces=['application/json'],
        info=InfoMessage(version='0.0.1', title=service_collection_name(reflect.services)),
        paths=methods_messages_map(reflect),
        definitions=messages(reflect)
    )
