import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.conf import settings
from django.urls import reverse
from django.test import TestCase, Client, override_settings
from shutil import rmtree


from ..models import Post
from ..forms import PostForm, CommentForm

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TaskCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create_user(username='TestUser')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_post(self):
        """Валидная форма создает новый Post с картинкой."""
        posts_count = Post.objects.count()

        POST_TEXT = 'Новый тестовый текст'

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        form = PostForm(data={
            'text': POST_TEXT,
            'image': uploaded,
        })
        self.assertTrue(form.is_valid())

        # Отправляем POST-запрос
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form.data,
            follow=True
        )

        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), posts_count + 1)

        # Сравниваем созданную запись в БД с формой
        self.assertEqual(Post.objects.last().text, form.data['text'])

        # Проверка наличия картинки
        self.assertTrue(
            Post.objects.filter(
                text=POST_TEXT,
                image='posts/small.gif'
            ).exists()
        )

        # Проверяем, сработал ли редирект
        self.assertRedirects(response, reverse(
            'posts:profile',
            args=[self.user.username])
        )

    def test_edit_post(self):
        """Валидная форма редактирования меняет Post."""
        post = Post.objects.create(
            author=self.user,
            text='Тестовый пост, содержащий более 15 символов',
        )
        NEW_POST_TEXT = 'Исправленный текст'

        # Отправляем POST-запрос
        response = self.authorized_client.post(
            reverse('posts:post_edit', args=[post.pk]),
            data={'text': NEW_POST_TEXT},
            follow=True
        )
        post.refresh_from_db()
        self.assertEqual(post.text, NEW_POST_TEXT)

        # Проверяем, сработал ли редирект
        self.assertRedirects(response, reverse(
            'posts:post_detail',
            args=[post.pk])
        )


# Тестирование создания комментариев
class TaskCreateCommentsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create_user(username='TestUser')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост'
        )

    def test_comment_apears_in_post(self):
        """Проверка добавления комментария авторизованным пользователем."""
        form = CommentForm(data={
            'text': 'some comment',
        })
        self.assertTrue(form.is_valid())

        # Отправляем POST-запрос
        response = self.authorized_client.post(
            reverse('posts:add_comment', args=[self.post.pk]),
            data=form.data,
            follow=True
        )

        # Проверяем наличие каментов
        self.assertEqual(self.post.comments.last().text, form.data['text'])

        # Проверяем, сработал ли редирект
        self.assertRedirects(response, reverse(
            'posts:post_detail',
            args=[self.post.pk])
        )

    def test_not_auth_comment(self):
        """Проверка комментирования неавторизованными пользователями."""
        form = CommentForm(data={
            'text': 'some comment',
        })
        self.assertTrue(form.is_valid())

        # Отправляем POST-запрос
        response = self.client.post(
            reverse('posts:add_comment', args=[self.post.pk]),
            data=form.data,
            follow=True
        )

        self.assertNotIsInstance(response.context['form'], CommentForm)
