import os
import re
import itertools
import json
import logging
import warnings
from math import ceil

from contextlib import contextmanager
from django.apps import apps
from django.db import connection
from django.db.migrations.operations.base import Operation

from website import settings
from osf.models import NodeLicense, RegistrationSchema
from osf.models.base import generate_object_id
from website.project.metadata.schemas import OSF_META_SCHEMAS


logger = logging.getLogger(__file__)


increment = 100000

# Dict to map original schema formats to schema block types
FORMAT_TYPE_TO_TYPE_MAP = {
    ('multiselect', 'choose'): 'multi-select-input',
    (None, 'multiselect'): 'multi-select-input',
    (None, 'choose'): 'single-select-input',
    ('osf-upload-open', 'osf-upload'): 'file-input',
    ('osf-upload-toggle', 'osf-upload'): 'file-input',
    ('singleselect', 'choose'): 'single-select-input',
    ('text', 'string'): 'short-text-input',
    ('textarea', 'osf-author-import'): 'contributors-input',
    ('textarea', 'string'): 'long-text-input',
    ('textarea-lg', None): 'long-text-input',
    ('textarea-lg', 'string'): 'long-text-input',
    ('textarea-xl', 'string'): 'long-text-input',
}

# For registration_responses validation, expected format for files
FILE_UPLOAD_SCHEMA = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'file_name': {'type': 'string'},
        'file_id': {'type': 'string'}
    },
    'dependencies': {
        'file_name': ['file_id'],
        'file_id': ['file_name']
    }
}

def get_osf_models():
    """
    Helper function to retrieve all osf related models.

    Example usage:
        with disable_auto_now_fields(models=get_osf_models()):
            ...
    """
    return list(itertools.chain(*[app.get_models() for app in apps.get_app_configs() if app.label.startswith('addons_') or app.label.startswith('osf')]))

@contextmanager
def disable_auto_now_fields(models=None):
    """
    Context manager to disable auto_now field updates.
    If models=None, updates for all auto_now fields on *all* models will be disabled.

    :param list models: Optional list of models for which auto_now field updates should be disabled.
    """
    if not models:
        models = apps.get_models()

    changed = []
    for model in models:
        for field in model._meta.get_fields():
            if hasattr(field, 'auto_now') and field.auto_now:
                field.auto_now = False
                changed.append(field)
    try:
        yield
    finally:
        for field in changed:
            if hasattr(field, 'auto_now') and not field.auto_now:
                field.auto_now = True

@contextmanager
def disable_auto_now_add_fields(models=None):
    """
    Context manager to disable auto_now_add field updates.
    If models=None, updates for all auto_now_add fields on *all* models will be disabled.

    :param list models: Optional list of models for which auto_now_add field updates should be disabled.
    """
    if not models:
        models = apps.get_models()

    changed = []
    for model in models:
        for field in model._meta.get_fields():
            if hasattr(field, 'auto_now_add') and field.auto_now_add:
                field.auto_now_add = False
                changed.append(field)
    try:
        yield
    finally:
        for field in changed:
            if hasattr(field, 'auto_now_add') and not field.auto_now_add:
                field.auto_now_add = True

def ensure_licenses(*args, **kwargs):
    """Upsert the licenses in our database based on a JSON file.

    :return tuple: (number inserted, number updated)

    Moved from website/project/licenses/__init__.py
    """
    ninserted = 0
    nupdated = 0
    try:
        NodeLicense = args[0].get_model('osf', 'nodelicense')
    except Exception:
        # Working outside a migration
        from osf.models import NodeLicense
    with open(
            os.path.join(
                settings.APP_PATH,
                'node_modules', '@centerforopenscience', 'list-of-licenses', 'dist', 'list-of-licenses.json'
            )
    ) as fp:
        licenses = json.loads(fp.read())
        for id, info in licenses.items():
            name = info['name']
            text = info['text']
            properties = info.get('properties', [])
            url = info.get('url', '')

            node_license, created = NodeLicense.objects.get_or_create(license_id=id)

            node_license.name = name
            node_license.text = text
            node_license.properties = properties
            node_license.url = url
            node_license.save()

            if created:
                ninserted += 1
            else:
                nupdated += 1

            logger.info('License {name} ({id}) added to the database.'.format(name=name, id=id))

    logger.info('{} licenses inserted into the database, {} licenses updated in the database.'.format(
        ninserted, nupdated
    ))

    return ninserted, nupdated


def remove_licenses(*args):
    pre_count = NodeLicense.objects.all().count()
    NodeLicense.objects.all().delete()

    logger.info('{} licenses removed from the database.'.format(pre_count))


