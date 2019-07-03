from ckan import plugins
from ckan.common import config
from validate import validate
from collections import OrderedDict
import logging
import auth
import os
import inspect
import json
from validation_blueprint import manual_validation

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
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IAuthFunctions)

    def get_helpers(self):
        return {
            "validator_show_validation_schemas": show_validation_schemas,
        }

    def get_blueprint(self):
        log.info("registering blueprint")
        return manual_validation

    def get_auth_functions(self):
        return {
            "manual_validation": auth.validator_manual_validation
        }

    # IConfigurer
    def update_config(self, config):
        '''
        This method allows to access and modify the CKAN configuration object
        '''
        log.info("ValidatorPlugin is enabled")
        plugins.toolkit.add_template_directory(config, 'templates')

    def configure(self, config):
        # Load the config text and throw error if config doesn't exist
        schema_config = config.get('ckanext.validator.schema_config')
        if not schema_config:
            raise RuntimeError(
                'Required config key ckanext.validator.schema_config not found'
            )

        # Turn schema config text to json
        self.schema_config = json.loads(schema_config)

        # Load all schemas in the specified schema directory
        if self.schema_config.get(u"schema_directory"):
            schemas = _files_from_directory(
                self.schema_config.pop("schema_directory", "")
            )
            for name, path in schemas.iteritems():
                self.schema_config[name] = path

        # Reset the config value to the fully loaded python dict
        config['ckanext.validator.schema_config'] = self.schema_config

        # Load each schema into the Plugin's schema_config property
        for key, path in self.schema_config.iteritems():
            schema = _load_schema_from_path(path)
            self.schema_config[key] = schema

    def before_create(self, context, resource):
        """
        Validates the data before the resource is created
        """
        validation_outcome = validate(context, resource, self.schema_config)
        if not validation_outcome:
            return
        report, schema = validation_outcome
        error_count = report["tables"][0]["error-count"]
        if error_count > 0:
            error_summary = create_error_summary(report, schema)
            raise plugins.toolkit.ValidationError(error_summary)

    def after_create(self, context, resource):
        mv = resource.get("manual_validation")
        if mv == "unvalidated":
            log.info("Sending Emails")


def create_error_summary(report, schema):
    """
    This function takes a good tables error report and turns them into a grouped list of error
    messages to be displayed in the frontend.  If someone has failed to comply with the data
    template in one row, it is likely they havn't complied with the template in many rows. It is
    very easy to end up with the same error message duplicated hundreds of times.  In these
    situations we want to group the errors of the same type together.  We do this by grouping on
    column and error code (so same type of errors in the same columns are grouped).
    """
    error_summary = {}
    grouped_errors = OrderedDict()

    # Group the errors by type/column
    for i, error in enumerate(report["tables"][0]["errors"]):
        # Get the error message & transpose rows/columns if necessary
        message = error["message"]
        if schema.get("transpose"):
            message = message.replace("column", "xxxx").replace(
                "row",
                "column"
            ).replace("xxxx", "row")

        # Create a combined group key from column and code & add error to group
        error_group = "{}-{}".format(
            error["code"],
            error.get("column-number", "")
        )
        grouped_errors.setdefault(error_group, []).append(message)

    # Count number of groups with more than 2 messages
    number_large_groups = len(filter(
        lambda k: len(grouped_errors[k]) > 2,
        grouped_errors.keys()
    ))

    errors_to_show = 10
    counter = 1
    errors_to_expand = max(0, errors_to_show - len(grouped_errors.keys()))
    errors_to_expand = int(errors_to_expand / number_large_groups)

    # Unpack the errors according to some sensible logic
    for group, messages in grouped_errors.items():

        def create_error(message):
            key = "Data Validation Error " + str(counter)
            error_summary[key] = [message]

        number = len(messages)
        if number > 3:
            for i in range(0, errors_to_expand):
                if i < number:
                    create_error(messages[i])
                    counter += 1
            messages = messages[errors_to_expand:]

        if len(messages) > 2:
            message = (
                "{} (There are {} other errors like this)"
            ).format(
                messages[0], (len(messages)-1)
            )
            create_error(message)
            counter += 1
        else:
            for message in messages:
                create_error(message)
                counter += 1

        if counter >= errors_to_show:
            break

    return error_summary


def _files_from_directory(path, extension='.json'):
    listed_files = {}
    for root, dirs, files in os.walk(path):
        for file in files:
            if extension in file:
                name = file.split(".json")[0]
                listed_files[name] = os.path.join(root, file)
    return listed_files


def _load_schema_from_path(path):
    """
    Given an absolute file path (beginning with /) load a json schema object
    in that file.
    """
    if os.path.exists(path):
        try:
            return json.load(open(path))
        except Exception:
            log.error("Error reading schema " + path)
            raise
    else:
        raise IOError(path + " file not found")


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
        try:
            return json.load(open(p))
        except Exception:
            log.error("Error with shcmea " + url)
            raise
    else:
        raise IOError(url + "file not found")
