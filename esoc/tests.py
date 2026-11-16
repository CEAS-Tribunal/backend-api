from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient, APIRequestFactory

from dashboard.models import ExecMember, ExecRole

from .emailing import send_esoc_request_created
from .models import EsocClub, EsocContact, EsocRequest
from .serializers import EsocRequestCreateSerializer, EsocRequestSerializer


class EsocContactNormalizationTests(TestCase):
    def test_indexed_multipart_fields_are_validated_and_serialized(self):
        data = {
            "organization_name": "Campus Club",
            "requester_name": "Alex Student",
            "requester_email": "alex@example.com",
            "m_number": "M12345678",
            "position": "Treasurer",
            "purpose": "Conference registration",
            "additional_club_0_name": "Robotics Club",
            "additional_club_0_person_0_name": "Jordan Lee",
            "additional_club_0_person_0_email": "jordan@example.com",
            "additional_club_0_person_0_role": "President",
            "w9": SimpleUploadedFile("w9.pdf", b"w9"),
            "application": SimpleUploadedFile("application.pdf", b"application"),
            "slides": SimpleUploadedFile("slides.pdf", b"slides"),
        }
        serializer = EsocRequestCreateSerializer(data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data["additional_clubs"],
            [
                {
                    "clubName": "Robotics Club",
                    "people": [
                        {
                            "name": "Jordan Lee",
                            "email": "jordan@example.com",
                            "role": "President",
                        }
                    ],
                }
            ],
        )

    def test_nested_response_uses_relational_contacts(self):
        request = EsocRequest.objects.create(
            organization_name="Campus Club",
            requester_name="Alex Student",
            requester_email="alex@example.com",
            m_number="M12345678",
            position="Treasurer",
            purpose="Conference registration",
        )
        club = EsocClub.objects.create(request=request, name="Robotics Club", position=0)
        EsocContact.objects.create(
            club=club,
            name="Jordan Lee",
            email="jordan@example.com",
            role="President",
            position=0,
        )

        response = EsocRequestSerializer(
            request,
            context={"request": APIRequestFactory().get("/")},
        ).data

        self.assertEqual(
            response["additional_contacts"],
            [
                {
                    "clubName": "Robotics Club",
                    "people": [
                        {
                            "name": "Jordan Lee",
                            "email": "jordan@example.com",
                            "role": "President",
                        }
                    ],
                }
            ],
        )


class EsocRequestCreateTests(TestCase):
    def test_request_creation_uses_relational_contacts(self):
        client = APIClient()
        data = {
            "organization_name": "Campus Club",
            "requester_name": "Alex Student",
            "requester_email": "alex@example.com",
            "m_number": "M12345678",
            "position": "Treasurer",
            "purpose": "Conference registration",
            "additional_club_0_name": "Robotics Club",
            "additional_club_0_person_0_name": "Jordan Lee",
            "additional_club_0_person_0_email": "jordan@example.com",
            "additional_club_0_person_0_role": "President",
            "w9": SimpleUploadedFile("w9.pdf", b"w9"),
            "application": SimpleUploadedFile("application.pdf", b"application"),
            "slides": SimpleUploadedFile("slides.pdf", b"slides"),
        }

        with patch("esoc.views.send_esoc_request_created"):
            response = client.post("/api/esoc/", data, format="multipart")

        self.assertEqual(response.status_code, 201, response.data)
        request = EsocRequest.objects.get(pk=response.data["id"])
        club = request.additional_clubs.get()
        self.assertEqual(club.name, "Robotics Club")
        self.assertEqual(club.contacts.get().email, "jordan@example.com")


class EsocNotificationEmailTests(TestCase):
    def setUp(self):
        self.request = EsocRequest.objects.create(
            organization_name="Campus Club",
            requester_name="Alex Student",
            requester_email="alex@example.com",
            m_number="M12345678",
            position="Treasurer",
        )

    def _add_member(self, username, email, *roles):
        user = User.objects.create_user(username=username, email=email)
        member = ExecMember.objects.create(user=user)
        for role_name in roles:
            role = ExecRole.objects.create(
                role=role_name,
                description="ESOC testing",
                committee="pres",
            )
            role.ExecMember.add(member)
        return member

    def test_sends_only_to_members_with_sole_esoc_chair_role(self):
        self._add_member("chair", "chair@example.com", "  esoc chair ")
        self._add_member(
            "multi-role",
            "multi@example.com",
            "ESOC Chair",
            "Treasurer",
        )
        self._add_member("other", "other@example.com", "Treasurer")

        self.assertEqual(send_esoc_request_created(self.request), 1)
        self.assertEqual(mail.outbox[0].to, ["chair@example.com"])

    def test_skips_notification_when_no_matching_member_has_email(self):
        self._add_member("no-email", "", "ESOC Chair")

        self.assertEqual(send_esoc_request_created(self.request), 0)
        self.assertEqual(mail.outbox, [])
