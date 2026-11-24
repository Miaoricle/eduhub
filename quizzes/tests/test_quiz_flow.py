"""End-to-end tests through Django's test client: what students, lecturers and admins can do."""

from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from quizzes.models import Answer, Attempt, Choice, Question, Quiz, Topic, User
from quizzes.views import leaderboard_rows


def make_user(username, role=User.Role.STUDENT, **extra):
    return User.objects.create_user(username=username, password="pw-123456!", role=role, **extra)


class QuizFixture(TestCase):
    """A topic with one timed 2-question quiz, a lecturer who wrote it, and a student."""

    def setUp(self):
        self.lecturer = make_user("lect", User.Role.LECTURER)
        self.student = make_user("stud")
        self.topic = Topic.objects.create(name="Testing")
        self.quiz = Quiz.objects.create(topic=self.topic, title="Unit testing", time_limit_minutes=5, author=self.lecturer)
        self.q1 = self.add_question("What does a unit test check?", ["One unit in isolation", "The whole system"], correct=0)
        self.q2 = self.add_question("Which comes first in TDD?", ["The code", "A failing test"], correct=1)

    def add_question(self, text, choices, correct, quiz=None):
        q = Question.objects.create(quiz=quiz or self.quiz, text=text)
        for i, c in enumerate(choices):
            Choice.objects.create(question=q, text=c, is_correct=i == correct, order=i + 1)
        return q

    def right(self, q):
        return q.choices.get(is_correct=True).id

    def wrong(self, q):
        return q.choices.filter(is_correct=False).first().id

    def take_quiz(self, client, answers):
        client.get(reverse("quiz_play", args=[self.quiz.pk]))
        return client.post(reverse("quiz_submit", args=[self.quiz.pk]), answers)


class RegistrationTests(TestCase):
    def test_signup_always_creates_a_student(self):
        r = self.client.post(
            reverse("register"),
            {
                "username": "sneaky",
                "first_name": "S",
                "last_name": "Y",
                "email": "s@example.com",
                "password1": "a-long-Passw0rd",
                "password2": "a-long-Passw0rd",
                "role": "LECTURER",  # a crafted field that the form must ignore
            },
        )
        self.assertRedirects(r, reverse("dashboard"), fetch_redirect_response=False)
        self.assertEqual(User.objects.get(username="sneaky").role, User.Role.STUDENT)


class GradingTests(QuizFixture):
    def test_grading_is_done_on_the_server(self):
        self.client.force_login(self.student)
        r = self.take_quiz(self.client, {f"q{self.q1.id}": self.right(self.q1), f"q{self.q2.id}": self.wrong(self.q2)})
        attempt = Attempt.objects.get()
        self.assertRedirects(r, reverse("quiz_result", args=[attempt.pk]))
        self.assertEqual((attempt.score, attempt.total, attempt.percentage), (1, 2, 50))
        self.assertFalse(attempt.submitted_late)

    def test_a_choice_from_another_question_is_not_accepted(self):
        self.client.force_login(self.student)
        # correct answer of q2 submitted as the answer to q1
        self.take_quiz(self.client, {f"q{self.q1.id}": self.right(self.q2)})
        attempt = Attempt.objects.get()
        self.assertEqual(attempt.score, 0)
        self.assertIsNone(Answer.objects.get(question=self.q1).selected_choice)

    def test_submitting_twice_does_not_create_a_second_attempt(self):
        self.client.force_login(self.student)
        answers = {f"q{self.q1.id}": self.right(self.q1)}
        self.take_quiz(self.client, answers)
        r = self.client.post(reverse("quiz_submit", args=[self.quiz.pk]), answers)
        self.assertEqual(Attempt.objects.count(), 1)
        self.assertRedirects(r, reverse("quiz_result", args=[Attempt.objects.get().pk]))

    def test_lecturers_and_admins_cannot_take_quizzes_and_strangers_cannot_see_results(self):
        self.client.force_login(self.student)
        self.take_quiz(self.client, {})
        attempt = Attempt.objects.get()

        self.client.force_login(self.lecturer)
        self.assertEqual(self.client.get(reverse("quiz_play", args=[self.quiz.pk])).status_code, 302)
        # the quiz author may review their students' results
        self.assertEqual(self.client.get(reverse("quiz_result", args=[attempt.pk])).status_code, 200)

        other = make_user("other")
        self.client.force_login(other)
        self.assertRedirects(self.client.get(reverse("quiz_result", args=[attempt.pk])), reverse("dashboard"), fetch_redirect_response=False)


