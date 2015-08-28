from rest_framework.metadata import SimpleMetadata

from website.project.metadata.schemas import OSF_META_SCHEMAS


class SchemaMetadata(SimpleMetadata):
    """
    Adds registration_schema_choices to OPTIONS response.
    """

    # Overrides SimpleMetadata
    def determine_metadata(self, request, view):
        metadata = super(SchemaMetadata, self).determine_metadata(request, view)
        schema_choices = {schema['name'] + ' v' + str(schema['version']): schema for schema in OSF_META_SCHEMAS}
        metadata['registration_schema_choices'] = schema_choices

        return metadata
