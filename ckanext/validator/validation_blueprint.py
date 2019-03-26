# encoding: utf-8
import logging

from flask import Blueprint
import ckan.logic as logic
from ckan.plugins import toolkit
import ckan.lib.helpers as h
log = logging.getLogger(__name__)

manual_validation = Blueprint(u'validation_blueprint', __name__,
                              url_prefix=u'/manual_validation')


def validate_view(resource_id):
    """ Set's validated=True for the given resource id"""


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
    pkg_dict = toolkit.get_action('package_show')(dict(context, return_type='dict'),
                                           {'id': res["package_id"]})
    
    return toolkit.render("validator/manual_validation.html",
                          {
                              "resource": res,
                              "pkg": pkg_dict
                          })


def validate():
    context = {}
    try:
        toolkit.check_access('manual_validation', context)
    except toolkit.NotAuthorized:
        toolkit.abort(403, toolkit._('User %r not authorized to edit %s') %
                      (context.user, resource_id))
    resource_id = toolkit.request.form.get("resource_id")
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

manual_validation.add_url_rule(u'/<resource_id>', view_func=validate_view)
manual_validation.add_url_rule(u'/validate', view_func=validate, methods=["POST"])