class TimerTests(QuizFixture):
    def test_refreshing_resumes_the_same_attempt_and_clock(self):
        self.client.force_login(self.student)
        start = timezone.now()
        with mock.patch("django.utils.timezone.now", return_value=start):
            self.client.get(reverse("quiz_play", args=[self.quiz.pk]))
        with mock.patch("django.utils.timezone.now", return_value=start + timedelta(minutes=2)):
            r = self.client.get(reverse("quiz_play", args=[self.quiz.pk]))
        self.assertEqual(Attempt.objects.count(), 1)
        self.assertEqual(r.context["seconds_left"], 180)  # 5 min limit, 2 min used

    def test_late_submission_is_flagged_not_trusted(self):
        self.client.force_login(self.student)
        start = timezone.now()
        with mock.patch("django.utils.timezone.now", return_value=start):
            self.client.get(reverse("quiz_play", args=[self.quiz.pk]))
        with mock.patch("django.utils.timezone.now", return_value=start + timedelta(minutes=9)):
            # the old version trusted an "elapsed" field from the browser; it's ignored now
            self.client.post(reverse("quiz_submit", args=[self.quiz.pk]), {"elapsed": "10"})
        attempt = Attempt.objects.get()
        self.assertTrue(attempt.submitted_late)
        self.assertEqual(attempt.duration_seconds, 9 * 60)

    def test_an_abandoned_expired_attempt_is_replaced(self):
        self.client.force_login(self.student)
        start = timezone.now()
        with mock.patch("django.utils.timezone.now", return_value=start):
            self.client.get(reverse("quiz_play", args=[self.quiz.pk]))
        with mock.patch("django.utils.timezone.now", return_value=start + timedelta(hours=1)):
            r = self.client.get(reverse("quiz_play", args=[self.quiz.pk]))
        self.assertEqual(Attempt.objects.count(), 1)
        self.assertEqual(r.context["seconds_left"], 300)

    def test_unfinished_attempts_do_not_count_anywhere(self):
        self.client.force_login(self.student)
        self.client.get(reverse("quiz_play", args=[self.quiz.pk]))  # opened, never submitted
        r = self.client.get(reverse("student_dashboard"))
        self.assertEqual(r.context["attempt_count"], 0)
        self.assertEqual(leaderboard_rows(), [])


class LeaderboardTests(QuizFixture):
    def finished(self, student, quiz, score, total=2):
        now = timezone.now()
        return Attempt.objects.create(student=student, quiz=quiz, score=score, total=total, started_at=now, completed_at=now)

    def test_retaking_a_quiz_cannot_farm_points(self):
        farmer, steady = make_user("farmer"), make_user("steady")
        quiz2 = Quiz.objects.create(topic=self.topic, title="Integration testing", author=self.lecturer)
        for _ in range(20):
            self.finished(farmer, self.quiz, 2)  # 100% on one quiz, twenty times
        self.finished(steady, self.quiz, 2)
        self.finished(steady, quiz2, 1)  # 100% + 50% across two quizzes

        rows = leaderboard_rows()
        self.assertEqual([r["student"].username for r in rows], ["steady", "farmer"])
        self.assertEqual((rows[0]["points"], rows[0]["quizzes"], rows[0]["average"]), (150, 2, 75))
        self.assertEqual(rows[1]["points"], 100)

    def test_admin_average_uses_percentages(self):
        admin = make_user("boss", User.Role.ADMIN)
        long_quiz = Quiz.objects.create(topic=self.topic, title="Long", author=self.lecturer)
        self.finished(self.student, self.quiz, 2, total=2)  # 100%
        self.finished(self.student, long_quiz, 5, total=10)  # 50%
        self.client.force_login(admin)
        r = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(r.context["avg_score"], 75)  # the old code averaged raw scores: 3.5


