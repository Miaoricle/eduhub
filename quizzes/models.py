"""
EduHub data model (the MODEL layer of Django's Model-Template-View).

Source of truth for the UML class diagram. It demonstrates the four required
relationship types:

    * INHERITANCE   -> User extends Django's AbstractUser
    * AGGREGATION   -> Topic groups many Quizzes (a quiz can outlive its topic)
    * COMPOSITION   -> Quiz owns Questions, Question owns Choices, Attempt owns Answers
    * ASSOCIATION   -> Attempt links a Student (User) and a Quiz
"""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """One account type for everyone. INHERITANCE: extends AbstractUser."""

    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        LECTURER = "LECTURER", "Lecturer"
        ADMIN = "ADMIN", "Admin"

    role = models.CharField(max_length=12, choices=Role.choices, default=Role.STUDENT)

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_lecturer(self):
        return self.role == self.Role.LECTURER

    @property
    def is_platform_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"


class Topic(models.Model):
    """A main Software-Engineering subject area. AGGREGATION: groups quizzes."""

    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(
        max_length=40, default="bi-journal-code",
        help_text="Bootstrap Icon class, e.g. bi-bug.",
    )
    color = models.CharField(
        max_length=20, default="#3b5b8c", help_text="Accent colour (hex)."
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    @property
    def published_quizzes(self):
        return self.quizzes.filter(is_published=True)

    def __str__(self):
        return self.name


class Quiz(models.Model):
    """A quiz that belongs to a Topic and is authored by a Lecturer."""

    class Difficulty(models.TextChoices):
        BEGINNER = "BEGINNER", "Beginner"
        INTERMEDIATE = "INTERMEDIATE", "Intermediate"
        ADVANCED = "ADVANCED", "Advanced"

    topic = models.ForeignKey(
        Topic, on_delete=models.SET_NULL, null=True, related_name="quizzes"
    )
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    difficulty = models.CharField(
        max_length=12, choices=Difficulty.choices, default=Difficulty.BEGINNER
    )
    time_limit_minutes = models.PositiveIntegerField(
        default=10, help_text="Countdown shown to the student (0 = no limit)."
    )
    pass_mark = models.PositiveIntegerField(default=50, help_text="Pass percentage.")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="authored_quizzes"
    )
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["topic__order", "title"]
        verbose_name_plural = "Quizzes"

    @property
    def question_count(self):
        return self.questions.count()

    @property
    def difficulty_color(self):
        return {
            self.Difficulty.BEGINNER: "success",
            self.Difficulty.INTERMEDIATE: "warning",
            self.Difficulty.ADVANCED: "danger",
        }.get(self.difficulty, "secondary")

    def __str__(self):
        return self.title


class Question(models.Model):
    """A single MCQ. COMPOSITION: deleted together with its quiz."""

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    subtopic = models.CharField(max_length=120, blank=True, help_text="Sub-topic tag.")
    explanation = models.TextField(blank=True, help_text="Shown after answering.")
    points = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    @property
    def correct_choice(self):
        return self.choices.filter(is_correct=True).first()

    def __str__(self):
        return self.text[:70]


class Choice(models.Model):
    """An answer option. COMPOSITION: deleted together with its question."""

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.text} {'(correct)' if self.is_correct else ''}"


# Extra time allowed after the countdown hits zero, for slow connections.
SUBMIT_GRACE = timedelta(seconds=30)


class AttemptQuerySet(models.QuerySet):
    def completed(self):
        """Attempts that were submitted. In-progress ones exist while a student is answering."""
        return self.filter(completed_at__isnull=False)

    def in_progress(self):
        return self.filter(completed_at__isnull=True)


class Attempt(models.Model):
    """One student's run through one quiz. ASSOCIATION: student <-> quiz.

    Created when the student opens the quiz (so the server knows when they started)
    and completed when they submit.
    """

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attempts"
    )
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    score = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    submitted_late = models.BooleanField(
        default=False, help_text="Submitted after the time limit (plus a short grace period)."
    )

    objects = AttemptQuerySet.as_manager()

    class Meta:
        ordering = ["-completed_at", "-started_at"]

    @property
    def deadline(self):
        """When the countdown ends, or None for untimed quizzes."""
        minutes = self.quiz.time_limit_minutes
        return self.started_at + timedelta(minutes=minutes) if minutes else None

    def seconds_left(self, now=None):
        if self.deadline is None:
            return None
        return max(0, int((self.deadline - (now or timezone.now())).total_seconds()))

    def is_expired(self, now=None):
        """Past the deadline and the grace period: too late to submit."""
        return self.deadline is not None and (now or timezone.now()) > self.deadline + SUBMIT_GRACE

    @property
    def percentage(self):
        return round((self.score / self.total) * 100) if self.total else 0

    @property
    def passed(self):
        return self.percentage >= self.quiz.pass_mark

    @property
    def duration_seconds(self):
        if self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None

    @property
    def duration_display(self):
        """e.g. "4 min 05 s"; None while the attempt is still in progress."""
        s = self.duration_seconds
        if s is None:
            return None
        return f"{s // 60} min {s % 60:02d} s" if s >= 60 else f"{s} s"

    def __str__(self):
        return f"{self.student.username} - {self.quiz.title} ({self.percentage}%)"


class Answer(models.Model):
    """A student's chosen option for one question. COMPOSITION: owned by Attempt."""

    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.SET_NULL, null=True)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.attempt_id} - Q{self.question_id} - {'OK' if self.is_correct else 'X'}"
