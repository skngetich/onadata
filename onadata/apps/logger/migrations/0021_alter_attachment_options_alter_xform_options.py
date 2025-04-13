# Generated by Django 4.2.13 on 2024-07-16 10:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        (
            "logger",
            "0020_rename_logger_inst_deleted_at_da31a3_idx_logger_inst_deleted_da31a3_idx_and_more",
        ),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="attachment",
            options={},
        ),
        migrations.AlterModelOptions(
            name="xform",
            options={
                "permissions": (
                    ("view_xform_all", "Can view all associated data"),
                    ("view_xform_data", "Can view submitted data"),
                    ("report_xform", "Can make submissions to the form"),
                    ("move_xform", "Can move form between projects"),
                    ("transfer_xform", "Can transfer form ownership."),
                    ("can_export_xform_data", "Can export form data"),
                    ("delete_submission", "Can delete submissions from form"),
                ),
                "verbose_name": "XForm",
                "verbose_name_plural": "XForms",
            },
        ),
    ]
