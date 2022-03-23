from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from http import HTTPStatus

from ..models import Group, Post

User = get_user_model()


class TaskURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Создаем авторизованый клиент
        cls.author_user = User.objects.create_user(username='TestUser')
        cls.author_client = Client()
        cls.author_client.force_login(cls.author_user)

        # Создаем авторизованый клиент - не являющийся автором
        cls.junior_user = User.objects.create_user(username='JuniorUser')
        cls.junior_client = Client()
        cls.junior_client.force_login(cls.junior_user)

        # Создадим группу и пост для проверки
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author_user,
            text='Тестовый пост, содержащий более 15 символов',
            group=cls.group
        )
        cls.post_page_address = f'/posts/{cls.post.pk}/'
        cls.post_page_edit_address = ''.join([cls.post_page_address, 'edit/'])
        cls.templates_url_names = {
            'posts/index.html': '/',
            'posts/group_list.html': f'/group/{cls.group.slug}/',
            'posts/profile.html': f'/profile/{cls.author_user.username}/',
            'posts/post_detail.html': cls.post_page_address,
        }

    # Проверяем наличие и шаблоны общедоступных страниц
    def test_base_pages_unauthorized(self):
        """Проверка доступности страниц неавторизованному пользователю."""
        for template, url in self.templates_url_names.items():
            with self.subTest(url=url):
                response = self.author_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)
                self.assertTemplateUsed(response, template)

    # Проверяем несуществующую страницу
    def test_unexisting_page_response(self):
        """Проверка ответа на обращение к несуществующей странице."""
        response = self.client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')

    # Проверяем создание поста
    def test_post_create_authorized(self):
        """Проверка доступа к странице создания поста авторизованному юзеру."""
        response = self.author_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_create_anonymous(self):
        """Перенаправление страницы создания для неавторизованного юзера."""
        response = self.client.get('/create/', follow=True)
        self.assertRedirects(response, '/auth/login/?next=/create/')

    # Проверяем редактирование поста
    def test_post_edit_author(self):
        """Проверка доступа к редактирования поста автору"""
        response = self.author_client.get(self.post_page_edit_address)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit_non_author(self):
        """Проверка доступа к редактирования поста не автору"""
        response = self.junior_client.get(self.post_page_edit_address)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(
            response,
            reverse('posts:post_detail', args=[self.post.pk])
        )

    def test_post_edit_unauthorized(self):
        """Проверка редиректа на страницу логина при попытке редактирования"""
        response = self.client.get(
            self.post_page_edit_address,
            follow=True
        )
        self.assertRedirects(
            response,
            f'/auth/login/?next={self.post_page_edit_address}'
        )
