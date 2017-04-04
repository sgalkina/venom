from itertools import groupby
from functools import singledispatch
from collections import defaultdict
from venom.rpc.reflect.reflect import Reflect
from venom.rpc.reflect.stubs import TypeMessage, MethodMessage, \
    ParameterMessage, ResponsesMessage, ResponseMessage, \
    FieldsMessage, InfoMessage, OpenAPISchema
from venom.protocol import JSON
from venom.fields import Field, RepeatField, MapField
from venom import Message
from venom.message import field_names, fields
from venom.rpc.method import Method, HTTPFieldLocation


DEFINITIONS = 'definitions'
DESCRIPTION = 'description'
MESSAGE = 'message'
ARRAY = 'array'
MAP = 'map'


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


def description_param(field: Field) -> dict:
    if DESCRIPTION in field.options:
        return {DESCRIPTION: field.options.get(DESCRIPTION)}
    return {}


@singledispatch
def type_message(field: Field) -> TypeMessage:
    f_type = field.type.__name__
    if f_type not in TYPES:
        return TypeMessage(ref=reference_string(field.type))
    return TypeMessage(
        type=TYPES[f_type],
        **description_param(field)
    )


@type_message.register(RepeatField)
def type_message_repeat(field: RepeatField) -> TypeMessage:
    return TypeMessage(
        type=ARRAY,
        items=type_message(field.items),
        **description_param(field)
    )


@type_message.register(MapField)
def type_message_map(field: MapField) -> TypeMessage:
    return TypeMessage(
        type='object',
        additionalProperties=type_message(field.values),
        **description_param(field)
    )


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
        description=method.options.get(DESCRIPTION, ''),
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


def fields_message(fields, description='') -> FieldsMessage:
    params = dict(
        type='object',
        properties={
            v.name: type_message(v) for v in fields
        }
    )
    if description:
        params[DESCRIPTION] = description
    return FieldsMessage(**params)


def field_types_message(message: Message) -> FieldsMessage:
    return fields_message(
        fields(message),
        description=message.__meta__.get(DESCRIPTION, '')
    )


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
