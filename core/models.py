from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Lesson(models.Model):
    """Тематический урок (например, 'Семья', 'Еда')"""
    title = models.CharField(max_length=100, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Word(models.Model):
    """Слово для изучения"""
    word = models.CharField(max_length=100, verbose_name="Слово")
    translation = models.CharField(max_length=200, verbose_name="Перевод")
    transcription = models.CharField(max_length=100, blank=True, verbose_name="Транскрипция")
    part_of_speech = models.CharField(max_length=50, blank=True, verbose_name="Часть речи")
    audio_file = models.FileField(upload_to='audio/', blank=True, null=True, verbose_name="Аудиофайл")
    lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Урок")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.word

class UserWord(models.Model):
    """Связь пользователя со словом (статистика повторений)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    word = models.ForeignKey(Word, on_delete=models.CASCADE)
    stage = models.IntegerField(default=0, verbose_name="Уровень")  # 0-5
    next_review = models.DateField(default=timezone.now, verbose_name="Дата следующего повторения")
    correct_streak = models.IntegerField(default=0, verbose_name="Правильных подряд")

    class Meta:
        unique_together = ('user', 'word')

    def __str__(self):
        return f"{self.user.username} - {self.word.word}"

class Attempt(models.Model):
    """История попыток ответа"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    word = models.ForeignKey(Word, on_delete=models.CASCADE)
    is_correct = models.BooleanField(default=False)
    answer_given = models.CharField(max_length=200, verbose_name="Ответ пользователя")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.word.word} - {self.is_correct}"

class DailyProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    words_reviewed = models.IntegerField(default=0)

    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f"{self.user.username} - {self.date} - {self.words_reviewed}"