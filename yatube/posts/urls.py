from django.urls import path

from . import views

app_name = 'posts'


urlpatterns = [
    # Главная страница.
    path('', views.index, name='main-view'),
    # Страница со списком сообществ.
    path('groups/', views.groups, name='groups_list'),
    # Страница со списком постов в сообществе.
    path('group/<str:slug>/', views.group_posts, name='group_posts'),
    # Профайл пользователя
    path('profile/<str:username>/', views.profile, name='profile'),
    # Просмотр записи
    path('posts/<int:post_id>/', views.post_detail, name='post_detail'),
    # Создание поста
    path('create/', views.post_create, name='post_create'),
    # Редактирование поста
    path('posts/<int:post_id>/edit/', views.post_edit, name='post_edit'),
    # Каменты поста
    path(
        'posts/<int:post_id>/comment/',
        views.add_comment,
        name='add_comment'
    ),
]
