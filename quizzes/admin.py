"""Django admin so the Admin role gets full CRUD over the question bank."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Answer, Attempt, Choice, Question, Quiz, Topic, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "role", "is_staff")
    list_filter = ("role", "is_staff")
    fieldsets = DjangoUserAdmin.fieldsets + (("EduHub", {"fields": ("role",)}),)
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (("EduHub", {"fields": ("role",)}),)


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "quiz", "subtopic", "points")
    list_filter = ("quiz__topic", "quiz")
    search_fields = ("text", "subtopic")
    inlines = [ChoiceInline]


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 0
    show_change_link = True


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "topic", "difficulty", "question_count", "is_published", "author")
    list_filter = ("topic", "difficulty", "is_published")
    search_fields = ("title", "description")
    inlines = [QuestionInline]


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "quiz_count")
    ordering = ("order",)

    @admin.display(description="Quizzes")
    def quiz_count(self, obj):
        return obj.quizzes.count()


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ("student", "quiz", "score", "total", "percentage", "completed_at")
    list_filter = ("quiz__topic", "quiz")
    search_fields = ("student__username",)


admin.site.register(Answer)
admin.site.site_header = "EduHub Administration"
admin.site.site_title = "EduHub Admin"
admin.site.index_title = "Manage quizzes, topics and attempts"
