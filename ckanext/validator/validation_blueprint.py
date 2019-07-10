# encoding: utf-8
import logging
from flask import Blueprint, Response, abort
import ckan.logic as logic
from ckan.plugins import toolkit
import ckan.lib.helpers as h
from ckan.plugins.toolkit import config

log = logging.getLogger(__name__)

validation_blueprint = Blueprint(
    u'validation_blueprint',
    __name__,
    url_prefix=u'/validation'
)


def validate_view(resource_id):
    """ Manual validation. Set's validated=True for the given resource id"""
    context = {}
    try:
        toolkit.check_access('manual_validation', context)
    except toolkit.NotAuthorized:
        toolkit.abort(403, toolkit._('User %r not authorized to edit %s') %
                      (context.user, resource_id))
    data_dict = {
        "id": resource_id
    }
    res = toolkit.get_action("resource_show")(context, data_dict)
    pkg_dict = toolkit.get_action('package_show')(
        dict(context, return_type='dict'),
        {'id': res["package_id"]}
    )
    return toolkit.render(
        "validator/manual_validation.html",
        {"resource": res, "pkg": pkg_dict}
    )


def validate():
    """
    For Manual Validation
    """
    context = {}
    resource_id = toolkit.request.form.get("resource_id")
    try:
        toolkit.check_access('manual_validation', context)
    except toolkit.NotAuthorized:
        toolkit.abort(403, toolkit._('User %r not authorized to edit %s') %
                      (context.user, resource_id))
    if not resource_id:
        toolkit.abort(404, toolkit._('Resource not found'))
    data_dict = {
            "id": resource_id,
            "manual_validation": "validated"
        }
    try:
        toolkit.get_action("resource_update")(context, data_dict)
    except logic.NotFound:
        toolkit.abort(404, toolkit._('Resource not found'))

    h.flash(toolkit._("Resource sucesfully validated"))
    return toolkit.redirect_to("/")


def download_table_template(validation_schema):
    """
    Downloads a CSV template file for the specified validation schema.
    """
    try:

        validator_config = config.get('ckanext.validator.schema_config')
        schemed_table = validator_config.get(validation_schema)
        template = schemed_table.create_template()
        csv_content = template.to_csv(header=False, index=False, encoding='utf-8')

        return Response(
            csv_content,
            mimetype="text/csv",
            headers={"Content-disposition":
                     "attachment; filename=" + str(validation_schema) + ".csv"}
        )

    except AttributeError as e:
        logging.error(e)
        abort(404, "404 Not Found Error: No schema exists for " + validation_schema)
    except Exception as e:
        logging.error(e)
        abort(
            500,
            "500 Internal server error: Something went wrong whilst "
            "generating your template " + validation_schema
        )


validation_blueprint.add_url_rule(
    u'/template/<validation_schema>',
    view_func=download_table_template
)
validation_blueprint.add_url_rule(
    u'/validate',
    view_func=validate,
    methods=["POST"]
)
validation_blueprint.add_url_rule(
    u'/<resource_id>',
    view_func=validate_view
)
