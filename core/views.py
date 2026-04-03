from datetime import date
import random

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.utils import timezone
from .models import Word, Lesson, Attempt, UserWord
from .forms import UserRegisterForm, WordForm
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import WordSerializer

# --- Ленивая инициализация для pymorphy2 и ruwordnet ---
_morph = None
_wn = None

def _get_morph():
    global _morph
    if _morph is None:
        import pymorphy2
        _morph = pymorphy2.MorphAnalyzer()
    return _morph

def _get_wn():
    global _wn
    if _wn is None:
        from ruwordnet import RuWordNet
        _wn = RuWordNet()
    return _wn

def is_smart_match(user_answer, correct_answer):
    """
    Умное сравнение ответа с правильным переводом.
    Использует приведение к нормальной форме и словарь синонимов.
    """
    user_answer = user_answer.lower().strip()
    correct_answer = correct_answer.lower().strip()

    # Точное совпадение
    if user_answer == correct_answer:
        return True

    # Приведение к нормальной форме (лемматизация)
    try:
        morph = _get_morph()
        normalized_user = morph.parse(user_answer)[0].normal_form
        if normalized_user == correct_answer:
            return True
    except Exception:
        # Если лемматизация не удалась, игнорируем
        pass

    # Проверка через словарь синонимов RuWordNet
    try:
        wn = _get_wn()
        synsets = wn.get_synsets(correct_answer)
        for synset in synsets:
            for word in synset.get_words():
                if word == normalized_user:
                    return True
    except Exception:
        # Если словарь синонимов недоступен, просто пропускаем
        pass

    return False
# ----------------------------------------------------

class RegisterView(CreateView):
    form_class = UserRegisterForm
    template_name = 'core/register.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.object
        all_words = Word.objects.all()
        for word in all_words:
            UserWord.objects.get_or_create(
                user=user,
                word=word,
                defaults={'stage': 0, 'next_review': timezone.now().date()}
            )
        return response


def home(request):
    return render(request, 'core/home.html')


@login_required
def select_lesson(request):
    lessons = Lesson.objects.all()
    if request.method == 'POST':
        lesson_id = request.POST.get('lesson_id')
        if lesson_id:
            request.session['selected_lesson_id'] = int(lesson_id)
            messages.success(request, "Урок выбран")
        else:
            messages.error(request, "Пожалуйста, выберите урок")
        return redirect('review')
    return render(request, 'core/select_lesson.html', {'lessons': lessons})


@login_required
def review(request):
    lesson_id = request.session.get('selected_lesson_id')
    if not lesson_id:
        messages.warning(request, "Сначала выберите урок для изучения")
        return redirect('select_lesson')

    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        messages.error(request, "Выбранный урок не найден. Выберите снова.")
        return redirect('select_lesson')

    today = timezone.now().date()
    user_words = UserWord.objects.filter(
        user=request.user,
        word__lesson=lesson,
        next_review__lte=today,
        stage__lt=5
    ).select_related('word')

    if not user_words.exists():
        context = {'no_words': True, 'lesson_title': lesson.title}
        return render(request, 'core/review.html', context)

    attempts_today = Attempt.objects.filter(user=request.user, created_at__date=today).count()
    if attempts_today >= 5:
        context = {'limit_reached': True, 'attempts_today': attempts_today, 'lesson_title': lesson.title}
        return render(request, 'core/review.html', context)

    user_word = random.choice(user_words)
    word = user_word.word

    context = {
        'word': word,
        'limit_reached': False,
        'attempts_today': attempts_today,
        'remaining': 5 - attempts_today,
        'lesson_title': lesson.title,
        'user_word': user_word,
    }
    return render(request, 'core/review.html', context)


@login_required
def check_answer(request):
    if request.method != 'POST':
        return redirect('review')

    today = timezone.now().date()
    attempts_today = Attempt.objects.filter(user=request.user, created_at__date=today).count()
    if attempts_today >= 5:
        messages.error(request, "Вы уже использовали все 5 попыток сегодня. Возвращайтесь завтра!")
        return redirect('review')

    word_id = request.POST.get('word_id')
    if not word_id:
        messages.error(request, "Ошибка: слово не выбрано.")
        return redirect('review')

    word = get_object_or_404(Word, id=word_id)
    user_word = get_object_or_404(UserWord, user=request.user, word=word)
    answer = request.POST.get('answer', '').strip()

    is_correct = is_smart_match(answer, word.translation)

    Attempt.objects.create(
        user=request.user,
        word=word,
        is_correct=is_correct,
        answer_given=answer
    )

    if is_correct:
        if user_word.stage < 5:
            user_word.stage += 1
        intervals = [1, 3, 7, 14, 30, 60]
        user_word.next_review = today + timezone.timedelta(days=intervals[user_word.stage])
        user_word.correct_streak += 1
        messages.success(request, f"Правильно! Слово перешло на {user_word.stage} уровень. Следующее повторение через {intervals[user_word.stage]} дней.")
    else:
        user_word.stage = 0
        user_word.next_review = today + timezone.timedelta(days=1)
        user_word.correct_streak = 0
        messages.error(request, f"Неправильно. Правильный ответ: {word.translation}. Уровень сброшен до 0. Повторите завтра.")

    user_word.save()
    return redirect('review')


@login_required
def statistics(request):
    total_words = UserWord.objects.filter(user=request.user).count()
    learned = UserWord.objects.filter(user=request.user, stage=5).count()
    attempts = Attempt.objects.filter(user=request.user)
    total_attempts = attempts.count()
    correct_attempts = attempts.filter(is_correct=True).count()
    success_rate = (correct_attempts / total_attempts * 100) if total_attempts > 0 else 0

    today = timezone.now().date()
    attempts_today = Attempt.objects.filter(user=request.user, created_at__date=today).count()

    context = {
        'total_words': total_words,
        'learned': learned,
        'total_attempts': total_attempts,
        'correct_attempts': correct_attempts,
        'success_rate': round(success_rate, 1),
        'attempts_today': attempts_today,
    }
    return render(request, 'core/statistics.html', context)


@login_required
def word_list(request):
    words = Word.objects.all().select_related('lesson')
    return render(request, 'core/word_list.html', {'words': words})


@login_required
def word_create(request):
    if not request.user.is_staff:
        messages.error(request, "Доступ только для администратора")
        return redirect('word_list')
    if request.method == 'POST':
        form = WordForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Слово добавлено")
            return redirect('word_list')
    else:
        form = WordForm()
    return render(request, 'core/word_form.html', {'form': form, 'title': 'Добавить слово'})


@login_required
def word_edit(request, pk):
    word = get_object_or_404(Word, pk=pk)
    if not request.user.is_staff:
        messages.error(request, "Доступ только для администратора")
        return redirect('word_list')
    if request.method == 'POST':
        form = WordForm(request.POST, request.FILES, instance=word)
        if form.is_valid():
            form.save()
            messages.success(request, "Слово обновлено")
            return redirect('word_list')
    else:
        form = WordForm(instance=word)
    return render(request, 'core/word_form.html', {'form': form, 'title': 'Редактировать слово'})


@login_required
def word_delete(request, pk):
    word = get_object_or_404(Word, pk=pk)
    if not request.user.is_staff:
        messages.error(request, "Доступ только для администратора")
        return redirect('word_list')
    if request.method == 'POST':
        word.delete()
        messages.success(request, "Слово удалено")
        return redirect('word_list')
    return render(request, 'core/word_confirm_delete.html', {'word': word})


@api_view(['GET'])
def api_word_list(request):
    words = Word.objects.all()
    serializer = WordSerializer(words, many=True)
    return Response(serializer.data)