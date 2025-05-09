from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from src.profiles.models import UserNet
from src.wall.models import Post, Comment
from src.followers.models import Follower
from django.db.models import Q
from django.template.loader import get_template
from django.template import TemplateDoesNotExist
import logging
import requests
from src.profiles.models import Technology

API_BASE_URL = getattr(settings, 'API_BASE_URL', 'http://localhost:8000/api/v1/')
logger = logging.getLogger(__name__)

def make_api_request(method, endpoint, data=None, token=None, files=None):
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if files:
            # For file uploads, don't set Content-Type header
            response = requests.request(method, url, data=data, files=files, headers=headers)
        else:
            # For JSON data
            headers['Content-Type'] = 'application/json'
            response = requests.request(method, url, json=data, headers=headers)
        
        response.raise_for_status()
        
        if response.status_code == 204:
            return None
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"API request error: {str(e)}")
        if e.response is not None:
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
        return None

# Auth views
def login_view(request):
    try:
        template = get_template('auth/login.html')
        logger.info(f"Template found: auth/login.html")
    except TemplateDoesNotExist as e:
        logger.error(f"Template not found: {str(e)}")
        return render(request, 'base.html', {'error': 'Login template not found'})

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        logger.debug(f"Attempting login for user: {username}")
        
        try:
            # First check if user exists
            user_exists = UserNet.objects.filter(username=username).exists()
            if not user_exists:
                logger.warning(f"Login attempt failed: User {username} does not exist")
                messages.error(request, 'Неверный пароль или имя пользователя')
                return render(request, 'auth/login.html')
            
            # Try to authenticate
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    logger.info(f"User {username} successfully logged in")
                    messages.success(request, 'Успешный вход!')
                    return redirect('feed')
                else:
                    logger.warning(f"Login attempt failed: User {username} is inactive")
                    messages.error(request, 'Аккаунт не активен')
            else:
                logger.warning(f"Login attempt failed: Invalid password for user {username}")
                messages.error(request, 'Неверный пароль или имя пользователя')
        except Exception as e:
            logger.error(f"Login error for user {username}: {str(e)}")
            messages.error(request, 'Ошибка во время входа. Повторите позже')
            
    return render(request, 'auth/login.html')

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        
        if UserNet.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'auth/register.html')
            
        try:
            user = UserNet.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            messages.success(request, 'Аккаунт создан')
            return redirect('feed')
        except Exception as e:
            messages.error(request, f'Ошибка во время создания аккаунта: {str(e)}')
    return render(request, 'auth/register.html')

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'Успешный вход')
    return redirect('login')

# Feed views
@login_required
def feed(request):
    try:
        # Get posts from users that the current user follows
        following = Follower.objects.filter(subscriber=request.user).values_list('user_id', flat=True)
        posts = Post.objects.filter(
            Q(user_id__in=following) | Q(user=request.user)
        ).select_related('user').order_by('-create_date')
        
        return render(request, 'feed/feed.html', {'posts': posts})
    except Exception as e:
        logger.error(f"Error loading feed: {str(e)}")
        messages.error(request, 'Ошибка загрузки ленты')
        return render(request, 'feed/feed.html', {'posts': []})

@login_required
def feed_list_view(request):
    try:
        token = request.session.get('access_token')
        posts = make_api_request('GET', 'feed/', token=token)
        if posts is None:
            posts = []
        return render(request, 'feed/feed_list.html', {'posts': posts})
    except Exception as e:
        messages.error(request, f'Ошибка загрузки ленты: {str(e)}')
        return render(request, 'feed/feed_list.html', {'posts': []})

@login_required
def feed_detail_view(request, id):
    try:
        token = request.session.get('access_token')
        post = make_api_request('GET', f'feed/{id}', token=token)
        if post is None:
            messages.error(request, 'Пост не найден')
            return redirect('feed')
        return render(request, 'feed/feed_detail.html', {'post': post})
    except Exception as e:
        messages.error(request, f'Ошибка загрузки поста: {str(e)}')
        return redirect('feed')

# Profile views
@login_required
def profile(request, username):
    try:
        profile = get_object_or_404(UserNet, username=username)
        posts = Post.objects.filter(user=profile).order_by('-create_date')
        is_following = Follower.objects.filter(subscriber=request.user, user=profile).exists()
        
        # Получаем все технологии пользователя
        technologies = profile.technology.all()
        
        return render(request, 'profiles/profile.html', {
            'profile': profile,
            'posts': posts,
            'is_following': is_following,
            'technologies': technologies
        })
    except Exception as e:
        logger.error(f"Error loading profile: {str(e)}")
        messages.error(request, 'Ошибка загрузки профиля')
        return redirect('profiles')

