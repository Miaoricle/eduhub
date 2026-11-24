"""The VIEW layer: routing logic, role-based access, and quiz grading."""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Avg, Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import QuestionForm, QuizForm, RegistrationForm
from .models import Answer, Attempt, Choice, Question, Quiz, Topic, User


# --------------------------------------------------------------------------- #
# Role helpers
# --------------------------------------------------------------------------- #
def _role(*roles):
    def check(u):
        return u.is_authenticated and (u.role in roles or u.is_superuser)

    return user_passes_test(check)


student_required = _role("STUDENT")
lecturer_required = _role("LECTURER")
admin_required = _role("ADMIN")


# --------------------------------------------------------------------------- #
# Public + auth
# --------------------------------------------------------------------------- #
def home(request):
    topics = Topic.objects.prefetch_related("quizzes")
    context = {
        "topics": topics,
        "quiz_count": Quiz.objects.filter(is_published=True).count(),
        "question_count": Question.objects.count(),
        "topic_count": topics.count(),
    }
    return render(request, "quizzes/home.html", context)


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome to EduHub, {user.first_name}!")
        return redirect("dashboard")
    return render(request, "quizzes/register.html", {"form": form})


@login_required
def dashboard(request):
    u = request.user
    if u.is_lecturer:
        return redirect("lecturer_dashboard")
    if u.is_platform_admin:
        return redirect("admin_dashboard")
    return redirect("student_dashboard")


# --------------------------------------------------------------------------- #
# Student
# --------------------------------------------------------------------------- #
@login_required
@student_required
def student_dashboard(request):
    attempts = request.user.attempts.select_related("quiz__topic")
    completed = attempts.filter(completed_at__isnull=False)
    avg = completed.aggregate(a=Avg("score"))["a"]
    context = {
        "attempt_count": completed.count(),
        "quizzes_done": completed.values("quiz").distinct().count(),
        "avg_percent": round((sum(a.percentage for a in completed) / completed.count())) if completed else 0,
        "passed_count": sum(1 for a in completed if a.passed),
        "recent": completed[:5],
        "topics": Topic.objects.prefetch_related("quizzes"),
    }
    return render(request, "quizzes/student_dashboard.html", context)


@login_required
def catalog(request):
    topics = Topic.objects.prefetch_related("quizzes")
    return render(request, "quizzes/catalog.html", {"topics": topics})


@login_required
def topic_detail(request, pk):
    topic = get_object_or_404(Topic, pk=pk)
    return render(request, "quizzes/topic_detail.html", {"topic": topic})


@login_required
def quiz_detail(request, pk):
    quiz = get_object_or_404(
        Quiz.objects.select_related("topic", "author"), pk=pk, is_published=True
    )
    best = None
    if request.user.is_student:
        best = (
            request.user.attempts.filter(quiz=quiz, completed_at__isnull=False)
            .order_by("-score")
            .first()
        )
    context = {"quiz": quiz, "best": best, "attempts": quiz.attempts.count()}
    return render(request, "quizzes/quiz_detail.html", context)


@login_required
@student_required
def quiz_play(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, is_published=True)
    questions = quiz.questions.prefetch_related("choices")
    if not questions:
        messages.warning(request, "This quiz has no questions yet.")
        return redirect("quiz_detail", pk=quiz.pk)
    return render(request, "quizzes/quiz_play.html", {"quiz": quiz, "questions": questions})


@login_required
@student_required
def quiz_submit(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, is_published=True)
    if request.method != "POST":
        return redirect("quiz_detail", pk=quiz.pk)

    questions = list(quiz.questions.prefetch_related("choices"))
    now = timezone.now()
    elapsed = int(request.POST.get("elapsed", 0) or 0)
    attempt = Attempt.objects.create(
        student=request.user,
        quiz=quiz,
        total=len(questions),
        started_at=now - timedelta(seconds=elapsed),
        completed_at=now,
    )

    score = 0
    for q in questions:
        selected_id = request.POST.get(f"q{q.id}")
        choice = next((c for c in q.choices.all() if str(c.id) == selected_id), None)
        is_correct = bool(choice and choice.is_correct)
        if is_correct:
            score += 1
        Answer.objects.create(
            attempt=attempt, question=q, selected_choice=choice, is_correct=is_correct
        )
    attempt.score = score
    attempt.save()
    return redirect("quiz_result", pk=attempt.pk)


@login_required
def quiz_result(request, pk):
    attempt = get_object_or_404(
        Attempt.objects.select_related("quiz__topic", "student"), pk=pk
    )
    if not (attempt.student_id == request.user.id or request.user.is_platform_admin):
        messages.error(request, "You cannot view that result.")
        return redirect("dashboard")
    answers = attempt.answers.select_related("question", "selected_choice").prefetch_related(
        "question__choices"
    )
    return render(request, "quizzes/quiz_result.html", {"attempt": attempt, "answers": answers})


@login_required
@student_required
def attempt_history(request):
    attempts = request.user.attempts.select_related("quiz__topic").filter(
        completed_at__isnull=False
    )
    return render(request, "quizzes/history.html", {"attempts": attempts})


@login_required
def leaderboard(request):
    students = (
        User.objects.filter(role=User.Role.STUDENT)
        .annotate(
            total_score=Sum("attempts__score"),
            attempts_done=Count("attempts"),
        )
        .filter(attempts_done__gt=0)
        .order_by("-total_score")[:15]
    )
    return render(request, "quizzes/leaderboard.html", {"students": students})


