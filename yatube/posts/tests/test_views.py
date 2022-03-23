import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django import forms
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from http import HTTPStatus
from shutil import rmtree


from ..models import Group, Post, Follow

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TaskPagesTemplatesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создаем авторизованный клиент
        cls.user = User.objects.create_user(username='TestUser')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        # Создадим группу и пост для проверки
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост, содержащий более 15 символов',
            group=cls.group,
            image=cls.uploaded
        )

        # Темплейты страниц.
        cls.templates_pages_names = {
            reverse('posts:main-view'):
                'posts/index.html',
            reverse('posts:group_posts', args=[cls.group.slug]):
                'posts/group_list.html',
            reverse('posts:profile', args=[cls.user.username]):
                'posts/profile.html',
            reverse('posts:post_detail', args=[cls.post.pk]):
                'posts/post_detail.html',
            reverse('posts:post_edit', args=[cls.post.pk]):
                'posts/create_post.html',
            reverse('posts:post_create'):
                'posts/create_post.html',
        }

        # Поля редактирования/создания поста.
        cls.form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }

        # Ссылка на тестовый файл
        cls.IMAGE_URL = 'posts/small.gif'

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    # Проверяем используемые шаблоны
    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""

        # Проверяем, что вызывается соответствующий HTML-шаблон
        for reverse_name, template in self.templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    # Проверка словаря контекста
    def test_main_page_show_correct_context(self):
        """Проверка контекста: index."""
        response = self.authorized_client.get(reverse('posts:main-view'))
        self.assertIn(self.post, response.context['page_obj'].object_list)
        self.assertEqual(
            response.context['page_obj'].object_list[0].image,
            self.IMAGE_URL
        )

    def test_group_page_show_correct_context(self):
        """Проверка контекста: group_list."""
        response = self.authorized_client.get(
            reverse('posts:group_posts', args=[self.group.slug])
        )
        self.assertIn(self.post, response.context['page_obj'].object_list)
        self.assertEqual(
            response.context['page_obj'].object_list[0].image,
            self.IMAGE_URL
        )

    def test_profile_page_show_correct_context(self):
        """Проверка контекста: profile."""
        response = self.authorized_client.get(
            reverse('posts:profile', args=[self.user.username])
        )
        self.assertIn(self.post, response.context['page_obj'].object_list)
        self.assertEqual(
            response.context['page_obj'].object_list[0].image,
            self.IMAGE_URL
        )

    def test_post_page_show_correct_image(self):
        """Проверка контекста: post_detail."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', args=[self.post.pk])
        )
        self.assertEqual(
            response.context['post'],
            self.post
        )
        self.assertEqual(
            response.context['post'].image,
            self.IMAGE_URL
        )

    def test_edit_post_page_show_correct_context(self):
        """Проверка контекста: форма редактирования поста."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', args=[self.post.pk])
        )

        # Проверяем наличие формы в контексте
        self.assertIsNotNone(response.context.get('form'))

        # Проверяем is_edit == True
        self.assertTrue(response.context.get('is_edit'))

        got_post = response.context.get('form').instance

        # Проверяем что содержание - Post
        self.assertIsInstance(got_post, Post)

        for value, expected in self.form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

        # Проверим еще и совпадение содеражния формы с редактируемым
        self.assertEqual(self.post, got_post)

    def test_create_post_page_show_correct_context(self):
        """Проверка контекста: форма создания поста."""
        response = self.authorized_client.get(
            reverse('posts:post_create')
        )

        for value, expected in self.form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    # Проверка создания поста
    def test_created_post_appears_correctly(self):
        """Дополнительные проверки размещения поста после создания."""
        # Создадим группу и пост для проверки
        new_group = Group.objects.create(
            title='One test group',
            slug='one_test_slug',
            description='One test group',
        )
        new_post = Post.objects.create(
            author=self.user,
            text='Got this text to test',
            group=new_group
        )

        # Проверяем главную страницу
        response = self.authorized_client.get(reverse('posts:main-view'))
        self.assertIn(new_post, response.context['page_obj'].object_list)

        # Проверяем страницы групп
        response = self.authorized_client.get(
            reverse('posts:group_posts', args=[new_group.slug]))
        self.assertIn(new_post, response.context['page_obj'].object_list)

        # Проверяем отсутствие в другой группе
        response = self.authorized_client.get(
            reverse('posts:group_posts', args=[self.group.slug]))
        self.assertNotIn(new_post, response.context['page_obj'].object_list)

        # Проверяем страницу автора
        response = self.authorized_client.get(
            reverse('posts:profile', args=[self.user.username]))
        self.assertIn(new_post, response.context['page_obj'].object_list)

    # Проверка работы кеша
    def test_cache_works_correctly(self):
        """Проверка работы кеша главной страницы."""
        new_post = Post.objects.create(
            author=self.user,
            text='Casche test post',
        )

        # Берем контент главной сраницы
        init_cont = self.client.get(reverse('posts:main-view')).content

        new_post.delete()

        # Проверяем страницу на использование кешированных данных
        new_cont = self.client.get(reverse('posts:main-view')).content
        self.assertEqual(init_cont, new_cont)

        cache.clear()

        # Проверяем главную страницу
        new_cont = self.client.get(reverse('posts:main-view')).content
        self.assertNotEqual(init_cont, new_cont)


