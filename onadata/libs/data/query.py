# -*- coding: utf-8 -*-
"""
Query data utility functions.
"""

import logging

from django.conf import settings
from django.db import connection

from onadata.apps.logger.models.data_view import DataView
from onadata.libs.utils.common_tags import SUBMISSION_TIME, SUBMITTED_BY
from onadata.libs.utils.common_tools import get_abbreviated_xpath

logger = logging.getLogger(__name__)


def _dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    desc = cursor.description

    return [dict(zip([col[0] for col in desc], row)) for row in cursor.fetchall()]


def _execute_query(query, to_dict=True):
    cursor = connection.cursor()
    cursor.execute(query)

    return _dictfetchall(cursor) if to_dict else cursor


def _get_fields_of_type(xform, types):
    k = []
    survey_elements = flatten([xform.get_survey_elements_of_type(t) for t in types])

    for element in survey_elements:
        name = get_abbreviated_xpath(element.get_xpath())
        k.append(name)

    return k


def _additional_data_view_filters(data_view):
    # pylint: disable=protected-access
    where, where_params = DataView._get_where_clause(data_view)

    data_view_where = ""
    if where:
        data_view_where = " AND " + " AND ".join(where)

    for param in where_params:
        data_view_where = data_view_where.replace("%s", f"'{param}'", 1)

    return data_view_where


def _json_query(field):
    if not field:
        logger.info("Field is empty")
        return f"json->>'{field}'"

    _field = field.replace("'", "''")

    return f"json->>'{_field}'"


def _postgres_count_group_field_n_group_by(field, name, xform, group_by, data_view):
    string_args = _query_args(field, name, xform, group_by)
    if is_date_field(xform, field):
        string_args["json"] = (
            "to_char(to_date(%(json)s, 'YYYY-MM-DD'), 'YYYY" "-MM-DD')" % string_args
        )

    additional_filters = ""
    if data_view:
        additional_filters = _additional_data_view_filters(data_view)

    restricted_string = _restricted_query(xform)
    query = (
        'SELECT %(json)s AS "%(name)s", '
        '%(group_by)s AS "%(group_name)s", '
        "count(*) as count "
        "FROM %(table)s WHERE "
        + restricted_string
        + " AND deleted_at IS NULL "
        + additional_filters
        + " GROUP BY %(json)s, %(group_by)s"
        + " ORDER BY %(json)s, %(group_by)s"
    )
    query = query % string_args

    return query


def _postgres_count_group(field, name, xform, data_view=None):
    string_args = _query_args(field, name, xform)
    if is_date_field(xform, field):
        string_args["json"] = (
            "to_char(to_date(%(json)s, 'YYYY-MM-DD'), 'YYYY" "-MM-DD')" % string_args
        )

    additional_filters = ""
    if data_view:
        additional_filters = _additional_data_view_filters(data_view)

    # Use left join to the auth user model for better performance.
    if field == SUBMITTED_BY:
        string_args["json"] = "au.username"
        string_args["join"] = "i LEFT JOIN auth_user au ON au.id = i.user_id"

    restricted_string = _restricted_query(xform)
    sql_query = (
        'SELECT %(json)s AS "%(name)s", COUNT(*) AS count FROM '
        "%(table)s %(join)s WHERE "
        + restricted_string
        + " AND deleted_at IS NULL "
        + additional_filters
        + " GROUP BY %(json)s"
        " ORDER BY %(json)s"
    )
    sql_query = sql_query % string_args

    return sql_query


