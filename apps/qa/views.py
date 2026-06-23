from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AnswerForm, QuestionForm
from .models import Answer, Question


def question_list(request: HttpRequest) -> HttpResponse:
    questions = Question.objects.select_related("author").order_by("-created_at")[:50]
    return render(request, "qa/questions.html", {"questions": questions})


def question_detail(request: HttpRequest, question_id: int) -> HttpResponse:
    question = get_object_or_404(Question.objects.select_related("author"), id=question_id)
    answers = Answer.objects.select_related("author").filter(question=question).order_by("created_at")
    form = AnswerForm()
    return render(request, "qa/detail.html", {"question": question, "answers": answers, "form": form})


@login_required
def ask(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = QuestionForm(request.POST)
        if form.is_valid():
            q = form.save(commit=False)
            q.author = request.user
            q.save()
            return redirect("qa:detail", question_id=q.id)
    else:
        form = QuestionForm()
    return render(request, "qa/ask.html", {"form": form})


@login_required
def answer(request: HttpRequest, question_id: int) -> HttpResponse:
    question = get_object_or_404(Question, id=question_id)
    form = AnswerForm(request.POST)
    if form.is_valid():
        a = form.save(commit=False)
        a.author = request.user
        a.question = question
        a.save()
    return redirect("qa:detail", question_id=question.id)

