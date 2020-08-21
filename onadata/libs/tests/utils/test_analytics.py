# -*- coding: utf-8 -*-
"""
Test onadata.libs.utils.analytics module.
"""
import os
from unittest.mock import MagicMock

from django.contrib.auth.models import User, AnonymousUser
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.test import override_settings

import onadata.libs.utils.analytics
from onadata.apps.api.tests.viewsets.test_abstract_viewset import \
    TestAbstractViewSet
from onadata.apps.api.viewsets.xform_submission_viewset import \
    XFormSubmissionViewSet
from onadata.libs.utils.analytics import get_user_id


class TestAnalytics(TestAbstractViewSet):
    def test_get_user_id(self):
        """Test get_user_id()"""
        self.assertEqual(get_user_id(None), 'anonymous')

        # user1 has no email set
        user1 = User(username='abc')
        self.assertEqual(get_user_id(user1), user1.username)

        # user2 has email set
        user2 = User(username='abc', email='abc@example.com')
        self.assertTrue(len(user2.email) > 0)
        self.assertEqual(get_user_id(user2), user2.email)

    @override_settings(SEGMENT_WRITE_KEY='123', HOSTNAME='test-server')
    def test_track(self):
        """Test analytics.track() function.
        """
        segment_mock = MagicMock()
        onadata.libs.utils.analytics.segment_analytics = segment_mock
        onadata.libs.utils.analytics.init_analytics()
        self.assertEqual(segment_mock.write_key, '123')

        user1 = User(username='abc')
        onadata.libs.utils.analytics.track(user1, 'testing track function')
        segment_mock.track.assert_called_with(
            user1.username,
            'testing track function',
            {'value': 1},
            {'source': 'test-server'})

    @override_settings(
            SEGMENT_WRITE_KEY='123', HOSTNAME='test-server',
            APPOPTICS_API_TOKEN='123')
    def test_submission_tracking(self):
        """Test that submissions are tracked"""
        segment_mock = MagicMock()
        appoptics_mock = MagicMock()
        onadata.libs.utils.analytics.segment_analytics = segment_mock
        onadata.libs.utils.analytics.init_analytics()
        onadata.libs.utils.analytics._appoptics_api = appoptics_mock
        self.assertEqual(segment_mock.write_key, '123')

        # Test out that the track_object_event decorator
        # Tracks created submissions
        view = XFormSubmissionViewSet.as_view({
            'post': 'create',
            'head': 'create'
        })
        self._publish_xls_form_to_project()
        s = self.surveys[0]
        media_file = "1335783522563.jpg"
        path = os.path.join(self.main_directory, 'fixtures',
                            'transportation', 'instances', s, media_file)
        request_path = f"/{self.user.username}/submission"
        with open(path, 'rb') as f:
            f = InMemoryUploadedFile(f, 'media_file', media_file, 'image/jpg',
                                     os.path.getsize(path), None)
            submission_path = os.path.join(
                self.main_directory, 'fixtures',
                'transportation', 'instances', s, s + '.xml')
            with open(submission_path, 'rb') as sf:
                data = {'xml_submission_file': sf, 'media_file': f}
                request = self.factory.post(request_path, data)
                request.user = AnonymousUser()
                response = view(request, username=self.user.username)
                self.assertContains(response, 'Successful submission',
                                    status_code=201)
                self.assertTrue(response.has_header('X-OpenRosa-Version'))
                self.assertTrue(
                    response.has_header('X-OpenRosa-Accept-Content-Length'))
                self.assertTrue(response.has_header('Date'))
                self.assertEqual(response['Content-Type'],
                                 'text/xml; charset=utf-8')
                self.assertEqual(response['Location'],
                                 'http://testserver' + request_path)
        segment_mock.track.assert_called_with(
            'bob@columbia.edu',
            'Submission created',
            {
                'xform_id': 1,
                'organization': 'Bob Inc.',
                'from': 'XML Submissions',
                'label': 'form-1-owned-by-bob',
                'value': 1,
                'event_by': 'anonymous'
            },
            {
                'source': 'test-server',
                'event_by': 'anonymous',
                'organization': 'Bob Inc.',
                'action_from': 'XML Submissions',
                'xform_id': self.xform.pk,
                'path': '/bob/submission',
                'url': 'http://testserver/bob/submission',
                'userAgent': '',
                'ip': '127.0.0.1',
                'userId': self.user.id
            })
        appoptics_mock.submit_measurement.assert_called_with(
            'Submission created',
            1,
            tags={
                'source': 'test-server',
                'event_by': 'anonymous',
                'organization': 'Bob Inc.',
                'action_from': 'XML Submissions',
                'xform_id': self.xform.pk,
                'path': '/bob/submission',
                'url': 'http://testserver/bob/submission',
                'ip': '127.0.0.1',
                'userId': self.user.id})
