import ckan.plugins.toolkit as toolkit
from ckanext.restricted import logic

from logging import getLogger
log = getLogger(__name__)


def validator_manual_validation(context, resource):

    return {"success": True}
