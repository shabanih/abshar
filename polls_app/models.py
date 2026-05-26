from django.db import models
from user_app.models import User, Unit, MyHouse


class Poll(models.Model):
    house = models.ForeignKey(MyHouse, on_delete=models.CASCADE, related_name="polls")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Question(models.Model):
    QUESTION_TYPE = (
        ('yesno', 'بلی / خیر'),
        ('single', 'چند گزینه‌ای (یک انتخاب)'),
        ('multi', 'چند انتخابی'),
    )

    poll = models.ForeignKey(
        Poll,
        on_delete=models.CASCADE,
        related_name="questions"
    )

    title = models.CharField(max_length=500)
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPE)

    order = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.title


class Choice(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="choices"
    )

    title = models.CharField(max_length=255)

    def __str__(self):
        return self.title

    def vote_count(self):
        return self.vote_set.count()

    def percentage(self):
        total = Vote.objects.filter(question=self.question).count()
        if total == 0:
            return 0
        return round((self.vote_count() / total) * 100, 1)


class Vote(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE)

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('question', 'user')