@login_required
def profiles(request):
    try:
        profiles = UserNet.objects.all().exclude(id=request.user.id)
        return render(request, 'profiles/profiles.html', {'profiles': profiles})
    except Exception as e:
        logger.error(f"Error loading profiles: {str(e)}")
        messages.error(request, 'Ошибка загрузки подписок')
        return render(request, 'profiles/profiles.html', {'profiles': []})

@login_required
def profile_detail_view(request, id):
    token = request.session.get('access_token')
    profile = make_api_request('GET', f'profile/{id}/', token=token)
    posts = make_api_request('GET', f'wall/{id}', token=token)
    is_following = False
    
    if request.user.id != id:
        followers = make_api_request('GET', 'follower/', token=token)
        is_following = any(f['subscriber'] == request.user.id for f in followers)
    
    return render(request, 'profiles/profile_detail.html', {
        'profile': profile,
        'posts': posts,
        'is_following': is_following,
        'show_create_form': request.user.id == id
    })

@login_required
def profile_edit(request, id):
    if request.method == 'POST':
        # Handle form submission
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.bio = request.POST.get('bio', '')
        
        # Handle avatar upload
        if 'avatar' in request.FILES:
            user.avatar = request.FILES['avatar']
        
        # Handle technologies
        technology_ids = request.POST.getlist('technology')
        user.technology.set(technology_ids)
        
        user.save()
        messages.success(request, 'Профиль успешно обновлен')
        return redirect('profile', username=user.username)
    
    # Get all technologies for the form
    all_technologies = Technology.objects.all()
    
    return render(request, 'profiles/profile_edit.html', {
        'user': request.user,
        'all_technologies': all_technologies
    })