def ensure_schemas(*args):
    """Import meta-data schemas from JSON to database if not already loaded
    """
    schema_count = 0
    try:
        RegistrationSchema = args[0].get_model('osf', 'registrationschema')
    except Exception:
        try:
            RegistrationSchema = args[0].get_model('osf', 'metaschema')
        except Exception:
            # Working outside a migration
            from osf.models import RegistrationSchema
    for schema in OSF_META_SCHEMAS:
        schema_obj, created = RegistrationSchema.objects.update_or_create(
            name=schema['name'],
            schema_version=schema.get('version', 1),
            defaults={
                'schema': schema,
            }
        )
        schema_count += 1

        if created:
            logger.info('Added schema {} to the database'.format(schema['name']))

        schema_obj.registration_responses_jsonschema = build_flattened_jsonschema(schema_obj)
        schema_obj.save()

    logger.info('Ensured {} schemas are in the database'.format(schema_count))


def remove_schemas(*args):
    pre_count = RegistrationSchema.objects.all().count()
    RegistrationSchema.objects.all().delete()

    logger.info('Removed {} schemas from the database'.format(pre_count))


def create_block(state, schema_id, block_type, display_text='', required=False, help_text='',
        registration_response_key=None, schema_block_group_key='', example_text=''):
    """
    For mapping schemas to schema blocks: creates a given block from the specified parameters
    """
    RegistrationSchemaBlock = state.get_model('osf', 'registrationschemablock')

    return RegistrationSchemaBlock.objects.create(
        schema_id=schema_id,
        block_type=block_type,
        required=required,
        display_text=display_text,
        help_text=help_text,
        registration_response_key=registration_response_key,
        schema_block_group_key=schema_block_group_key,
        example_text=example_text
    )

# Split question multiple choice options into their own blocks
def split_options_into_blocks(state, rs, question, schema_block_group_key):
    """
    For mapping schemas to schema blocks: splits individual multiple choice
    options into their own schema blocks
    """
    for option in question.get('options', []):
        answer_text = option if isinstance(option, basestring) else option.get('text')
        help_text = '' if isinstance(option, basestring) else option.get('tooltip', '')

        create_block(
            state,
            rs.id,
            'select-input-option',
            display_text=answer_text,
            help_text=help_text,
            schema_block_group_key=schema_block_group_key,
        )

def get_registration_response_key(question):
    """
    For mapping schemas to schema blocks:
    Answer ids will map to the user's response
    """
    return question.get('qid', '') or question.get('id', '')

def strip_html(string_with_html):
    """
    For mapping schemas to schema blocks:
    Some original schemas have html in the description/help text.  Just replacing this with empty strings.
    """
    stripped_html = re.sub('<.*?>', '', string_with_html)
    return stripped_html


def find_title_description_help_example(rs, question):
    """
    For mapping schemas to schema blocks:
    Schemas are inconsistent with regards to the information going into "title",
    "description", and "help" blocks.

    :returns tuple, title, description, help, example strings

    """
    title = question.get('title', '')
    description = strip_html(question.get('description', ''))
    help = strip_html(question.get('help', ''))
    example = ''

    schema_name = rs.schema.get('name', '')
    # Descriptions that contain any of these keywords
    # are turned into help text instead.
    help_text_keywords = [
        'please',
        'choose',
        'provide',
        'format',
        'describe',
        'who',
        'what',
        'when',
        'where',
        'use',
        'you',
        'your',
        'skip',
        'enter',
    ]

    if title:
        if schema_name in ['OSF Preregistration', 'Prereg Challenge']:
            # These two schemas have clear "example" text in the "help" section
            example = help
            help = description
            description = ''
        else:
            for keyword in help_text_keywords:
                if keyword in description.lower():
                    help = description
                    description = ''
                    break
    else:
        # if no title, description text is moved to title.
        title = description
        description = ''

    return title, description, help, example

def format_property(question, property, index):
    """
    For mapping schemas to schema blocks:
    Modify a subquestion's qid, title, description, and help text, because
    these are often absent.
    - Modify a subquestion's qid to be of the format "parent-id.current-id", to
      reflect its nested nature, to ensure uniqueness
    - For the first nested subquestion, transfer the parent's title, description, and help.
    """
    property['qid'] = '{}.{}'.format(get_registration_response_key(question) or '', property.get('id', ''))
    if not index:
        title = question.get('title', '')
        description = question.get('description', '')
        help = question.get('help', '')
        if not property.get('title', '') and not property.get('description'):
            property['title'] = title
        if not property.get('description', ''):
            property['description'] = description
        if not property.get('help', ''):
            property['help'] = help
    return property


