from alsdkdefs import OpenAPIKeyWord


def derive_type_from_decomposed_schema(schema):
    oneof = schema.get(OpenAPIKeyWord.ONE_OF)
    anyof = schema.get(OpenAPIKeyWord.ANY_OF)
    allof = schema.get(OpenAPIKeyWord.ALL_OF)

    if oneof or anyof or allof:
        # Attempt to find type in the decomposed schema
        find_type = [t.get('type') for t in allof or anyof or oneof if t.get('type')]
        return find_type[0] if find_type else None
    else:
        return None
