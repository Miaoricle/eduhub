"""URL routing for the quizzes app (each use case maps to a view)."""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("dashboard/", views.dashboard, name="dashboard"),
    # Student
    path("student/", views.student_dashboard, name="student_dashboard"),
    path("learn/", views.catalog, name="catalog"),
    path("topic/<int:pk>/", views.topic_detail, name="topic_detail"),
    path("quiz/<int:pk>/", views.quiz_detail, name="quiz_detail"),
    path("quiz/<int:pk>/play/", views.quiz_play, name="quiz_play"),
    path("quiz/<int:pk>/submit/", views.quiz_submit, name="quiz_submit"),
    path("result/<int:pk>/", views.quiz_result, name="quiz_result"),
    path("history/", views.attempt_history, name="attempt_history"),
    path("leaderboard/", views.leaderboard, name="leaderboard"),
    # Lecturer
    path("lecturer/", views.lecturer_dashboard, name="lecturer_dashboard"),
    path("lecturer/quiz/new/", views.quiz_create, name="quiz_create"),
    path("lecturer/quiz/<int:pk>/edit/", views.quiz_edit, name="quiz_edit"),
    path("lecturer/quiz/<int:pk>/questions/", views.quiz_questions, name="quiz_questions"),
    path("lecturer/quiz/<int:pk>/questions/add/", views.question_add, name="question_add"),
    path("lecturer/question/<int:pk>/edit/", views.question_edit, name="question_edit"),
    path("lecturer/question/<int:pk>/delete/", views.question_delete, name="question_delete"),
    # Admin
    path("manage/", views.admin_dashboard, name="admin_dashboard"),
]