def format_question(state, rs, question, sub=False):
    """
    For mapping schemas to schema blocks:
    Split the original question from the schema into multiple schema blocks, all of
    which have the same schema_block_group_key, to link them.
    """
    # If there are subquestions, recurse and format subquestions
    if question.get('properties'):
        # Creates section or subsection
        create_block(
            state,
            rs.id,
            block_type='subsection-heading' if sub else 'section-heading',
            display_text=question.get('title', '') or question.get('description', ''),
        )
        for index, property in enumerate(question.get('properties')):
            format_question(state, rs, format_property(question, property, index), sub=True)
    else:
        # All form blocks related to a particular question share the same schema_block_group_key.
        schema_block_group_key = generate_object_id()
        title, description, help, example = find_title_description_help_example(rs, question)

        # Creates question title block
        create_block(
            state,
            rs.id,
            block_type='question-title',
            display_text=title,
            help_text='' if description else help,
            example_text=example,
            schema_block_group_key=schema_block_group_key
        )

        # Creates paragraph block (question description)
        if description:
            create_block(
                state,
                rs.id,
                block_type='paragraph',
                display_text=description,
                help_text=help,
                schema_block_group_key=schema_block_group_key,
            )

        # Creates question input block - this block will correspond to an answer
        # Map the original schema section format to the new block_type, and create a schema block
        block_type = FORMAT_TYPE_TO_TYPE_MAP[(question.get('format'), question.get('type'))]
        create_block(
            state,
            rs.id,
            block_type,
            required=question.get('required', False),
            schema_block_group_key=schema_block_group_key,
            registration_response_key=get_registration_response_key(question)
        )

        # If there are multiple choice answers, create blocks for these as well.
        split_options_into_blocks(state, rs, question, schema_block_group_key)


def map_schemas_to_schemablocks(*args):
    """Map schemas to schema blocks
    """
    state = args[0]
    try:
        RegistrationSchema = state.get_model('osf', 'registrationschema')
    except Exception:
        try:
            RegistrationSchema = state.get_model('osf', 'metaschema')
        except Exception:
            # Working outside a migration
            from osf.models import RegistrationSchema

    # TODO: remove. Until RegistrationSchemaBlocks are set, running this method
    # will delete all existing RegistrationSchemaBlocks and rebuild
    unmap_schemablocks(*args)

    for rs in RegistrationSchema.objects.all():
        logger.info('Migrating schema {}, version {} to schema blocks.'.format(rs.schema.get('name'), rs.schema_version))
        for page in rs.schema['pages']:
            # Create page heading block
            create_block(
                state,
                rs.id,
                'page-heading',
                display_text=strip_html(page.get('title', '')),
                help_text=strip_html(page.get('description', ''))
            )
            for question in page['questions']:
                format_question(state, rs, question)


def unmap_schemablocks(*args):
    state = args[0]
    RegistrationSchemaBlock = state.get_model('osf', 'registrationschemablock')
    RegistrationSchemaBlock.objects.all().delete()


# For registration_responses validation
def get_multiple_choice_options(registration_schema, question):
    """
    Returns a dictionary with an 'enum' key, and a value as
    an array with the possible multiple choice answers for a given question.
    Schema blocks are linked by chunk_ids, so fetches multiple choice options
    with the same chunk_id as the given question
    :question SchemaBlock with an registration_response_key
    """
    options = registration_schema.schema_blocks.filter(
        schema_block_group_key=question.schema_block_group_key,
        block_type='select-input-option'
    ).values_list('display_text', flat=True)

    return {
        'enum': list(options)
    }

# For registration_responses validation
def get_jsonschema_type(block_type):
    """
    For a given schema block type, returns the corresponding
    jsonschema type
    :params block_type: string, SchemaBlock block_type
    :return string
    """
    if block_type == 'file-input':
        return 'array'
    elif block_type == 'multi-select-input':
        return 'array'
    else:
        return 'string'

# For registration_responses validation
def format_question_validation(registration_schema, question):
    """
    Returns json for validating an individual question
    :params question SchemaBlock
    """
    if question.block_type == 'single-select-input':
        property = get_multiple_choice_options(registration_schema, question)
    elif question.block_type == 'multi-select-input':
        property = {
            'items': get_multiple_choice_options(registration_schema, question)
        }
    elif question.block_type == 'file-input':
        property = {
            'items': FILE_UPLOAD_SCHEMA
        }
    else:
        property = {}

    property['type'] = get_jsonschema_type(question.block_type)
    # Stashing the question title on the jsonschema's description field
    property['description'] = registration_schema.schema_blocks.get(
        schema_block_group_key=question.schema_block_group_key,
        block_type='question-title'
    ).display_text
    return property