class LecturerTests(QuizFixture):
    def question_post(self, **overrides):
        data = {
            "text": "Which test double records calls?",
            "subtopic": "Test doubles",
            "explanation": "",
            "choice_1": "Spy",
            "choice_2": "Stub",
            "choice_3": "",
            "choice_4": "",
            "correct": "1",
        }
        data.update(overrides)
        return data

    def test_correct_answer_must_be_a_filled_choice(self):
        self.client.force_login(self.lecturer)
        r = self.client.post(reverse("question_add", args=[self.quiz.pk]), self.question_post(correct="3"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("correct", r.context["form"].errors)
        self.assertEqual(self.quiz.questions.count(), 2)

    def test_duplicate_choices_are_rejected(self):
        self.client.force_login(self.lecturer)
        r = self.client.post(reverse("question_add", args=[self.quiz.pk]), self.question_post(choice_2="spy"))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["form"].non_field_errors())

    def test_editing_a_question_keeps_past_answers_linked(self):
        self.client.force_login(self.student)
        picked = self.right(self.q1)
        self.take_quiz(self.client, {f"q{self.q1.id}": picked})

        self.client.force_login(self.lecturer)
        r = self.client.post(
            reverse("question_edit", args=[self.q1.pk]),
            self.question_post(text="What does a unit test check? (edited)", choice_1="A single unit, in isolation", choice_2="The whole system"),
        )
        self.assertRedirects(r, reverse("quiz_questions", args=[self.quiz.pk]))
        answer = Answer.objects.get(question=self.q1)
        self.assertEqual(answer.selected_choice_id, picked)  # the old code deleted and recreated choices
        self.assertEqual(answer.selected_choice.text, "A single unit, in isolation")

    def test_lecturers_can_only_edit_their_own_quizzes(self):
        intruder = make_user("other_lect", User.Role.LECTURER)
        self.client.force_login(intruder)
        self.assertEqual(self.client.get(reverse("quiz_edit", args=[self.quiz.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("question_delete", args=[self.q1.pk])).status_code, 404)
        self.assertTrue(Question.objects.filter(pk=self.q1.pk).exists())

    def test_students_cannot_reach_lecturer_pages(self):
        self.client.force_login(self.student)
        r = self.client.get(reverse("quiz_create"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("login"), r["Location"])

    def test_draft_quizzes_are_hidden_from_students_but_previewable_by_the_author(self):
        self.quiz.is_published = False
        self.quiz.save()
        self.client.force_login(self.student)
        self.assertRedirects(self.client.get(reverse("quiz_detail", args=[self.quiz.pk])), reverse("catalog"))
        self.assertEqual(self.client.get(reverse("quiz_play", args=[self.quiz.pk])).status_code, 404)
        self.client.force_login(self.lecturer)
        self.assertEqual(self.client.get(reverse("quiz_detail", args=[self.quiz.pk])).status_code, 200)


class PageSmokeTests(QuizFixture):
    """Every page renders for the role that can see it (catches template errors)."""

    def test_pages_render(self):
        admin = make_user("boss", User.Role.ADMIN)
        self.client.force_login(self.student)
        self.take_quiz(self.client, {f"q{self.q1.id}": self.right(self.q1)})
        attempt = Attempt.objects.get()
        student_pages = ["student_dashboard", "catalog", "attempt_history", "leaderboard"]
        for name in student_pages:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        for name, arg in [("topic_detail", self.topic.pk), ("quiz_detail", self.quiz.pk), ("quiz_result", attempt.pk)]:
            self.assertEqual(self.client.get(reverse(name, args=[arg])).status_code, 200, name)

        self.client.force_login(self.lecturer)
        for name, args in [("lecturer_dashboard", []), ("quiz_create", []), ("quiz_questions", [self.quiz.pk]),
                           ("question_add", [self.quiz.pk]), ("question_edit", [self.q1.pk]), ("quiz_edit", [self.quiz.pk])]:
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 200, name)

        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse("admin_dashboard")).status_code, 200)

        self.client.logout()
        for name in ["home", "login", "register"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
