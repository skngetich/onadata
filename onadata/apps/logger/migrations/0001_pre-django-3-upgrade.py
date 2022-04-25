# Generated by Django 3.2.13 on 2022-04-25 06:54

import datetime
from django.conf import settings
import django.contrib.gis.db.models.fields
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
from django.utils.timezone import utc
import onadata.apps.logger.models.attachment
import onadata.apps.logger.models.xform
import onadata.libs.utils.common_tools
from onadata.apps.logger.models import Instance
from onadata.libs.utils.model_tools import queryset_iterator
from onadata.libs.utils.logger_tools import create_xform_version
import taggit.managers
from hashlib import md5


def recalculate_xform_hash(apps, schema_editor):  # pylint: disable=W0613
    """
    Recalculate all XForm hashes.
    """
    XForm = apps.get_model('logger', 'XForm')  # pylint: disable=C0103
    xforms = XForm.objects.filter(downloadable=True,
                                  deleted_at__isnull=True).only('xml')
    count = xforms.count()
    counter = 0

    for xform in queryset_iterator(xforms, 500):
        hash_value = md5(xform.xml.encode('utf8')).hexdigest()
        xform.hash = f"md5:{hash_value}"
        xform.save(update_fields=['hash'])
        counter += 1
        if counter % 500 == 0:
            print(f"Processed {counter} of {count} forms.")

    print(f"Processed {counter} forms.")


def generate_uuid_if_missing(apps, schema_editor):
    """
    Generate uuids for XForms without them
    """
    XForm = apps.get_model('logger', 'XForm')

    for xform in XForm.objects.filter(uuid=''):
        xform.uuid = onadata.libs.utils.common_tools.get_uuid()
        xform.save()


def regenerate_instance_json(apps, schema_editor):
    """
    Regenerate Instance JSON
    """
    for inst in Instance.objects.filter(
            deleted_at__isnull=True,
            xform__downloadable=True,
            xform__deleted_at__isnull=True):
        inst.json = inst.get_full_dict(load_existing=False)
        inst.save()


