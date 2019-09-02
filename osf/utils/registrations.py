from django.apps import apps

"""
Old workflow uses DraftRegistration.registration_metadata and Registration.registered_meta.
New workflow uses DraftRegistration.registration_responses and Registration.registration_responses.

Both workflows need to be accommodated for the foreseeable future, so writing to one field
needs to write to the other field.

Contains "flatten_registration_metadata" for converting from old to new, and
"expand_registration_responses" for converting from new to old.
"""

# For flatten_registration_metadata
def extract_file_info(file):
    """
    Extracts name and file_id from the nested "extras" dictionary.
    Pulling name from selectedFileName and the file_id from the viewUrl.

    Some weird data here...such as {u'selectedFileName': u'No file selected'}
    :returns dictionary {'file_name': <file_name>, 'file_id': <file__id>}
    if both exist, otherwise {}
    """
    if file:
        name = file.get('selectedFileName', '')
        # viewUrl is the only place the file id is accurate.  On a
        # registration, the other file ids in extra refer to the original
        # file on the node, not the file that was archived on the reg
        view_url = file.get('viewUrl', '')
        file__id = view_url.split('/')[5] if view_url else ''
        if name and file__id:
            return {
                'file_name': name,
                'file_id': file__id
            }
    return {}

# For flatten_registration_metadata
def format_extra(extra):
    """
    Pulls file names, and file ids out of "extra"
    Note: "extra" is typically an array, but for some data, it's a dict

    :returns array of dictionaries, of format
    [{'file_name': <filename>, 'file_id': <file__id>}]
    """
    files = []
    if isinstance(extra, list):
        for file in extra:
            file_info = extract_file_info(file)
            files.append(file_info)
    else:
        file_info = extract_file_info(extra)
        if file_info:
            files.append(file_info)
    return files

# For flatten_registration_metadata
def get_value_or_extra(nested_response, block_type, key, keys):
    """
    Sometimes the relevant information is stored under "extra" for files,
    otherwise, "value".

    :params, nested dictionary
    :block_type, string, current block type
    :key, particular key in question
    :keys, array of keys remaining to recurse through to find the user's answer
    :returns array (files or multi-response answers) or a string IF deepest level of nesting,
    otherwise, returns a dictionary to get the next level of nesting.
    """
    keyed_value = nested_response.get(key, '')
    # No guarantee that the key exists in the dictionary
    if isinstance(keyed_value, basestring):
        return keyed_value

    # If we are on the most deeply nested key (no more keys left in array),
    # and the block type is "file-input", the information we want is
    # stored under extra
    if block_type == 'file-input' and not keys:
        extra = format_extra(keyed_value.get('extra', []))
        return extra
    else:
        value = keyed_value.get('value', '')
        return value

# For flatten_registration_metadata
def get_nested_answer(nested_response, block_type, keys):
    """
    Recursively fetches the nested response in registered_meta.

    :params nested_response dictionary
    :params keys array, of nested question_ids: ["recommended-analysis", "specify", "question11c"]
    :returns array (files or multi-response answers) or a string
    """
    if isinstance(nested_response, dict):
        key = keys.pop(0)
        # Returns the value associated with the given key
        value = get_value_or_extra(nested_response, block_type, key, keys)
        return get_nested_answer(value, block_type, keys)
    else:
        # Once we've drilled down through the entire dictionary, our nested_response
        # should be an array or a string
        return nested_response

# For flatten_registration_metadata
def get_schema(resource):
    """
    Fetches the RegistrationSchema from the resource

    :param resource: DraftRegistration or Registration
    :returns RegistrationSchema
    """
    if getattr(resource, 'registered_meta', None):
        # Registrations
        RegistrationSchema = apps.get_model('osf.RegistrationSchema')
        schema_id = resource.registered_meta.keys()[0] if resource.registered_meta.keys() else None
        return RegistrationSchema.objects.get(_id=schema_id) if schema_id else None
    else:
        # DraftRegistrations
        return resource.registration_schema

# For flatten_registration_metadata
def get_registration_metadata(resource, schema=None):
    """
    Fetches the original registration responses
    :param resource: DraftRegistration or Registration
    :returns dictionary, registration_metadata
    """
    if getattr(resource, 'registered_meta', None):
        # Registration - registered_meta is under the schema key
        return resource.registered_meta.get(schema._id, {})
    # Draft Registration
    return resource.registration_metadata

def flatten_registration_metadata(resource):
    """
    Extracts questions/nested registration_responses - makes use of schema block `registration_response_key`
    and block_type to pull out the nested registered_meta

    For example, if the registration_response_key = "description-methods.planned-sample.question7b",
    this will recurse through the registered_meta, looking for each key, starting with "description-methods",
    then "planned-sample", and finally "question7b", returning the most deeply nested value corresponding
    with the final key to flatten the dictionary.
    :resource, DraftRegistration or Registration
    :returns dictionary, registration_responses, flattened dictionary with registration_response_keys
    top-level
    """
    schema = get_schema(resource)
    registered_meta = get_registration_metadata(resource, schema)

    registration_responses = {}
    registration_response_keys = schema.schema_blocks.filter(
        registration_response_key__isnull=False
    ).values(
        'registration_response_key',
        'block_type'
    )

    for registration_response_key_dict in registration_response_keys:
        key = registration_response_key_dict['registration_response_key']
        registration_responses[key] = get_nested_answer(
            registered_meta,
            registration_response_key_dict['block_type'],
            key.split('.')
        )
    return registration_responses


def expand_registration_responses(resource):
    pass