# For registration_responses validation
def build_flattened_jsonschema(registration_schema):
    """
    Builds jsonschema for validating flattened registration_responses field
    :params schema RegistrationSchema
    :returns dictionary, jsonschema, for validation
    """
    properties = {}
    # schema blocks corresponding to registration_responses
    questions = registration_schema.schema_blocks.filter(registration_response_key__isnull=False)
    for question in questions:
        properties[question.registration_response_key] = format_question_validation(registration_schema, question)

    json_schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': properties
    }

    required = questions.filter(required=True).values_list('registration_response_key', flat=True)
    if required:
        json_schema['required'] = list(required)

    return json_schema


class UpdateRegistrationSchemas(Operation):
    """Custom migration operation to update registration schemas
    """
    reversible = True

    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        ensure_schemas(to_state.apps)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        warnings.warn('Reversing UpdateRegistrationSchemas is a noop')

    def describe(self):
        return 'Updated registration schemas'


class AddWaffleFlags(Operation):
    """Custom migration operation to add waffle flags

    Params:
    - flag_names: iterable of strings, flag names to create
    - on_for_everyone: boolean (default False), whether to activate the newly created flags
    """
    reversible = True

    def __init__(self, flag_names, on_for_everyone=False):
        self.flag_names = flag_names
        self.on_for_everyone = on_for_everyone

    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        Flag = to_state.apps.get_model('waffle', 'flag')
        for flag_name in self.flag_names:
            Flag.objects.get_or_create(name=flag_name, defaults={'everyone': self.on_for_everyone})

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        Flag = to_state.apps.get_model('waffle', 'flag')
        Flag.objects.filter(name__in=self.flag_names).delete()

    def describe(self):
        return 'Adds waffle flags: {}'.format(', '.join(self.flag_names))


class DeleteWaffleFlags(Operation):
    """Custom migration operation to delete waffle flags

    Params:
    - flag_names: iterable of strings, flag names to delete
    """
    reversible = True

    def __init__(self, flag_names):
        self.flag_names = flag_names

    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        Flag = to_state.apps.get_model('waffle', 'flag')
        Flag.objects.filter(name__in=self.flag_names).delete()

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        Flag = to_state.apps.get_model('waffle', 'flag')
        for flag_name in self.flag_names:
            Flag.objects.get_or_create(name=flag_name)

    def describe(self):
        return 'Removes waffle flags: {}'.format(', '.join(self.flag_names))


class AddWaffleSwitches(Operation):
    """Custom migration operation to add waffle switches

    Params:
    - switch_names: iterable of strings, the names of the switches to create
    - active: boolean (default False), whether the switches should be active
    """
    reversible = True

    def __init__(self, switch_names, active=False):
        self.switch_names = switch_names
        self.active = active

    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        Switch = to_state.apps.get_model('waffle', 'switch')
        for switch in self.switch_names:
            Switch.objects.get_or_create(name=switch, defaults={'active': self.active})

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        Switch = to_state.apps.get_model('waffle', 'switch')
        Switch.objects.filter(name__in=self.switch_names).delete()

    def describe(self):
        return 'Adds waffle switches: {}'.format(', '.join(self.switch_names))


class DeleteWaffleSwitches(Operation):
    """Custom migration operation to delete waffle switches

    Params:
    - switch_names: iterable of strings, switch names to delete
    """
    reversible = True

    def __init__(self, switch_names):
        self.switch_names = switch_names

    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        Switch = to_state.apps.get_model('waffle', 'switch')
        Switch.objects.filter(name__in=self.switch_names).delete()

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        Switch = to_state.apps.get_model('waffle', 'switch')
        for switch in self.switch_names:
            Switch.objects.get_or_create(name=switch)

    def describe(self):
        return 'Removes waffle switches: {}'.format(', '.join(self.switch_names))

def batch_node_migrations(state, migrations):
    AbstractNode = state.get_model('osf', 'abstractnode')
    max_nid = getattr(AbstractNode.objects.last(), 'id', 0)

    for migration in migrations:
        total_pages = int(ceil(max_nid / float(increment)))
        page_start = 0
        page_end = 0
        page = 0
        logger.info('{}'.format(migration['description']))
        while page_end <= (max_nid):
            page += 1
            page_end += increment
            if page <= total_pages:
                logger.info('Updating page {} / {}'.format(page_end / increment, total_pages))
            with connection.cursor() as cursor:
                cursor.execute(migration['sql'].format(
                    start=page_start,
                    end=page_end
                ))
            page_start = page_end
