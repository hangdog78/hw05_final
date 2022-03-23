from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
    reverse
)
from django.utils import timezone
from django.conf import settings

from .forms import PostForm, CommentForm
from .models import Group, Post, User, Follow
from .utils import _get_page


# Главная страница
def index(request):
    template = 'posts/index.html'
    posts = Post.objects.select_related('group', 'author').all()

    paginator = Paginator(posts, settings.PAGE_SIZE)
    page_obj = _get_page(request, paginator)

    context = {
        'page_obj': page_obj,
        'pages_count': paginator.page_range,
    }
    return render(request, template, context)


# Страница со списком сообществ.
def groups(request):
    groups_list = Group.objects.all()
    template = 'posts/group_view.html'
    context = {
        'groups': groups_list,
    }
    return render(request, template, context)


# Cтраница с постами в сообществе.
def group_posts(request, slug):
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()

    paginator = Paginator(posts, settings.PAGE_SIZE)
    page_obj = _get_page(request, paginator)

    context = {
        'group': group,
        'page_obj': page_obj,
        'pages_count': paginator.page_range
    }
    return render(request, template, context)


# Профиль пользоватаеля.
def profile(request, username):
    template = 'posts/profile.html'
    author = get_object_or_404(User, username=username)
    posts = author.posts.all()
    following = Follow.objects.filter(
        user=request.user,
        author=author
    ).exists()

    paginator = Paginator(posts, settings.PAGE_SIZE)
    page_obj = _get_page(request, paginator)

    context = {
        'posts_count': posts.count,
        'page_obj': page_obj,
        'pages_count': paginator.page_range,
        'author': author,
        'following': following
    }
    return render(request, template, context)


# Страница поста.
def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    comms = post.comments.all()
    form = CommentForm()
    context = {
        'posts_cont': post.author.posts.count(),
        'post': post,
        'comments': comms,
        "form": form,
    }
    return render(request, 'posts/post_detail.html', context)


# Страница создания поста.
@login_required(login_url='users:login')
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST, files=request.FILES or None)
        if form.is_valid():
            post = form.save(commit=False)
            post.pub_date = timezone.now()
            post.author = request.user
            post.save()
            form.save_m2m()
            return redirect(reverse('posts:profile',
                                    args=[request.user.username]))
        else:
            return render(request, 'posts/create_post.html',
                          {'form': form, 'is_edit': False})

    form = PostForm()
    return render(request, 'posts/create_post.html',
                  {'form': form, 'is_edit': False})


# Страница редактирования поста.
@login_required(login_url='users:login')
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)

    if request.user != post.author:
        return redirect(reverse('posts:post_detail', args=[post_id]))

    if request.method == 'POST':
        form = PostForm(
            request.POST or None,
            files=request.FILES or None,
            instance=post
        )
        if form.is_valid():
            form.save()
            return redirect(reverse('posts:post_detail', args=[post_id]))

    form = PostForm(instance=post)
    return render(request, 'posts/create_post.html',
                  {'form': form, 'is_edit': True})


# Страница комментирования поста.
@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
        form.save_m2m()
    return redirect('posts:post_detail', post_id=post_id)


# Страница спика постов по подписке
@login_required(login_url='users:login')
def follow_index(request):
    template = 'posts/follow.html'
    authors_id = request.user.follower.all().values_list(
        'author',
        flat=True
    )
    posts = Post.objects.filter(author_id__in=authors_id)
    paginator = Paginator(posts, settings.PAGE_SIZE)
    page_obj = _get_page(request, paginator)
    context = {
        'page_obj': page_obj,
        'pages_count': paginator.page_range,
    }
    return render(request, template, context)


@login_required(login_url='users:login')
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if Follow.objects.filter(
            user=request.user,
            author=author
    ).exists():
        return redirect('posts:follow_index')
    if author == request.user:
        return redirect('posts:follow_index')

    follow = Follow.objects.create(
        author=author,
        user=request.user
    )
    follow.save()
    cache.clear()
    return redirect('posts:follow_index')


@login_required(login_url='users:login')
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    follow = get_object_or_404(
        Follow,
        author=author,
        user=request.user
    )
    follow.delete()
    cache.clear()
    return redirect('posts:follow_index')
