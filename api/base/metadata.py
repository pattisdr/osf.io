from rest_framework.metadata import SimpleMetadata

from website.project.model import MetaSchema

class SchemaMetadata(SimpleMetadata):
    """
    Adds registration_schema_choices to OPTIONS
    """
    def determine_metadata(self, request, view):
        metadata = super(SchemaMetadata, self).determine_metadata(request, view)
        schema_choices = {schema.name: schema.schema for schema in MetaSchema.find()}

        metadata['registration_schema_choices'] = schema_choices

        return metadata
