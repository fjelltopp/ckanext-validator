import cStringIO
import goodtables
from werkzeug.datastructures import FileStorage
import cgi
from ckan.lib import munge
import pandas
import logging
from ckan import plugins

log = logging.getLogger(__name__)

def validate(context, resource, schema_config):

    schema_name = resource.get("validator_schema")
    if not schema_name:
        return
    if schema_name not in schema_config:
        raise FileNotFoundError("Could not find schema")
    schema = schema_config.get(schema_name)
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
        file_upload = file_string.decode("utf-8").encode("ascii", "ignore")
    checks = ["schema"]
    if schema.get("transpose"):
        file_upload = transpose(file_upload, extension)
                                    
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
            message = error["message"]
            if schema.get("transpose"):
                message = message.replace("column", "xxxx").replace("row", "column").replace("xxxx", "row")
                error_summary["Data Validation Error " + str(i + 1)] = [message]
        raise plugins.toolkit.ValidationError(error_summary)


def transpose(data, extension):
    
    if extension == "csv":
        f = cStringIO.StringIO(data)
        out = cStringIO.StringIO()
        df = pandas.read_csv(f)
    elif extension in ["xls", "xlsx"]:
        out = cStringIO.StringIO()
        df = pandas.read_excel(data)
    col_name = df.columns[0]
    df.set_index(col_name, inplace=True)
    trans = df.T
    trans.index.name = col_name

    if extension == "csv":
        trans.to_csv(out)
        out.seek(0)
        return out.read()
    elif extension in ["xls", "xlsx"]:
        trans.to_excel(out)
        out.seek(0)
        return out