# Проверка паджинатора
class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.OVER_PAGE_COUNT = settings.PAGE_SIZE // 2
        cls.TEST_POSTS_CONT = settings.PAGE_SIZE + cls.OVER_PAGE_COUNT
        super().setUpClass()
        # Создаем авторизованный клиент
        cls.user = User.objects.create_user(username='TestUser')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

        # Создадим группу и пост для проверки
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        # Создаем тестовые постов.
        cls.posts = Post.objects.bulk_create([
            Post(
                text=f'{i} тестовый пост, содержащий более 15 символов',
                author=cls.user,
                group=cls.group)
            for i in range(cls.TEST_POSTS_CONT)]
        )

    def test_index_page_contains_ten_records(self):
        """Проверка: количество постов на первой странице."""
        response = self.authorized_client.get(reverse('posts:main-view'))
        self.assertEqual(len(response.context['page_obj']), settings.PAGE_SIZE)

    def test_second_index_page_contains_three_records(self):
        """Проверка: количество постов на второй странице."""
        response = self.authorized_client.get(
            reverse('posts:main-view')
            + '?page=2'
        )
        self.assertEqual(
            len(response.context['page_obj']), self.OVER_PAGE_COUNT)

    def test_group_page_contains_ten_records(self):
        """Проверка: количество постов на 1 странице группы."""
        response = self.authorized_client.get(
            reverse('posts:group_posts', args=[self.group.slug]))
        self.assertEqual(len(response.context['page_obj']), settings.PAGE_SIZE)

    def test_second_group_page_contains_three_records(self):
        """Проверка: количество постов на 2 странице группы."""
        response = self.authorized_client.get(
            reverse('posts:group_posts', args=[self.group.slug])
            + '?page=2')
        self.assertEqual(
            len(response.context['page_obj']), self.OVER_PAGE_COUNT)

    def test_author_contains_ten_records(self):
        """Проверка: количество постов странице автора."""
        response = self.authorized_client.get(
            reverse('posts:profile', args=[self.user.username]))
        self.assertEqual(len(response.context['page_obj']), settings.PAGE_SIZE)

    def test_author_second_page_contains_three_records(self):
        """Проверка: количество постов 2 странице автора."""
        response = self.authorized_client.get(
            reverse('posts:profile', args=[self.user.username])
            + '?page=2')
        self.assertEqual(
            len(response.context['page_obj']), self.OVER_PAGE_COUNT)


# Тестирование подписок
class TaskFollowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.a_user = User.objects.create_user(username='AuthorUser')
        cls.author_client = Client()
        cls.author_client.force_login(cls.a_user)

    def setUp(self):
        self.f_user = User.objects.create_user(username='FollowerUser')
        follow = Follow.objects.create(
            author=self.a_user,
            user=self.f_user
        )
        follow.save()
        self.follower_client = Client()
        self.follower_client.force_login(self.f_user)

        self.nf_user = User.objects.create_user(username='NonFollowerUser')
        self.nonfollower_client = Client()
        self.nonfollower_client.force_login(self.nf_user)

    def test_user_can_follow(self):
        """Проверка возможности подписаться на автора."""
        response = self.follower_client.get(reverse(
            'posts:profile_follow',
            args=[self.a_user.username]), follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(
            response,
            reverse('posts:follow_index')
        )

    def test_user_can_unfollow(self):
        """Проверка возможности отписаться от автора."""
        response = self.follower_client.get(reverse(
            'posts:profile_unfollow',
            args=[self.a_user.username]), follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(
            response,
            reverse('posts:follow_index')
        )

    def test_post_apears_feed(self):
        """Проверка появления поста в ленте подписчиков"""
        new_post = Post.objects.create(
            author=self.a_user,
            text='Got this text to test'
        )
        response = self.follower_client.get(reverse('posts:follow_index'))
        self.assertIn(new_post, response.context['page_obj'].object_list)
        response = self.nonfollower_client.get(reverse('posts:follow_index'))
        self.assertNotIn(new_post, response.context['page_obj'].object_list)