@login_required
def change_password_view(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect')
            return redirect('change_password')
        
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match')
            return redirect('change_password')
        
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long')
            return redirect('change_password')
        
        try:
            user = UserNet.objects.get(id=request.user.id)
            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully')
            return redirect('profile', username=user.username)
        except UserNet.DoesNotExist:
            messages.error(request, 'User not found')
            return redirect('login')
    
    return render(request, 'profiles/change_password.html')

@login_required
def change_username_view(request):
    if request.method == 'POST':
        new_username = request.POST.get('new_username')
        password = request.POST.get('password')
        
        if not request.user.check_password(password):
            messages.error(request, 'Password is incorrect')
            return redirect('change_username')
        
        if UserNet.objects.filter(username=new_username).exists():
            messages.error(request, 'Username already exists')
            return redirect('change_username')
        
        if len(new_username) < 3:
            messages.error(request, 'Username must be at least 3 characters long')
            return redirect('change_username')
        
        try:
            user = UserNet.objects.get(id=request.user.id)
            user.username = new_username
            user.save()
            messages.success(request, 'Username changed successfully')
            return redirect('profile', username=new_username)
        except UserNet.DoesNotExist:
            messages.error(request, 'User not found')
            return redirect('login')
    
    return render(request, 'profiles/change_username.html')

# Follower views
@login_required
def follower_list_view(request):
    try:
        followers = Follower.objects.filter(user=request.user).select_related('subscriber')
        return render(request, 'followers/follower_list.html', {'followers': followers})
    except Exception as e:
        logger.error(f"Error loading followers: {str(e)}")
        messages.error(request, 'Ошибка загрузки подписчиков')
        return render(request, 'followers/follower_list.html', {'followers': []})

@login_required
def follower_create_view(request, id):
    token = request.session.get('access_token')
    make_api_request('POST', f'follower/{id}/', token=token)
    return redirect('profile_detail', id=id)

@login_required
def follower_delete_view(request, id):
    token = request.session.get('access_token')
    make_api_request('DELETE', f'follower/{id}/', token=token)
    return redirect('follower_list')

# Wall views
@login_required
def post_create_view(request):
    if request.method == 'POST':
        try:
            text = request.POST.get('text')
            image = request.FILES.get('image')
            
            if text:
                post = Post.objects.create(
                    user=request.user,
                    text=text,
                    image=image
                )
                messages.success(request, 'Пост создан')
                return redirect('feed')
            else:
                messages.error(request, 'Текст поста не может быть пустым')
        except Exception as e:
            logger.error(f"Error creating post: {str(e)}")
            messages.error(request, 'Ошибка во время создания поста')
    return render(request, 'wall/post_form.html')

@login_required
def post_detail_view(request, id):
    try:
        post = get_object_or_404(Post, id=id)
        return render(request, 'wall/post_detail.html', {'post': post})
    except Exception as e:
        logger.error(f"Error loading post: {str(e)}")
        messages.error(request, 'Ошибка загрузки поста')
        return redirect('feed')

@login_required
def post_edit_view(request, id):
    post = get_object_or_404(Post, id=id)
    
    if post.user != request.user:
        messages.error(request, 'Вы можете редактировать только свои посты')
        return redirect('feed')
        
    if request.method == 'POST':
        try:
            text = request.POST.get('text')
            if text:
                post.text = text
                post.save()
                messages.success(request, 'Пост успешно обновлен')
                return redirect('post_detail', id=id)
            else:
                messages.error(request, 'Текст поста не может быть пустым')
        except Exception as e:
            logger.error(f"Error updating post: {str(e)}")
            messages.error(request, 'Ошибка во время обновления поста')
    
    return render(request, 'wall/post_form.html', {'post': post})

@login_required
def post_delete_view(request, id):
    try:
        post = get_object_or_404(Post, id=id)
        if post.user == request.user:
            post.delete()
            messages.success(request, 'Пост успешно удален')
        else:
            messages.error(request, 'Вы можете удалять только свои посты')
    except Exception as e:
        logger.error(f"Error deleting post: {str(e)}")
        messages.error(request, 'Ошибка во время удаления поста')
    return redirect('profile', username=request.user.username)

@login_required
def comment_create_view(request):
    if request.method == 'POST':
        try:
            post_id = request.POST.get('post')
            text = request.POST.get('text')
            
            if not post_id or not text:
                messages.error(request, 'Добавьте текст комментария')
                return redirect('feed')
                
            post = get_object_or_404(Post, id=post_id)
            comment = Comment.objects.create(
                user=request.user,
                post=post,
                text=text
            )
            messages.success(request, 'Комментарий опубликован')
            return redirect('post_detail', id=post_id)
        except Exception as e:
            logger.error(f"Error adding comment: {str(e)}")
            messages.error(request, 'Ошибка во время публикации комментария')
    return redirect('feed')

@login_required
def comment_edit_view(request, id):
    comment = get_object_or_404(Comment, id=id)
    
    if comment.user != request.user:
        messages.error(request, 'Вы можете редактировать только свои комментарии')
        return redirect('post_detail', id=comment.post.id)
        
    if request.method == 'POST':
        try:
            text = request.POST.get('text')
            if text:
                comment.text = text
                comment.save()
                messages.success(request, 'Комментарий успешно обновлен')
                return redirect('post_detail', id=comment.post.id)
            else:
                messages.error(request, 'Текст комментария не может быть пустым')
        except Exception as e:
            logger.error(f"Error updating comment: {str(e)}")
            messages.error(request, 'Ошибка во время обновления комментария')
    
    return render(request, 'wall/comment_form.html', {'comment': comment})

@login_required
def comment_delete_view(request, id):
    try:
        comment = get_object_or_404(Comment, id=id)
        if comment.user == request.user:
            post_id = comment.post.id
            comment.delete()
            messages.success(request, 'Комментарий удален')
            return redirect('post_detail', id=post_id)
        else:
            messages.error(request, 'Вы можете удалять только свои комментарии')
    except Exception as e:
        logger.error(f"Error deleting comment: {str(e)}")
        messages.error(request, 'Ошибка во время удаления комментария')
    return redirect('feed')

@login_required
def follow(request, username):
    try:
        user_to_follow = get_object_or_404(UserNet, username=username)
        if user_to_follow != request.user:
            Follower.objects.get_or_create(subscriber=request.user, user=user_to_follow)
            messages.success(request, f'Вы подписаны на {username}')
    except Exception as e:
        logger.error(f"Error following user {username}: {str(e)}")
        messages.error(request, f'Ошибка подписки на пользователя: {str(e)}')
    return redirect('profile', username=username)

@login_required
def unfollow(request, username):
    try:
        user_to_unfollow = get_object_or_404(UserNet, username=username)
        Follower.objects.filter(subscriber=request.user, user=user_to_unfollow).delete()
        messages.success(request, f'Вы отписались от {username}')
    except Exception as e:
        logger.error(f"Error unfollowing user {username}: {str(e)}")
        messages.error(request, f'Ошибка отписки от пользователя: {str(e)}')
    return redirect('profile', username=username)

def home(request):
    return render(request, 'home.html')