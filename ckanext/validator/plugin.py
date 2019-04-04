from ckan import plugins
import logging
from ckan.common import config
from ckan.logic import ActionError, side_effect_free
from validate import validate
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
        validation_outcome = validate(context, resource, self.schema_config)
        if not validation_outcome:
            return
        report, schema = validation_outcome
        error_count = report["tables"][0]["error-count"]
    
        if error_count > 0:
            error_summary = {}
            for i, error in enumerate(report["tables"][0]["errors"]):
                message = error["message"]
                if schema.get("transpose"):
                    message = message.replace("column", "xxxx").replace("row", "column").replace("xxxx", "row")
                error_summary["Data Validation Error " + str(i + 1)] = [message]
            raise plugins.toolkit.ValidationError(error_summary)

        
     
    def after_create(self, context, resource):
        mv = resource.get("manual_validation")
        if mv == "unvalidated":
            log.info("Sending Emails")
        
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
        except:
            log.error("Error with shcmea " + url)
            raise
    else:
        raise FileNotFoundError(url +" not found")
