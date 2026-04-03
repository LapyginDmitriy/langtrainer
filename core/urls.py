from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('review/', views.review, name='review'),
    path('check/', views.check_answer, name='check_answer'),
    path('statistics/', views.statistics, name='statistics'),
    path('words/', views.word_list, name='word_list'),
    path('words/add/', views.word_create, name='word_add'),
    path('words/<int:pk>/edit/', views.word_edit, name='word_edit'),
    path('words/<int:pk>/delete/', views.word_delete, name='word_delete'),
    path('api/words/', views.api_word_list, name='api_word_list'),
    path('select-lesson/', views.select_lesson, name='select_lesson'),
]