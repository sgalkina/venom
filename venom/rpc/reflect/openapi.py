from copy import deepcopy
from itertools import groupby
from collections import defaultdict
from venom.rpc.reflect.reflect import Reflect
from venom.rpc.reflect.stubs import OpenAPISchema
from venom.fields import Field
from venom import Message
from venom.rpc.method import Method, HTTPFieldLocation


DEFINITIONS = 'definitions'


# TODO: other types
TYPES = {
    'str': 'string',
    'int': 'integer',
    'float': 'double',
    'bool': 'boolean',
}

PATH_PARAMETER = {
    'in': 'path',
    'required': True
}

BODY_PARAMETER = {
    'in': 'body',
}

QUERY_PARAMETER = {
    'in': 'query',
}

META_INFO = {
    'swagger': '2.0',
    'info': {
        'version': '0.0.1',  # TODO: version of the collection of services
        'title': 'API',  # TODO: name of the collection of services
    },
    'schemes': [
        'http'
    ],
    'consumes': [
        'application/json'
    ],
    'produces': [
        'application/json'
    ],
}


def get_type(field: Field):
    return TYPES[field.type.__name__]


# TODO: get message name
def reference(message: Message) -> dict:
    name = message.__meta__.name
    if name == 'Empty':
        return {}
    return {'$ref': '#/{}/{}'.format(DEFINITIONS, name)}


def parameter_common(field: Field) -> dict:
    return {'name': field.name, 'type': get_type(field)}


def parameters_path(method: Method) -> list:
    fields = [getattr(method.request, f) for f in method.http_path_params()]
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
            schema=reference(method.request)
        )
    else:
        param = dict(
            name=method.name + '_body',
            schema=schema_fields(fields)
        )
    return [{**BODY_PARAMETER, **param}]


def parameters_schema(m: Method) -> list:
    return parameters_body(m) + parameters_path(m) + parameters_query(m)


# TODO: error codes
def schema_method(method: Method) -> dict:
    return {
        'produces': [
            'application/json'  # TODO: other formats
        ],
        'responses': {
            'default': {
                'description': method.options.get('description', ''),
                'schema': reference(method.response)
            }
        },
        'parameters': parameters_schema(method),
    }


def schema_methods(reflect: Reflect) -> dict:
    result = defaultdict(dict)
    for k, group in groupby(reflect.methods, key=lambda a: a.http_rule()):
        for m in group:
            result[k.strip('.')][m.http_verb.value.lower()] = schema_method(m)
    return result


def schema_fields(fields: dict) -> dict:
    return {
        'type': 'object',
        'properties': {
            k: dict(type=get_type(v)) for k, v in fields.items()
            }
    }


# TODO: get fields dict
def schema_message(message: Message) -> dict:
    return schema_fields(message.__fields__)


def schema_messages(reflect: Reflect) -> dict:
    return {
        m.__meta__.name: schema_message(m) for m in reflect.messages
        if not m.__meta__.name == 'Empty'
        }


def make_openapi_schema(reflect: Reflect) -> OpenAPISchema:
    result = deepcopy(META_INFO)
    result.update({
        'paths': schema_methods(reflect),
        DEFINITIONS: schema_messages(reflect),
    })
    return result

