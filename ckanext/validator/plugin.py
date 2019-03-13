from ckan import plugins
import logging
from ckan.common import config
from ckan.logic import ActionError, side_effect_free

import cStringIO
import goodtables
import os
from werkzeug.datastructures import FileStorage
import cgi
import inspect
from ckan.lib import munge
import json


log = logging.getLogger(__name__)


def show_validation_schemas():
    """ Returns a list of validation schemas"""
    schema_config = config.get('ckanext.validator.schema_config')
    return schema_config.keys()


class ValidatorPlugin(plugins.SingletonPlugin):
    """
    This plugin implements data validation using the goodtables library

    """
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IResourceController, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)

    def get_helpers(self):
        return {
            "validator_show_validation_schemas": show_validation_schemas,
        }

    # IConfigurer
    def update_config(self, config):
        '''
        This method allows to access and modify the CKAN configuration object
        '''
        log.info("ValidatorPlugin is enabled")
        plugins.toolkit.add_template_directory(config, 'templates')

    def configure(self, config):
        schema_config = config.get('ckanext.validator.schema_config')
        if not schema_config:
             raise RuntimeError(
                'Required config key ckanext.validator.schema_config not found'
            )

        self.schema_config = json.loads(schema_config)

        config['ckanext.validator.schema_config'] = self.schema_config
        for key, url in self.schema_config.iteritems():
            schema = _load_schema(url)
            self.schema_config[key] = schema

    def before_create(self, context, resource):
        """
        Validates the data before the resource is created
        """

        schema_name = resource.get("validator_schema")
        if not schema_name:
            return
        if schema_name not in self.schema_config:
            raise FileNotFoundError("Could not find schema")
        log.warning(resource)
        schema = self.schema_config.get(schema_name)
        upload_field_storage = resource.get("upload")
        log.debug(upload_field_storage)

        if isinstance(upload_field_storage, FileStorage):
            file_string = upload_field_storage._file.read()
        elif isinstance(upload_field_storage, cgi.FieldStorage):
            file_string = upload_field_storage.file.read()
        else:
            raise plugins.toolkit.ValidationError({
                "No file uploaded":
                ["Please choose a file to upload (not a link), you might need to reselect the file"]})
        filename = munge.munge_filename(upload_field_storage.filename)
        extension = filename.split(".")[-1]
        scheme = "stream"
        file_upload = cStringIO.StringIO(file_string)
        if extension == "csv":
            scheme = "text"
            file_upload = file_string
        log.warning(schema)
        log.warning({"custom-constraint": schema.get("custom-constraint",{})})

        checks = ["schema"]

        if "custom-constraint" in schema:
            checks.append({"custom-constraint": schema.get("custom-constraint",{})})

        report = goodtables.validate(file_upload,
                                     format=extension,
                                     scheme=scheme,
                                     schema=schema,
                                     checks=checks)
        log.debug(report)
        error_count = report["tables"][0]["error-count"]

        if error_count > 0:
            error_summary = {}
            for i, error in enumerate(report["tables"][0]["errors"]):
                error_summary["Data Validation Error " + str(i + 1)] = [error["message"]]
            raise plugins.toolkit.ValidationError(error_summary)


def _load_schema(url):
    """
    Given a path like "ckanext.spatialx:spatialx_schema.json"
    find the second part relative to the import path of the first

    Copied from ckanext-schema
    """

    module, file_name = url.split(':', 1)
    try:
        # __import__ has an odd signature
        m = __import__(module, fromlist=[''])
    except ImportError:
        return
    p = os.path.join(os.path.dirname(inspect.getfile(m)), file_name)
    if os.path.exists(p):
        return json.load(open(p))
    else:
        raise FileNotFoundError(url +" not found")
