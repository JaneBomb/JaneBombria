from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render
from home.models import RoommatePost

from .models import Message


@login_required
def chat_room(request, posting_id, inquirer_id):
    posting = get_object_or_404(RoommatePost, id=posting_id)

    # Fix 2: Only the posting owner or the designated inquirer can enter
    is_owner = request.user == posting.user
    is_inquirer = request.user.id == inquirer_id

    if not is_owner and not is_inquirer:
        raise PermissionDenied

    return render(
        request,
        "chat/chat_room.html",
        {
            "posting_id": posting_id,
            "inquirer_id": inquirer_id,
        },
    )


@login_required
def inbox(request):
    # Postings the user owns (as poster) — one entry per inquirer per post
    my_posts = RoommatePost.objects.filter(user=request.user)

    posts_with_chats = []
    for p in my_posts:
        # Find all unique inquirers who have messaged this posting
        inquirer_ids = (
            Message.objects.filter(posting_id=p.id)
            .exclude(inquirer_id__isnull=True)
            .values_list("inquirer_id", flat=True)
            .distinct()
        )
        for iid in inquirer_ids:
            inquirer = User.objects.filter(id=iid).first()
            posts_with_chats.append(
                {
                    "post": p,
                    "inquirer_id": iid,
                    "inquirer_name": inquirer.username if inquirer else f"User {iid}",
                    "message_count": Message.objects.filter(posting_id=p.id, inquirer_id=iid).count(),
                    "last_message": Message.objects.filter(posting_id=p.id, inquirer_id=iid).last(),
                }
            )

    # Postings the user has participated in as inquirer
    participated_ids = (
        Message.objects.filter(sender=request.user, inquirer_id=request.user.id)
        .exclude(posting_id__in=my_posts.values_list("id", flat=True))
        .values_list("posting_id", flat=True)
        .distinct()
    )
    participated_chats = [
        {
            "posting_id": pid,
            "inquirer_id": request.user.id,
            "message_count": Message.objects.filter(posting_id=pid, inquirer_id=request.user.id).count(),
            "last_message": Message.objects.filter(posting_id=pid, inquirer_id=request.user.id).last(),
        }
        for pid in participated_ids
    ]

    return render(
        request,
        "chat/inbox.html",
        {
            "posts_with_chats": posts_with_chats,
            "participated_chats": participated_chats,
        },
    )
