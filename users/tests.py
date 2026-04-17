from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase

from projects.models import Project


User = get_user_model()


class UsersViewsTests(TestCase):
    def setUp(self):
        self.password = "StrongPass123!"
        self.user = User.objects.create_user(
            email="user1@example.com",
            password=self.password,
            name="Ivan",
            surname="Ivanov",
        )
        self.other_user = User.objects.create_user(
            email="user2@example.com",
            password=self.password,
            name="Petr",
            surname="Petrov",
        )

    def test_register_get_returns_page(self):
        response = self.client.get("/users/register/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "users/register.html")

    def test_register_post_creates_user_and_logs_in(self):
        response = self.client.post(
            "/users/register/",
            {
                "name": "Maria",
                "surname": "Sidorova",
                "email": "maria@example.com",
                "password": "AnotherStrong123!",
            },
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response.url, "/projects/list/")
        self.assertTrue(User.objects.filter(email="maria@example.com").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_get_returns_page(self):
        response = self.client.get("/users/login/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "users/login.html")

    def test_login_post_success_redirects_to_projects(self):
        response = self.client.post(
            "/users/login/",
            {"email": self.user.email, "password": self.password},
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response.url, "/projects/list/")
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_post_invalid_adds_form_error(self):
        response = self.client.post(
            "/users/login/",
            {"email": self.user.email, "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, "Неверный имейл или пароль")

    def test_logout_logs_user_out(self):
        self.client.force_login(self.user)
        response = self.client.get("/users/logout/")
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response.url, "/projects/list/")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_user_detail_page_loads(self):
        response = self.client.get(f"/users/{self.user.id}/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "users/user-details.html")
        self.assertContains(response, self.user.name)

    def test_users_list_paginated_by_12(self):
        for idx in range(13):
            User.objects.create_user(
                email=f"bulk{idx}@example.com",
                password=self.password,
                name=f"Name{idx}",
                surname=f"Surname{idx}",
            )
        response_page_1 = self.client.get("/users/list/")
        self.assertEqual(response_page_1.status_code, HTTPStatus.OK)
        self.assertEqual(len(response_page_1.context["participants"]), 12)

        response_page_2 = self.client.get("/users/list/?page=2")
        self.assertEqual(response_page_2.status_code, HTTPStatus.OK)
        self.assertGreaterEqual(len(response_page_2.context["participants"]), 1)

    def test_users_filter_owners_of_favorite_projects(self):
        self.client.force_login(self.user)
        project = Project.objects.create(name="Test", owner=self.other_user, status=Project.STATUS_OPEN)
        project.participants.add(self.other_user)
        self.user.favorites.add(project)

        response = self.client.get("/users/list/?filter=owners-of-favorite-projects")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn(self.other_user, list(response.context["participants"]))

    def test_users_filter_not_applied_for_anonymous(self):
        project = Project.objects.create(name="Test2", owner=self.other_user, status=Project.STATUS_OPEN)
        project.participants.add(self.other_user)
        self.user.favorites.add(project)

        response = self.client.get("/users/list/?filter=owners-of-favorite-projects")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        participants = list(response.context["participants"])
        self.assertIn(self.user, participants)
        self.assertIn(self.other_user, participants)

    def test_edit_profile_requires_login(self):
        response = self.client.get("/users/edit-profile/")
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertIn("/accounts/login/", response.url)

    def test_edit_profile_post_updates_fields(self):
        self.client.force_login(self.user)
        response = self.client.post(
            "/users/edit-profile/",
            {
                "name": "Updated",
                "surname": "Name",
                "about": "About text",
                "phone": "89991234567",
                "github_url": "https://github.com/example",
            },
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, "Updated")
        self.assertEqual(self.user.phone, "+79991234567")

    def test_edit_profile_rejects_duplicate_phone(self):
        self.other_user.phone = "+79991234567"
        self.other_user.save(update_fields=["phone"])
        self.client.force_login(self.user)
        response = self.client.post(
            "/users/edit-profile/",
            {
                "name": self.user.name,
                "surname": self.user.surname,
                "about": self.user.about,
                "phone": "89991234567",
                "github_url": "https://github.com/example",
            },
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, "Такой номер уже используется другим пользователем.")

    def test_edit_profile_rejects_non_github_url(self):
        self.client.force_login(self.user)
        response = self.client.post(
            "/users/edit-profile/",
            {
                "name": self.user.name,
                "surname": self.user.surname,
                "about": self.user.about,
                "phone": "",
                "github_url": "https://example.com/not-github",
            },
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, "Ссылка должна вести на Github.")

    def test_change_password_requires_login(self):
        response = self.client.get("/users/change-password/")
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertIn("/accounts/login/", response.url)

    def test_change_password_post_success(self):
        self.client.force_login(self.user)
        response = self.client.post(
            "/users/change-password/",
            {
                "old_password": self.password,
                "new_password1": "NewStrongPass123!",
                "new_password2": "NewStrongPass123!",
            },
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewStrongPass123!"))
