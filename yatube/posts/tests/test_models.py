from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class GroupModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.GROUP_TITLE = 'Тестовая группа'

        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title=cls.GROUP_TITLE,
            slug='tst_slug',
            description='Тестовое описание',
        )

    def test_group_have_correct_object_names(self):
        """Проверка использолвания title для __str__ объекта Group."""
        self.assertEqual(str(self.group), self.GROUP_TITLE)


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.DESCR_CHARS_COUNT = 15
        cls.POST_TITLE = 'Тестовый пост, содержащий набор символов'

        cls.user = User.objects.create_user(username='auth')
        cls.post = Post.objects.create(
            author=cls.user,
            text=cls.POST_TITLE,
        )

    def test_post_have_correct_object_names(self):
        """Проверка использолвания 15 символов для __str__ объекта Post."""
        self.assertEqual(
            str(self.post),
            self.POST_TITLE[:self.DESCR_CHARS_COUNT]
        )
