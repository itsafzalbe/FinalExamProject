from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import Count
from .models import SuppportMessage
from .serializers import SupportSerializer


class SupportAPI(APIView):
    permission_classes = [IsAuthenticated]


    def get(self, request, action=None, user_id=None):
        User = get_user_model()

        if action is None:
            msgs = SuppportMessage.objects.filter(user=request.user).order_by("created_at")
            msgs.filter(is_admin_reply=True, is_read=False).update(is_read=True)
            return Response(SupportSerializer(msgs, many=True).data)

        if action == "list" and request.user.is_staff:
            users = User.objects.filter(support__isnull=False).distinct()
            data = []
            for u in users:
                unread = SuppportMessage.objects.filter(user=u, is_admin_reply=False, is_read=False).count()
                last = SuppportMessage.objects.filter(user=u).order_by("-created_at").first()

                data.append({
                    "user_id": u.id,
                    "username": u.username,
                    "unread_count": unread,
                    "last_message": last.message if last else None,
                    "last_time": last.created_at if last else None
                })

            data.sort(
                key=lambda x: (x["unread_count"], x["last_time"]),
                reverse=True)
            return Response(data)

        if action == "detail" and request.user.is_staff:
            chat_user = get_object_or_404(User, id=user_id)
            msgs = SuppportMessage.objects.filter(user=chat_user).order_by("created_at")
            msgs.filter(is_admin_reply=False, is_read=False).update(is_read=True)
            return Response(SupportSerializer(msgs, many=True).data)

        if action == "unread":
            if request.user.is_staff:
                count = SuppportMessage.objects.filter(is_admin_reply=False, is_read=False ).count()
            else:
                count = SuppportMessage.objects.filter(user=request.user,is_admin_reply=True, is_read=False).count()
            return Response({"unread_count": count})


    def post(self, request, action=None, user_id=None):
        data = request.data.copy()
        if not request.user.is_staff:
            data["is_admin_reply"] = False
            data["user"] = request.user.id
        else:
            if not user_id:
                return Response({"error": "user_id required"}, status=400)
            data["is_admin_reply"] = True
            data["user"] = user_id

        serializer = SupportSerializer(data=data, context={"request": request} )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=201)