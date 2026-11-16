"""python -m unittest discover -v; DOLG6_TEST_DATABASE_URL выбирает отдельную БД, все её таблицы пересоздаются."""

import os
import unittest
from unittest.mock import patch

from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

from app.controllers.profile_controller import ProfileController
from app.controllers.role_controller import RoleController
from app.core.security import verify_password
from app.db import database
from app.models import Profile, Role


class ControllerTests(unittest.TestCase):
    def setUp(self):
        url = os.getenv("DOLG6_TEST_DATABASE_URL", "sqlite://")
        options = {}
        if url.startswith("sqlite"):
            options = {
                "connect_args": {"check_same_thread": False},
                "poolclass": StaticPool,
            }
        self.engine = create_engine(url, **options)
        self.addCleanup(self.engine.dispose)
        if url.startswith("sqlite"):
            event.listen(
                self.engine,
                "connect",
                lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"),
            )
        self.addCleanup(SQLModel.metadata.drop_all, self.engine)
        SQLModel.metadata.drop_all(self.engine)
        SQLModel.metadata.create_all(self.engine)
        self.engine_patch = patch.object(database, "engine", self.engine)
        self.engine_patch.start()
        self.addCleanup(self.engine_patch.stop)

    def add_role(self, name="reader"):
        role = RoleController.add_role(Role(name_role=name))
        self.assertIsNotNone(role)
        self.assertIsInstance(role.id_role, int)
        return role

    def add_profile(self, role_id, email="one@example.test", **fields):
        values = {
            "role_id": role_id,
            "email": email,
            "password": "Пароль123!",
            "first_name": "Иван",
            "second_name": "Иванов",
        }
        values.update(fields)
        result = ProfileController.add_profile(Profile(**values))
        self.assertIsNotNone(result)
        self.assertIsInstance(result.id_users, int)
        return result

    def test_role_crud_duplicates_and_missing_ids(self):
        admin = self.add_role("admin")
        user = self.add_role("user")
        self.assertIsNone(RoleController.add_role(Role(name_role="admin")))
        self.assertEqual(RoleController.count_roles(), 2)
        self.assertEqual(RoleController.get_role_by_id(admin.id_role).name_role, "admin")
        self.assertEqual(RoleController.get_role_by_name("admin").id_role, admin.id_role)
        self.assertIsNone(RoleController.get_role_by_name("missing"))
        self.assertIsNone(RoleController.get_role_by_id(99999))
        unchanged = RoleController.update_role(admin.id_role, Role(name_role="admin"))
        self.assertIsNotNone(unchanged)
        self.assertIsNone(RoleController.update_role(user.id_role, Role(name_role="admin")))
        self.assertEqual(RoleController.get_role_by_id(user.id_role).name_role, "user")
        updated = RoleController.update_role(user.id_role, Role(name_role="manager"))
        self.assertEqual(updated.id_role, user.id_role)
        self.assertEqual(updated.name_role, "manager")
        self.assertIsNone(RoleController.update_role(99999, Role(name_role="missing")))
        self.assertTrue(RoleController.delete_role(user.id_role))
        self.assertFalse(RoleController.delete_role(user.id_role))
        self.assertIsNone(RoleController.get_role_by_id(user.id_role))

    def test_role_queries_and_bulk_deletion(self):
        names = ["viewer", "admin", "editor", "reviewer"]
        for name in names:
            self.add_role(name)
        self.assertEqual([r.name_role for r in RoleController.get_all_roles()], names)
        self.assertEqual(RoleController.count_roles(), 4)
        self.assertEqual(
            [r.name_role for r in RoleController.get_roles_paginated(offset=1, limit=2)],
            ["admin", "editor"],
        )
        self.assertEqual(RoleController.get_roles_paginated(offset=4, limit=2), [])
        self.assertEqual(
            [r.name_role for r in RoleController.search_roles("view")],
            ["viewer", "reviewer"],
        )
        self.assertEqual(RoleController.search_roles("missing"), [])
        self.assertEqual(
            [r.name_role for r in RoleController.get_roles_sorted()], sorted(names)
        )
        self.assertEqual(
            [r.name_role for r in RoleController.get_roles_sorted(descending=True)],
            sorted(names, reverse=True),
        )
        self.assertEqual(RoleController.delete_all_roles(), 4)
        self.assertEqual(RoleController.delete_all_roles(), 0)
        self.assertEqual(RoleController.get_all_roles(), [])
        self.assertEqual(RoleController.count_roles(), 0)

    def test_role_validation(self):
        for name in ["", "   ", "x" * 31]:
            with self.subTest(name_length=len(name)):
                self.assertIsNone(RoleController.add_role(Role(name_role=name)))
        role = self.add_role("reader")
        for name in ["", "x" * 31]:
            self.assertIsNone(RoleController.update_role(role.id_role, Role(name_role=name)))
        self.assertEqual(RoleController.get_role_by_id(role.id_role).name_role, "reader")

    def test_role_deletion_keeps_profiles_and_bulk_deletion_is_atomic(self):
        used = self.add_role("used")
        self.add_role("unused")
        profile = self.add_profile(used.id_role)
        self.assertFalse(RoleController.delete_role(used.id_role))
        self.assertIsNotNone(ProfileController.get_profile_by_id(profile.id_users))
        self.assertEqual(RoleController.delete_all_roles(), 0)
        self.assertEqual(RoleController.count_roles(), 2)
        self.assertEqual(ProfileController.get_profile_by_id(profile.id_users).role_id, used.id_role)
        self.assertTrue(ProfileController.delete_profile(profile.id_users))
        self.assertEqual(RoleController.delete_all_roles(), 2)

    def test_profile_add_hashes_password_without_mutating_input(self):
        role = self.add_role()
        original = Profile(role_id=role.id_role, email="one@example.test", password="Secret123!")
        profile = ProfileController.add_profile(original)
        self.assertIsNotNone(profile)
        self.assertEqual(original.password, "Secret123!")
        self.assertIsNone(original.id_users)
        self.assertTrue(profile.password.startswith("$argon2"))
        self.assertTrue(verify_password("Secret123!", profile.password))
        self.assertNotIn(profile.password, repr(profile))
        fetched = ProfileController.get_profile_by_id(profile.id_users)
        self.assertEqual(fetched.password, profile.password)
        second = self.add_profile(role.id_role, email="two@example.test", password="Secret123!")
        self.assertNotEqual(second.password, profile.password)

    def test_profile_queries_and_deletion(self):
        role_one = self.add_role("reader")
        role_two = self.add_role("admin")
        one = self.add_profile(role_one.id_role)
        two = self.add_profile(role_two.id_role, "two@example.test")
        three = self.add_profile(role_one.id_role, "three@example.test")
        self.assertEqual(
            [p.id_users for p in ProfileController.get_all_profiles()],
            [one.id_users, two.id_users, three.id_users],
        )
        self.assertEqual(
            [p.id_users for p in ProfileController.get_profiles_by_role(role_one.id_role)],
            [one.id_users, three.id_users],
        )
        self.assertEqual(ProfileController.get_profiles_by_role(99999), [])
        self.assertIsNone(ProfileController.get_profile_by_id(99999))
        self.assertFalse(ProfileController.delete_profile(99999))
        self.assertTrue(ProfileController.delete_profile(two.id_users))
        self.assertFalse(ProfileController.delete_profile(two.id_users))
        self.assertIsNone(ProfileController.get_profile_by_id(two.id_users))
        self.assertEqual(len(ProfileController.get_all_profiles()), 2)

    def test_profile_duplicates_and_unknown_roles(self):
        role = self.add_role()
        profile = self.add_profile(role.id_role)
        self.assertIsNone(ProfileController.add_profile(
            Profile(role_id=role.id_role, email=profile.email, password="Another123!")
        ))
        self.assertIsNone(ProfileController.add_profile(
            Profile(role_id=99999, email="missing@example.test", password="Secret123!")
        ))
        self.assertEqual(len(ProfileController.get_all_profiles()), 1)
        self.assertIsNotNone(self.add_profile(role.id_role, "next@example.test"))

    def test_profile_authentication(self):
        role = self.add_role()
        profile = self.add_profile(role.id_role)
        found = ProfileController.authenticate(profile.email, "Пароль123!")
        self.assertIsNotNone(found)
        self.assertEqual(found.id_users, profile.id_users)
        self.assertIsNone(ProfileController.authenticate(profile.email, "wrong"))
        self.assertIsNone(ProfileController.authenticate("missing@example.test", "Пароль123!"))

    def test_profile_update_changes_fields_and_password(self):
        old_role = self.add_role("reader")
        new_role = self.add_role("admin")
        profile = self.add_profile(old_role.id_role)
        updated = ProfileController.update_profile(profile.id_users, Profile(
            first_name="Анна", second_name="Петрова", patronymic="Ивановна",
            role_id=new_role.id_role, email="new@example.test", password="NewPassword123!",
        ))
        self.assertIsNotNone(updated)
        self.assertEqual(updated.id_users, profile.id_users)
        self.assertEqual((updated.first_name, updated.second_name, updated.patronymic),
                         ("Анна", "Петрова", "Ивановна"))
        self.assertEqual(updated.role_id, new_role.id_role)
        self.assertIsNone(ProfileController.authenticate("one@example.test", "Пароль123!"))
        self.assertIsNone(ProfileController.authenticate(updated.email, "Пароль123!"))
        self.assertEqual(ProfileController.authenticate(updated.email, "NewPassword123!").id_users,
                         profile.id_users)
        self.assertNotEqual(updated.password, profile.password)

    def test_profile_update_preserves_password_when_unchanged(self):
        role = self.add_role()
        profile = self.add_profile(role.id_role)
        unchanged = ProfileController.update_profile(profile.id_users, Profile(
            role_id=role.id_role, email=profile.email, password="", first_name="Пётр",
        ))
        self.assertEqual(unchanged.password, profile.password)
        round_trip = ProfileController.update_profile(unchanged.id_users, unchanged)
        self.assertEqual(round_trip.password, profile.password)
        self.assertEqual(ProfileController.authenticate(profile.email, "Пароль123!").id_users,
                         profile.id_users)

    def test_profile_update_rejects_duplicates_and_invalid_role(self):
        role = self.add_role()
        first = self.add_profile(role.id_role)
        second = self.add_profile(role.id_role, "two@example.test")
        self.assertIsNone(ProfileController.update_profile(first.id_users, Profile(
            role_id=role.id_role, email=second.email,
        )))
        self.assertIsNone(ProfileController.update_profile(first.id_users, Profile(
            role_id=99999, email=first.email,
        )))
        self.assertIsNone(ProfileController.update_profile(99999, Profile(
            role_id=role.id_role, email="missing@example.test",
        )))
        current = ProfileController.get_profile_by_id(first.id_users)
        self.assertEqual((current.email, current.role_id, current.password),
                         (first.email, role.id_role, first.password))

    def test_profile_validation(self):
        role = self.add_role()
        invalid = [
            {"email": ""},
            {"email": "missing-at"},
            {"email": "x" * 31 + "@example.test"},
            {"password": ""},
            {"first_name": "x" * 51},
            {"second_name": "x" * 51},
            {"patronymic": "x" * 51},
        ]
        for changes in invalid:
            values = {"role_id": role.id_role, "email": "valid@example.test", "password": "Secret123!"}
            values.update(changes)
            with self.subTest(fields=tuple(changes)):
                self.assertIsNone(ProfileController.add_profile(Profile(**values)))
        self.assertEqual(ProfileController.get_all_profiles(), [])
        valid = self.add_profile(role.id_role)
        self.assertIsNone(ProfileController.update_profile(valid.id_users, Profile(
            role_id=role.id_role, email=valid.email, first_name="x" * 51,
        )))
        self.assertEqual(ProfileController.get_profile_by_id(valid.id_users).first_name, "Иван")


if __name__ == "__main__":
    unittest.main()