# --------------------------------------------------------------------------- #
# Lecturer
# --------------------------------------------------------------------------- #
@login_required
@lecturer_required
def lecturer_dashboard(request):
    quizzes = (
        request.user.authored_quizzes.select_related("topic")
        .annotate(n_questions=Count("questions", distinct=True),
                  n_attempts=Count("attempts", distinct=True))
    )
    context = {
        "quizzes": quizzes,
        "total_quizzes": quizzes.count(),
        "total_attempts": sum(q.n_attempts for q in quizzes),
    }
    return render(request, "quizzes/lecturer_dashboard.html", context)


@login_required
@lecturer_required
def quiz_create(request):
    form = QuizForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        quiz = form.save(commit=False)
        quiz.author = request.user
        quiz.save()
        messages.success(request, "Quiz created. Now add some questions.")
        return redirect("quiz_questions", pk=quiz.pk)
    return render(request, "quizzes/quiz_form.html", {"form": form, "mode": "Create"})


@login_required
@lecturer_required
def quiz_edit(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, author=request.user)
    form = QuizForm(request.POST or None, instance=quiz)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Quiz updated.")
        return redirect("lecturer_dashboard")
    return render(request, "quizzes/quiz_form.html", {"form": form, "mode": "Edit", "quiz": quiz})


@login_required
@lecturer_required
def quiz_questions(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, author=request.user)
    return render(request, "quizzes/quiz_questions.html", {"quiz": quiz})


@login_required
@lecturer_required
def question_add(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, author=request.user)
    form = QuestionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data
        question = Question.objects.create(
            quiz=quiz, text=cd["text"], subtopic=cd["subtopic"],
            explanation=cd["explanation"], order=quiz.questions.count() + 1,
        )
        texts = [cd["choice_1"], cd["choice_2"], cd["choice_3"], cd["choice_4"]]
        correct_index = int(cd["correct"]) - 1
        for i, text in enumerate(texts):
            if text:
                Choice.objects.create(
                    question=question, text=text, is_correct=(i == correct_index), order=i + 1
                )
        messages.success(request, "Question added.")
        return redirect("quiz_questions", pk=quiz.pk)
    return render(request, "quizzes/question_form.html", {"form": form, "quiz": quiz})


@login_required
@lecturer_required
def question_edit(request, pk):
    """Lecturer updates a question's text and rebuilds its choices."""
    question = get_object_or_404(
        Question.objects.select_related("quiz"), pk=pk, quiz__author=request.user
    )
    quiz = question.quiz
    if request.method == "POST":
        form = QuestionForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            question.text = cd["text"]
            question.subtopic = cd["subtopic"]
            question.explanation = cd["explanation"]
            question.save()
            # Replace the old choices with the submitted ones.
            question.choices.all().delete()
            texts = [cd["choice_1"], cd["choice_2"], cd["choice_3"], cd["choice_4"]]
            correct_index = int(cd["correct"]) - 1
            for i, text in enumerate(texts):
                if text:
                    Choice.objects.create(
                        question=question, text=text, is_correct=(i == correct_index), order=i + 1
                    )
            messages.success(request, "Question updated.")
            return redirect("quiz_questions", pk=quiz.pk)
    else:
        initial = {
            "text": question.text,
            "subtopic": question.subtopic,
            "explanation": question.explanation,
            "correct": "1",
        }
        for i, choice in enumerate(question.choices.all()[:4], start=1):
            initial[f"choice_{i}"] = choice.text
            if choice.is_correct:
                initial["correct"] = str(i)
        form = QuestionForm(initial=initial)
    return render(
        request, "quizzes/question_form.html",
        {"form": form, "quiz": quiz, "question": question},
    )


@login_required
@lecturer_required
def question_delete(request, pk):
    """Lecturer removes a question (and its choices) from their quiz."""
    question = get_object_or_404(
        Question.objects.select_related("quiz"), pk=pk, quiz__author=request.user
    )
    quiz = question.quiz
    if request.method == "POST":
        question.delete()
        messages.info(request, "Question deleted.")
    return redirect("quiz_questions", pk=quiz.pk)


# --------------------------------------------------------------------------- #
# Admin
# --------------------------------------------------------------------------- #
@login_required
@admin_required
def admin_dashboard(request):
    today = timezone.localdate()
    day_labels, day_values = [], []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        day_labels.append(day.strftime("%d %b"))
        day_values.append(Attempt.objects.filter(completed_at__date=day).count())

    topic_rows = Topic.objects.annotate(n=Count("quizzes__attempts")).order_by("-n")
    topic_labels = [t.name for t in topic_rows]
    topic_values = [t.n for t in topic_rows]

    context = {
        "total_students": User.objects.filter(role="STUDENT").count(),
        "total_lecturers": User.objects.filter(role="LECTURER").count(),
        "total_quizzes": Quiz.objects.count(),
        "total_topics": Topic.objects.count(),
        "total_questions": Question.objects.count(),
        "total_attempts": Attempt.objects.count(),
        "avg_score": round(
            (Attempt.objects.aggregate(a=Avg("score"))["a"] or 0), 1
        ),
        "day_labels": day_labels,
        "day_values": day_values,
        "topic_labels": topic_labels,
        "topic_values": topic_values,
        "recent": Attempt.objects.select_related("student", "quiz")[:8],
    }
    return render(request, "quizzes/admin_dashboard.html", context)
