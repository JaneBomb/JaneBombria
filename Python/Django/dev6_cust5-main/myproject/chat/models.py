from django.contrib.auth.models import User
from django.db import models


class Message(models.Model):
    posting_id = models.IntegerField()
    inquirer_id = models.IntegerField(null=True, blank=True)  # scopes message to a specific conversation
    sender = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    sender_label = models.CharField(max_length=50)  # username of sender
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"[Posting {self.posting_id}] {self.sender_label}: {self.content[:40]}"
