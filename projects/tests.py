from django.contrib.auth import get_user_model
from django.test import TestCase

from projects.models import Project


User = get_user_model()


class ProjectsViewsTests(TestCase):
    def setUp(self):
        self.password = "StrongPass123!"
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password=self.password,
            name="Owner",
            surname="User",
        )
        self.member = User.objects.create_user(
            email="member@example.com",
            password=self.password,
            name="Member",
            surname="User",
        )
        self.project = Project.objects.create(
            name="Main project",
            description="Description",
            owner=self.owner,
            status=Project.STATUS_OPEN,
        )
        self.project.participants.add(self.owner)

    def test_root_redirects_to_projects_list(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/projects/list/")

    def test_project_list_get_returns_page(self):
        response = self.client.get("/projects/list/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "projects/project_list.html")

    def test_project_list_paginated_by_12(self):
        for idx in range(13):
            proj = Project.objects.create(
                name=f"Project {idx}",
                owner=self.owner,
                status=Project.STATUS_OPEN,
            )
            proj.participants.add(self.owner)
        response_page_1 = self.client.get("/projects/list/")
        self.assertEqual(response_page_1.status_code, 200)
        self.assertEqual(len(response_page_1.context["projects"]), 12)

        response_page_2 = self.client.get("/projects/list/?page=2")
        self.assertEqual(response_page_2.status_code, 200)
        self.assertGreaterEqual(len(response_page_2.context["projects"]), 1)

    def test_project_list_sorted_newest_first(self):
        older = Project.objects.create(
            name="Older project",
            owner=self.owner,
            status=Project.STATUS_OPEN,
        )
        older.participants.add(self.owner)
        newer = Project.objects.create(
            name="Newer project",
            owner=self.owner,
            status=Project.STATUS_OPEN,
        )
        newer.participants.add(self.owner)

        response = self.client.get("/projects/list/")
        projects = list(response.context["projects"])
        self.assertGreater(projects.index(newer), -1)
        self.assertGreater(projects.index(older), -1)
        self.assertLess(projects.index(newer), projects.index(older))

    def test_project_detail_page_loads(self):
        response = self.client.get(f"/projects/{self.project.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "projects/project-details.html")
        self.assertContains(response, self.project.name)

    def test_favorites_requires_login(self):
        response = self.client.get("/projects/favorites/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_favorites_page_for_authorized_user(self):
        self.owner.favorites.add(self.project)
        self.client.force_login(self.owner)
        response = self.client.get("/projects/favorites/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "projects/favorite_projects.html")
        self.assertIn(self.project, list(response.context["projects"]))

    def test_toggle_favorite_adds_project(self):
        self.client.force_login(self.owner)
        response = self.client.post(f"/projects/{self.project.id}/toggle-favorite/")
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "ok", "favorited": True})
        self.assertTrue(self.owner.favorites.filter(id=self.project.id).exists())

    def test_toggle_favorite_removes_project(self):
        self.owner.favorites.add(self.project)
        self.client.force_login(self.owner)
        response = self.client.post(f"/projects/{self.project.id}/toggle-favorite/")
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "ok", "favorited": False})
        self.assertFalse(self.owner.favorites.filter(id=self.project.id).exists())

    def test_toggle_participate_adds_member(self):
        self.client.force_login(self.member)
        response = self.client.post(f"/projects/{self.project.id}/toggle-participate/")
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "ok", "participant": True})
        self.assertTrue(self.project.participants.filter(id=self.member.id).exists())

    def test_toggle_participate_removes_member(self):
        self.project.participants.add(self.member)
        self.client.force_login(self.member)
        response = self.client.post(f"/projects/{self.project.id}/toggle-participate/")
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "ok", "participant": False})
        self.assertFalse(self.project.participants.filter(id=self.member.id).exists())

    def test_complete_project_owner_can_close(self):
        self.client.force_login(self.owner)
        response = self.client.post(f"/projects/{self.project.id}/complete/")
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "ok", "project_status": "closed"})
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.STATUS_CLOSED)

    def test_complete_project_non_owner_gets_403(self):
        self.client.force_login(self.member)
        response = self.client.post(f"/projects/{self.project.id}/complete/")
        self.assertEqual(response.status_code, 403)

    def test_complete_project_closed_returns_403(self):
        self.project.status = Project.STATUS_CLOSED
        self.project.save(update_fields=["status"])
        self.client.force_login(self.owner)
        response = self.client.post(f"/projects/{self.project.id}/complete/")
        self.assertEqual(response.status_code, 403)

    def test_create_project_requires_login(self):
        response = self.client.get("/projects/create-project/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_create_project_post_creates_project_and_adds_owner_to_participants(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            "/projects/create-project/",
            {
                "name": "Created via form",
                "description": "Some description",
                "github_url": "https://github.com/example/repo",
                "status": Project.STATUS_OPEN,
            },
        )
        self.assertEqual(response.status_code, 302)
        created = Project.objects.get(name="Created via form")
        self.assertEqual(created.owner, self.owner)
        self.assertTrue(created.participants.filter(id=self.owner.id).exists())
        self.assertEqual(response.url, f"/projects/{created.id}")

    def test_create_project_rejects_non_github_url(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            "/projects/create-project/",
            {
                "name": "Invalid github",
                "description": "desc",
                "github_url": "https://example.com/repo",
                "status": Project.STATUS_OPEN,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ссылка должна вести на Github.")

    def test_edit_project_owner_get(self):
        self.client.force_login(self.owner)
        response = self.client.get(f"/projects/{self.project.id}/edit/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "projects/create-project.html")
        self.assertTrue(response.context["is_edit"])

    def test_edit_project_non_owner_redirects_to_detail(self):
        self.client.force_login(self.member)
        response = self.client.get(f"/projects/{self.project.id}/edit/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"/projects/{self.project.id}")

    def test_edit_project_owner_post_updates_project(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            f"/projects/{self.project.id}/edit/",
            {
                "name": "Updated name",
                "description": "Updated description",
                "github_url": "https://github.com/example/new-repo",
                "status": Project.STATUS_CLOSED,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "Updated name")
        self.assertEqual(self.project.status, Project.STATUS_CLOSED)
