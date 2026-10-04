"""Tests for the course assessment feature."""

from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Choice, Course, Enrollment, Lesson, Question, Submission


class AssessmentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("learner", password="CoursePass123!")
        self.course = Course.objects.create(
            name="Django Essentials",
            description="Build reliable web applications with Django.",
            pub_date=date.today(),
        )
        self.enrollment = Enrollment.objects.create(
            user=self.user,
            course=self.course,
            mode=Enrollment.HONOR,
        )
        self.lesson = Lesson.objects.create(
            course=self.course,
            title="Django foundations",
            order=0,
            content="Models, views, and templates.",
        )
        self.question = Question.objects.create(
            lesson=self.lesson,
            question_text="Which features are included with Django?",
            grade=10,
        )
        self.correct_one = Choice.objects.create(
            question=self.question,
            choice_text="Object-relational mapper",
            is_correct=True,
        )
        self.correct_two = Choice.objects.create(
            question=self.question,
            choice_text="Administration site",
            is_correct=True,
        )
        self.incorrect = Choice.objects.create(
            question=self.question,
            choice_text="A JavaScript runtime",
            is_correct=False,
        )

    def test_question_requires_exact_correct_choices(self):
        self.assertTrue(
            self.question.is_get_score([self.correct_one.id, self.correct_two.id])
        )
        self.assertFalse(self.question.is_get_score([self.correct_one.id]))
        self.assertFalse(
            self.question.is_get_score(
                [self.correct_one.id, self.correct_two.id, self.incorrect.id]
            )
        )

    def test_submit_creates_submission_and_redirects_to_result(self):
        self.client.login(username="learner", password="CoursePass123!")
        response = self.client.post(
            reverse("onlinecourse:submit", args=[self.course.id]),
            {
                f"choice_{self.question.id}": [
                    self.correct_one.id,
                    self.correct_two.id,
                ]
            },
        )
        submission = Submission.objects.get(enrollment=self.enrollment)
        self.assertRedirects(
            response,
            reverse(
                "onlinecourse:show_exam_result",
                args=[self.course.id, submission.id],
            ),
        )
        self.assertEqual(submission.choices.count(), 2)

    def test_successful_result_displays_congratulations_and_score(self):
        self.client.login(username="learner", password="CoursePass123!")
        submission = Submission.objects.create(enrollment=self.enrollment)
        submission.choices.set([self.correct_one, self.correct_two])
        response = self.client.get(
            reverse(
                "onlinecourse:show_exam_result",
                args=[self.course.id, submission.id],
            )
        )
        self.assertContains(response, "Congratulations! You passed the exam.")
        self.assertContains(response, "Score: 100%")
        self.assertContains(response, "Exam results")

    def test_result_is_private_to_submission_owner(self):
        other_user = User.objects.create_user("other", password="CoursePass123!")
        submission = Submission.objects.create(enrollment=self.enrollment)
        self.client.login(username=other_user.username, password="CoursePass123!")
        response = self.client.get(
            reverse(
                "onlinecourse:show_exam_result",
                args=[self.course.id, submission.id],
            )
        )
        self.assertEqual(response.status_code, 404)
