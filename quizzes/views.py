"""The VIEW layer: routing logic, role-based access, and quiz grading."""

from collections import defaultdict
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Avg, Count, ExpressionWrapper, F, FloatField, Max, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import QuestionForm, QuizForm, RegistrationForm
from .models import Answer, Attempt, Choice, Question, Quiz, Topic, User

PERCENT = ExpressionWrapper(F("score") * 100.0 / F("total"), output_field=FloatField())


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
    topics = Topic.objects.annotate(
        n_quizzes=Count("quizzes", filter=Q(quizzes__is_published=True), distinct=True)
    )
    sample = (
        Question.objects.filter(quiz__is_published=True)
        .select_related("quiz__topic")
        .prefetch_related("choices")
        .order_by("id")
        .first()
    )
    context = {
        "topics": topics,
        "quiz_count": Quiz.objects.filter(is_published=True).count(),
        "question_count": Question.objects.filter(quiz__is_published=True).count(),
        "topic_count": topics.count(),
        "sample": sample,
    }
    return render(request, "quizzes/home.html", context)


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Account created. Welcome, {user.first_name}.")
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
    completed = list(request.user.attempts.completed().select_related("quiz__topic"))
    context = {
        "attempt_count": len(completed),
        "quizzes_done": len({a.quiz_id for a in completed}),
        "avg_percent": round(sum(a.percentage for a in completed) / len(completed)) if completed else 0,
        "passed_count": sum(1 for a in completed if a.passed),
        "recent": completed[:5],
        "topics": Topic.objects.annotate(
            n_quizzes=Count("quizzes", filter=Q(quizzes__is_published=True), distinct=True)
        ),
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
    quiz = get_object_or_404(Quiz.objects.select_related("topic", "author"), pk=pk)
    # Drafts are only visible to their author (for previewing).
    if not quiz.is_published and quiz.author_id != request.user.id:
        return redirect("catalog")
    best = None
    if request.user.is_student:
        mine = request.user.attempts.completed().filter(quiz=quiz)
        best = max(mine, key=lambda a: a.percentage, default=None)
    context = {"quiz": quiz, "best": best, "attempts": quiz.attempts.completed().count()}
    return render(request, "quizzes/quiz_detail.html", context)


def _current_attempt(student, quiz):
    return Attempt.objects.in_progress().filter(student=student, quiz=quiz).order_by("-started_at").first()


@login_required
@student_required
def quiz_play(request, pk):
    """Start (or resume) an attempt. The clock lives on the server.

    Opening the quiz creates an in-progress Attempt and records when it started.
    Refreshing the page resumes the same attempt, so the timer doesn't reset.
    """
    quiz = get_object_or_404(Quiz, pk=pk, is_published=True)
    questions = list(quiz.questions.prefetch_related("choices"))
    if not questions:
        messages.warning(request, "This quiz has no questions yet.")
        return redirect("quiz_detail", pk=quiz.pk)

    now = timezone.now()
    attempt = _current_attempt(request.user, quiz)
    if attempt and attempt.is_expired(now):
        attempt.delete()  # abandoned and out of time; start fresh
        attempt = None
    if attempt is None:
        attempt = Attempt.objects.create(student=request.user, quiz=quiz, total=len(questions), started_at=now)

    context = {"quiz": quiz, "questions": questions, "attempt": attempt, "seconds_left": attempt.seconds_left(now)}
    return render(request, "quizzes/quiz_play.html", context)


@login_required
@student_required
def quiz_submit(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, is_published=True)
    if request.method != "POST":
        return redirect("quiz_detail", pk=quiz.pk)

    with transaction.atomic():
        attempt = _current_attempt(request.user, quiz)
        if attempt is None:
            # Double submit, or the back button after finishing: show the last result.
            last = request.user.attempts.completed().filter(quiz=quiz).first()
            return redirect("quiz_result", pk=last.pk) if last else redirect("quiz_detail", pk=quiz.pk)

        now = timezone.now()
        questions = list(quiz.questions.prefetch_related("choices"))
        score = 0
        answers = []
        for q in questions:
            selected_id = request.POST.get(f"q{q.id}")
            # Only accept a choice that belongs to this question.
            choice = next((c for c in q.choices.all() if str(c.id) == selected_id), None)
            correct = bool(choice and choice.is_correct)
            score += correct
            answers.append(Answer(attempt=attempt, question=q, selected_choice=choice, is_correct=correct))
        Answer.objects.bulk_create(answers)

        attempt.score = score
        attempt.total = len(questions)
        attempt.completed_at = now
        attempt.submitted_late = attempt.is_expired(now)
        attempt.save()

    if attempt.submitted_late:
        messages.warning(request, "This was submitted after the time limit, so it's marked as late.")
    return redirect("quiz_result", pk=attempt.pk)


@login_required
def quiz_result(request, pk):
    attempt = get_object_or_404(
        Attempt.objects.completed().select_related("quiz__topic", "student"), pk=pk
    )
    u = request.user
    allowed = attempt.student_id == u.id or u.is_platform_admin or attempt.quiz.author_id == u.id
    if not allowed:
        messages.error(request, "You can't view that result.")
        return redirect("dashboard")
    answers = attempt.answers.select_related("question", "selected_choice").prefetch_related(
        "question__choices"
    )
    return render(request, "quizzes/quiz_result.html", {"attempt": attempt, "answers": answers})


@login_required
@student_required
def attempt_history(request):
    attempts = request.user.attempts.completed().select_related("quiz__topic")
    return render(request, "quizzes/history.html", {"attempts": attempts})


def leaderboard_rows(limit=15):
    """Rank students by the sum of their *best* percentage on each quiz.

    Each quiz is worth at most 100 points, so retaking a quiz can raise your
    score on it but can't be repeated to farm points.
    """
    best = (
        Attempt.objects.completed()
        .filter(total__gt=0, student__role=User.Role.STUDENT)
        .values("student", "quiz")
        .annotate(best=Max(PERCENT))
    )
    per_student = defaultdict(list)
    for row in best:
        per_student[row["student"]].append(row["best"])
    users = User.objects.in_bulk(per_student.keys())
    rows = [
        {
            "student": users[sid],
            "quizzes": len(scores),
            "points": round(sum(scores)),
            "average": round(sum(scores) / len(scores)),
        }
        for sid, scores in per_student.items()
    ]
    rows.sort(key=lambda r: (-r["points"], -r["average"], r["student"].username))
    return rows[:limit]


@login_required
def leaderboard(request):
    return render(request, "quizzes/leaderboard.html", {"rows": leaderboard_rows()})


# --------------------------------------------------------------------------- #
# Lecturer
# --------------------------------------------------------------------------- #
@login_required
@lecturer_required
def lecturer_dashboard(request):
    quizzes = list(
        request.user.authored_quizzes.select_related("topic").annotate(
            n_questions=Count("questions", distinct=True),
            n_attempts=Count("attempts", filter=Q(attempts__completed_at__isnull=False), distinct=True),
        )
    )
    recent = (
        Attempt.objects.completed()
        .filter(quiz__author=request.user)
        .select_related("student", "quiz")[:8]
    )
    context = {
        "quizzes": quizzes,
        "total_quizzes": len(quizzes),
        "total_attempts": sum(q.n_attempts for q in quizzes),
        "total_questions": sum(q.n_questions for q in quizzes),
        "recent": recent,
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


def _save_choices(question, form):
    """Create or update the four choice slots in place.

    Updating in place (instead of deleting and recreating) keeps choice ids
    stable, so students' past answers still point at the option they picked.
    """
    texts = form.choice_texts()
    correct_index = int(form.cleaned_data["correct"]) - 1
    existing = {c.order: c for c in question.choices.all()}
    for i, text in enumerate(texts):
        slot = i + 1
        choice = existing.get(slot)
        if text:
            if choice is None:
                choice = Choice(question=question, order=slot)
            choice.text = text
            choice.is_correct = i == correct_index
            choice.save()
        elif choice is not None:
            choice.delete()  # slot emptied; past answers to it become "no answer"


@login_required
@lecturer_required
def question_add(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, author=request.user)
    form = QuestionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data
        with transaction.atomic():
            question = Question.objects.create(
                quiz=quiz, text=cd["text"], subtopic=cd["subtopic"],
                explanation=cd["explanation"], order=quiz.questions.count() + 1,
            )
            _save_choices(question, form)
        messages.success(request, "Question added.")
        return redirect("quiz_questions", pk=quiz.pk)
    return render(request, "quizzes/question_form.html", {"form": form, "quiz": quiz})


@login_required
@lecturer_required
def question_edit(request, pk):
    """Lecturer updates a question and its choices."""
    question = get_object_or_404(
        Question.objects.select_related("quiz"), pk=pk, quiz__author=request.user
    )
    quiz = question.quiz
    if request.method == "POST":
        form = QuestionForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            with transaction.atomic():
                question.text = cd["text"]
                question.subtopic = cd["subtopic"]
                question.explanation = cd["explanation"]
                question.save()
                _save_choices(question, form)
            messages.success(request, "Question updated.")
            return redirect("quiz_questions", pk=quiz.pk)
    else:
        initial = {
            "text": question.text,
            "subtopic": question.subtopic,
            "explanation": question.explanation,
            "correct": "1",
        }
        for choice in question.choices.all():
            if 1 <= choice.order <= 4:
                initial[f"choice_{choice.order}"] = choice.text
                if choice.is_correct:
                    initial["correct"] = str(choice.order)
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
    done = Attempt.objects.completed()
    today = timezone.localdate()
    days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
    per_day = dict(
        done.filter(completed_at__date__gte=days[0])
        .values_list("completed_at__date")
        .annotate(n=Count("id"))
    )

    topic_rows = Topic.objects.annotate(
        n=Count("quizzes__attempts", filter=Q(quizzes__attempts__completed_at__isnull=False))
    ).order_by("-n")

    context = {
        "total_students": User.objects.filter(role=User.Role.STUDENT).count(),
        "total_lecturers": User.objects.filter(role=User.Role.LECTURER).count(),
        "total_quizzes": Quiz.objects.count(),
        "total_topics": Topic.objects.count(),
        "total_questions": Question.objects.count(),
        "total_attempts": done.count(),
        # average of percentages, not of raw scores (quizzes have different lengths)
        "avg_score": round(done.filter(total__gt=0).aggregate(a=Avg(PERCENT))["a"] or 0),
        "late_attempts": done.filter(submitted_late=True).count(),
        "day_labels": [d.strftime("%d %b") for d in days],
        "day_values": [per_day.get(d, 0) for d in days],
        "topic_labels": [t.name for t in topic_rows],
        "topic_values": [t.n for t in topic_rows],
        "recent": done.select_related("student", "quiz")[:8],
    }
    return render(request, "quizzes/admin_dashboard.html", context)