def _postgres_aggregate_group_by(field, name, xform, group_by, data_view=None):
    string_args = _query_args(field, name, xform, group_by)
    if is_date_field(xform, field):
        string_args["json"] = (
            "to_char(to_date(%(json)s, 'YYYY-MM-DD'), 'YYYY" "-MM-DD')" % string_args
        )

    additional_filters = ""
    if data_view:
        additional_filters = _additional_data_view_filters(data_view)

    group_by_select = ""
    group_by_group_by = ""
    if isinstance(group_by, list):
        group_by_group_by = []
        for i, __ in enumerate(group_by):
            group_by_select += (
                "%(group_by" + str(i) + ')s AS "%(group_name' + str(i) + ')s", '
            )
            group_by_group_by.append("%(group_by" + str(i) + ")s")
        group_by_group_by = ",".join(group_by_group_by)
    else:
        group_by_select = '%(group_by)s AS "%(group_name)s",'
        group_by_group_by = "%(group_by)s"

    restricted_string = _restricted_query(xform)
    aggregation_string = "COUNT(%(json)s) AS count "
    if field in get_numeric_fields(xform) or not isinstance(group_by, list):
        aggregation_string += (
            ", SUM((%(json)s)::numeric) AS sum, " "AVG((%(json)s)::numeric) AS mean "
        )
    else:
        group_by_select = "%(json)s AS %(name)s, " + group_by_select
        group_by_group_by = "%(json)s, " + group_by_group_by
    query = (
        "SELECT "
        + group_by_select
        + aggregation_string
        + "FROM %(table)s WHERE "
        + restricted_string
        + " AND deleted_at IS NULL "
        + additional_filters
        + " GROUP BY "
        + group_by_group_by
        + " ORDER BY "
        + group_by_group_by
    )

    return query % string_args


def _postgres_select_key(field, name, xform):
    string_args = _query_args(field, name, xform)
    restricted_string = _restricted_query(xform)
    query = (
        'SELECT %(json)s AS "%(name)s" FROM %(table)s WHERE '
        + restricted_string
        + " AND deleted_at IS NULL "
    )
    return query % string_args


def _restricted_query(xform):
    if xform.is_merged_dataset:
        return "%(restrict_field)s IN %(restrict_value)s"

    return "%(restrict_field)s=%(restrict_value)s"


def _query_args(field, name, xform, group_by=None):
    qargs = {
        "table": "logger_instance",
        "json": _json_query(field),
        "name": name,
        "restrict_field": "xform_id",
        "restrict_value": xform.pk,
        "join": "",
    }

    if xform.is_merged_dataset:
        xforms = tuple(
            __
            for __ in xform.mergedxform.xforms.filter(
                deleted_at__isnull=True
            ).values_list("id", flat=True)
        ) or (xform.pk, xform.pk)
        qargs["restrict_value"] = xforms

    if isinstance(group_by, list):
        for index, value in enumerate(group_by):
            qargs[f"group_name{index}"] = value
            qargs[f"group_by{index}"] = _json_query(value)
    else:
        qargs["group_name"] = group_by
        qargs["group_by"] = _json_query(group_by)

    return qargs


def _select_key(field, name, xform):
    if using_postgres():
        return _postgres_select_key(field, name, xform)

    raise ValueError("Unsupported Database")


def flatten(lst):
    """Flattens a list of lists."""
    return [item for sublist in lst for item in sublist]


def get_date_fields(xform):
    """List of date field names for specified xform"""
    return [SUBMISSION_TIME] + _get_fields_of_type(
        xform, ["date", "datetime", "start", "end", "today"]
    )


def get_field_records(field, xform):
    """Queries and returns all records of the given field."""
    result = _execute_query(_select_key(field, field, xform), to_dict=False)
    return [float(i[0]) for i in result if i[0] is not None]


# pylint: disable=invalid-name
def get_form_submissions_grouped_by_field(xform, field, name=None, data_view=None):
    """Number of submissions grouped by field"""
    if not name:
        name = field

    return _execute_query(_postgres_count_group(field, name, xform, data_view))


# pylint: disable=invalid-name
def get_form_submissions_aggregated_by_select_one(
    xform, field, name=None, group_by=None, data_view=None
):
    """Number of submissions grouped and aggregated by select_one field"""
    if not name:
        name = field
    return _execute_query(
        _postgres_aggregate_group_by(field, name, xform, group_by, data_view)
    )


# pylint: disable=invalid-name
def get_form_submissions_grouped_by_select_one(
    xform, field, group_by, name=None, data_view=None
):
    """Number of submissions disaggregated by select_one field"""
    if not name:
        name = field
    return _execute_query(
        _postgres_count_group_field_n_group_by(field, name, xform, group_by, data_view)
    )


def get_numeric_fields(xform):
    """List of numeric field names for specified xform"""
    return _get_fields_of_type(xform, ["decimal", "integer"])


def is_date_field(xform, field):
    """Returns True if an XForm field is a date field."""
    return field in get_date_fields(xform)


def using_postgres():
    """Returns True if django.db.backends.postgresql is the DB engine in use"""
    return settings.DATABASES["default"]["ENGINE"] in [
        "django.db.backends.postgresql",
        "django.contrib.gis.db.backends.postgis",
    ]