def create_initial_xform_version(apps, schema_editor):
    """
    Creates an XFormVersion object for an XForm that has no
    Version
    """
    queryset = onadata.apps.logger.models.xform.XForm.objects.filter(
        downloadable=True,
        deleted_at__isnull=True
    )
    for xform in queryset.iterator():
        if xform.version:
            create_xform_version(xform, xform.user)


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth', '0001_initial'),
        ('taggit', '0001_initial'),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('metadata', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                ('shared', models.BooleanField(default=False)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='project_owner', to=settings.AUTH_USER_MODEL)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='project_org', to=settings.AUTH_USER_MODEL)),
                ('tags', taggit.managers.TaggableManager(help_text='A comma-separated list of tags.', through='taggit.TaggedItem', to='taggit.Tag', verbose_name='Tags')),
                ('user_stars', models.ManyToManyField(related_name='project_stars', to=settings.AUTH_USER_MODEL)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'permissions': (('view_project', 'Can view project'), ('add_project_xform', 'Can add xform to project'), ('report_project_xform', 'Can make submissions to the project'), ('transfer_project', 'Can transfer project to different owner'), ('can_export_project_data', 'Can export data in project'), ('view_project_all', 'Can view all associated data'), ('view_project_data', 'Can view submitted data')),
                'unique_together': {('name', 'organization')},
            },
        ),
        migrations.CreateModel(
            name='SurveyType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='XForm',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('xls', models.FileField(null=True, upload_to=onadata.apps.logger.models.xform.upload_to)),
                ('json', models.TextField(default='')),
                ('description', models.TextField(blank=True, default='', null=True)),
                ('xml', models.TextField()),
                ('require_auth', models.BooleanField(default=False)),
                ('shared', models.BooleanField(default=False)),
                ('shared_data', models.BooleanField(default=False)),
                ('downloadable', models.BooleanField(default=True)),
                ('allows_sms', models.BooleanField(default=False)),
                ('encrypted', models.BooleanField(default=False)),
                ('sms_id_string', models.SlugField(default=b'', editable=False, max_length=100, verbose_name='SMS ID')),
                ('id_string', models.SlugField(editable=False, max_length=100, verbose_name='ID')),
                ('title', models.CharField(editable=False, max_length=255)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('last_submission_time', models.DateTimeField(blank=True, null=True)),
                ('has_start_time', models.BooleanField(default=False)),
                ('uuid', models.CharField(default='', max_length=32)),
                ('bamboo_dataset', models.CharField(default='', max_length=60)),
                ('instances_with_geopoints', models.BooleanField(default=False)),
                ('instances_with_osm', models.BooleanField(default=False)),
                ('num_of_submissions', models.IntegerField(default=0)),
                ('version', models.CharField(blank=True, max_length=255, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='logger.project')),
                ('tags', taggit.managers.TaggableManager(help_text='A comma-separated list of tags.', through='taggit.TaggedItem', to='taggit.Tag', verbose_name='Tags')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='xforms', to=settings.AUTH_USER_MODEL)),
                ('has_hxl_support', models.BooleanField(default=False)),
                ('last_updated_at', models.DateTimeField(auto_now=True, default=datetime.datetime(2016, 8, 18, 12, 43, 30, 316792, tzinfo=utc))),
                ('is_merged_dataset', models.BooleanField(default=False)),
                ('hash', models.CharField(blank=True, default=None, max_length=36, null=True, verbose_name='Hash')),
            ],
            options={
                'ordering': ('pk',),
                'verbose_name': 'XForm',
                'verbose_name_plural': 'XForms',
                'permissions': (('view_xform', 'Can view associated data'), ('view_xform_all', 'Can view all associated data'), ('view_xform_data', 'Can view submitted data'), ('report_xform', 'Can make submissions to the form'), ('move_xform', 'Can move form between projects'), ('transfer_xform', 'Can transfer form ownership.'), ('can_export_xform_data', 'Can export form data'), ('delete_submission', 'Can delete submissions from form')),
                'unique_together': {('user', 'id_string', 'project'), ('user', 'sms_id_string', 'project')},
            },
        ),
        migrations.CreateModel(
            name='Instance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('json', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                ('xml', models.TextField()),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(default=None, null=True)),
                ('status', models.CharField(default='submitted_via_web', max_length=20)),
                ('uuid', models.CharField(db_index=True, default='', max_length=249)),
                ('version', models.CharField(max_length=255, null=True)),
                ('geom', django.contrib.gis.db.models.fields.GeometryCollectionField(null=True, srid=4326)),
                ('survey_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='logger.surveytype')),
                ('tags', taggit.managers.TaggableManager(help_text='A comma-separated list of tags.', through='taggit.TaggedItem', to='taggit.Tag', verbose_name='Tags')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='instances', to=settings.AUTH_USER_MODEL)),
                ('xform', models.ForeignKey(default=328, on_delete=django.db.models.deletion.CASCADE, related_name='instances', to='logger.xform')),
                ('last_edited', models.DateTimeField(default=None, null=True)),
                ('media_all_received', models.NullBooleanField(default=True, verbose_name='Received All Media Attachemts')),
                ('media_count', models.PositiveIntegerField(default=0, null=True, verbose_name='Received Media Attachments')),
                ('total_media', models.PositiveIntegerField(default=0, null=True, verbose_name='Total Media Attachments')),
                ('checksum', models.CharField(blank=True, db_index=True, max_length=64, null=True)),
            ],
            options={
                'unique_together': {('xform', 'uuid')},
            },
        ),
        migrations.CreateModel(
            name='ProjectUserObjectPermission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content_object', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='logger.project')),
                ('permission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.permission')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
                'unique_together': {('user', 'permission', 'content_object')},
            },
        ),
        migrations.CreateModel(
            name='ProjectGroupObjectPermission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content_object', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='logger.project')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.group')),
                ('permission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.permission')),
            ],
            options={
                'abstract': False,
                'unique_together': {('group', 'permission', 'content_object')},
            },
        ),
        migrations.CreateModel(
            name='XFormUserObjectPermission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content_object', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='logger.xform')),
                ('permission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.permission')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
                'unique_together': {('user', 'permission', 'content_object')},
            },
        ),
        migrations.CreateModel(
            name='XFormGroupObjectPermission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content_object', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='logger.xform')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.group')),
                ('permission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.permission')),
            ],
            options={
                'abstract': False,
                'unique_together': {('group', 'permission', 'content_object')},
            },
        ),
        migrations.CreateModel(
            name='Note',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('note', models.TextField()),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('instance', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notes', to='logger.instance')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('instance_field', models.TextField(blank=True, null=True)),
            ],
            options={
                'permissions': (('view_note', 'View note'),),
            },
        ),
        migrations.CreateModel(
            name='DataView',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('columns', django.contrib.postgres.fields.jsonb.JSONField()),
                ('query', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='logger.project')),
                ('xform', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='logger.xform')),
                ('instances_with_geopoints', models.BooleanField(default=False)),
                ('matches_parent', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name': 'Data View',
                'verbose_name_plural': 'Data Views',
            },
        ),
        migrations.CreateModel(
            name='OsmData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('xml', models.TextField()),
                ('osm_id', models.CharField(max_length=20)),
                ('tags', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                ('geom', django.contrib.gis.db.models.fields.GeometryCollectionField(srid=4326)),
                ('filename', models.CharField(max_length=255)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(default=None, null=True)),
                ('instance', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='osm_data', to='logger.instance')),
                ('field_name', models.CharField(blank=True, default=b'', max_length=255)),
                ('osm_type', models.CharField(default=b'way', max_length=10)),
            ],
            options={
                'unique_together': {('instance', 'field_name')},
            },
        ),
        migrations.CreateModel(
            name='Widget',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField()),
                ('widget_type', models.CharField(choices=[(b'charts', b'Charts')], default=b'charts', max_length=25)),
                ('view_type', models.CharField(max_length=50)),
                ('column', models.CharField(max_length=255)),
                ('group_by', models.CharField(blank=True, default=None, max_length=255, null=True)),
                ('title', models.CharField(blank=True, default=None, max_length=255, null=True)),
                ('description', models.CharField(blank=True, default=None, max_length=255, null=True)),
                ('key', models.CharField(db_index=True, max_length=32, unique=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
                ('order', models.PositiveIntegerField(db_index=True, default=0, editable=False)),
                ('aggregation', models.CharField(blank=True, default=None, max_length=255, null=True)),
                ('metadata', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict)),
            ],
            options={
                'ordering': ('order',),
            },
        ),
        migrations.CreateModel(
            name='OpenData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('uuid', models.CharField(default=onadata.libs.utils.common_tools.get_uuid, max_length=32, unique=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('active', models.BooleanField(default=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
            ],
        ),
        migrations.CreateModel(
            name='Attachment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('media_file', models.FileField(max_length=255, upload_to=onadata.apps.logger.models.attachment.upload_to)),
                ('mimetype', models.CharField(blank=True, default=b'', max_length=100)),
                ('extension', models.CharField(db_index=True, default='non', max_length=10)),
                ('instance', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='logger.instance')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True)),
                ('date_modified', models.DateTimeField(auto_now=True, null=True)),
                ('deleted_at', models.DateTimeField(default=None, null=True)),
                ('file_size', models.PositiveIntegerField(default=0)),
            ],
            options={
                'ordering': ('pk',),
            },
        ),
        migrations.CreateModel(
            name='MergedXForm',
            fields=[
                ('xform_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='logger.xform')),
                ('xforms', models.ManyToManyField(related_name='mergedxform_ptr', to='logger.XForm')),
            ],
            options={
                'permissions': (('view_mergedxform', 'Can view associated data'),),
            },
            bases=('logger.xform',),
        ),
        migrations.CreateModel(
            name='InstanceHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('xml', models.TextField()),
                ('uuid', models.CharField(default='', max_length=249)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('xform_instance', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submission_history', to='logger.instance')),
                ('geom', django.contrib.gis.db.models.fields.GeometryCollectionField(null=True, srid=4326)),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('submission_date', models.DateTimeField(default=None, null=True)),
                ('checksum', models.CharField(blank=True, max_length=64, null=True)),
            ],
        ),
        migrations.RunSQL(
            sql="UPDATE logger_xform SET hash = CONCAT('md5:', MD5(XML)) WHERE hash IS NULL;",
            reverse_sql='',
        ),
        migrations.AddField(
            model_name='attachment',
            name='name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='xform',
            name='uuid',
            field=models.CharField(default='', max_length=36),
        ),
        migrations.AddField(
            model_name='dataview',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='dataview',
            name='deleted_by',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='dataview_deleted_by', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='xform',
            name='deleted_by',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='xform_deleted_by', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='project',
            name='deleted_by',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='project_deleted_by', to=settings.AUTH_USER_MODEL),
        ),
        migrations.RunPython(
            recalculate_xform_hash
        ),
        migrations.AddField(
            model_name='instance',
            name='deleted_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deleted_instances', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='instance',
            name='has_a_review',
            field=models.BooleanField(default=False, verbose_name='has_a_review'),
        ),
        migrations.CreateModel(
            name='SubmissionReview',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('1', 'Approved'), ('3', 'Pending'), ('2', 'Rejected')], db_index=True, default='3', max_length=1, verbose_name='Status')),
                ('deleted_at', models.DateTimeField(db_index=True, default=None, null=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('deleted_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deleted_reviews', to=settings.AUTH_USER_MODEL)),
                ('instance', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='logger.instance')),
                ('note', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='notes', to='logger.note')),
            ],
        ),
        migrations.AlterModelOptions(
            name='mergedxform',
            options={},
        ),
        migrations.AlterModelOptions(
            name='note',
            options={},
        ),
        migrations.AlterModelOptions(
            name='project',
            options={'permissions': (('add_project_xform', 'Can add xform to project'), ('report_project_xform', 'Can make submissions to the project'), ('transfer_project', 'Can transfer project to different owner'), ('can_export_project_data', 'Can export data in project'), ('view_project_all', 'Can view all associated data'), ('view_project_data', 'Can view submitted data'))},
        ),
        migrations.AlterModelOptions(
            name='xform',
            options={'ordering': ('pk',), 'permissions': (('view_xform_all', 'Can view all associated data'), ('view_xform_data', 'Can view submitted data'), ('report_xform', 'Can make submissions to the form'), ('move_xform', 'Can move form between projects'), ('transfer_xform', 'Can transfer form ownership.'), ('can_export_xform_data', 'Can export form data'), ('delete_submission', 'Can delete submissions from form')), 'verbose_name': 'XForm', 'verbose_name_plural': 'XForms'},
        ),
        migrations.AlterField(
            model_name='attachment',
            name='mimetype',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AlterField(
            model_name='instance',
            name='survey_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='logger.surveytype'),
        ),
        migrations.AlterField(
            model_name='instance',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='instances', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='osmdata',
            name='field_name',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AlterField(
            model_name='osmdata',
            name='osm_type',
            field=models.CharField(default='way', max_length=10),
        ),
        migrations.AlterField(
            model_name='project',
            name='tags',
            field=taggit.managers.TaggableManager(help_text='A comma-separated list of tags.', related_name='project_tags', through='taggit.TaggedItem', to='taggit.Tag', verbose_name='Tags'),
        ),
        migrations.AlterField(
            model_name='widget',
            name='order',
            field=models.PositiveIntegerField(db_index=True, editable=False, verbose_name='order'),
        ),
        migrations.AlterField(
            model_name='widget',
            name='widget_type',
            field=models.CharField(choices=[('charts', 'Charts')], default='charts', max_length=25),
        ),
        migrations.AlterField(
            model_name='xform',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='xform',
            name='sms_id_string',
            field=models.SlugField(default='', editable=False, max_length=100, verbose_name='SMS ID'),
        ),
        migrations.AddField(
            model_name='xform',
            name='public_key',
            field=models.TextField(blank=True, default='', null=True),
        ),
        migrations.AddField(
            model_name='attachment',
            name='deleted_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deleted_attachments', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='xform',
            name='uuid',
            field=models.CharField(db_index=True, default='', max_length=36),
        ),
        migrations.RunPython(generate_uuid_if_missing),
        migrations.RunPython(regenerate_instance_json),
        migrations.CreateModel(
            name='XFormVersion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('xls', models.FileField(upload_to='')),
                ('version', models.CharField(max_length=100)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('xml', models.TextField()),
                ('json', models.TextField()),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('xform', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='versions', to='logger.xform')),
            ],
            options={
                'unique_together': {('xform', 'version')},
            },
        ),
        migrations.RunPython(create_initial_xform_version),
    ]
