from __future__ import annotations

import logging
from typing import Any, Dict

from rest_framework import permissions, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    TranscriptListQuerySerializer,
    TranscriptCreateSerializer,
    UUIDPathSerializer,
    AskQuestionSerializer,
    QuestionsListQuerySerializer,
    QuestionUUIDPathSerializer,
)
from .resemble_client import (
    resemble_list_transcripts,
    resemble_create_transcript_job,
    resemble_get_transcript,
    resemble_ask_transcript,
    resemble_list_questions,
    resemble_get_question,
)

logger = logging.getLogger(__name__)


class TranscriptsListCreateView(APIView):
    """
    Mirrors:
      GET  /api/v2/speech-to-text?page=1&per_page=25
      POST /api/v2/speech-to-text  (multipart: file + optional query)
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        ser = TranscriptListQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        data = resemble_list_transcripts(ser.validated_data)
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        ser = TranscriptCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        f = ser.validated_data.get("file")
        query = ser.validated_data.get("query") or None

        file_tuple = None
        if f:
            # (filename, fileobj, content_type)
            content_type = getattr(f, "content_type", None) or "application/octet-stream"
            file_tuple = (f.name, f.file, content_type)

        data = resemble_create_transcript_job(file_tuple=file_tuple, query=query)
        return Response(data, status=status.HTTP_200_OK)


class TranscriptDetailView(APIView):
    """
    GET /api/v2/speech-to-text/:uuid
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, uuid: str):
        UUIDPathSerializer(data={"uuid": uuid}).is_valid(raise_exception=True)
        data = resemble_get_transcript(uuid)
        return Response(data, status=status.HTTP_200_OK)


class TranscriptAskView(APIView):
    """
    POST /api/v2/speech-to-text/:uuid/ask
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, uuid: str):
        UUIDPathSerializer(data={"uuid": uuid}).is_valid(raise_exception=True)

        ser = AskQuestionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        payload: Dict[str, Any] = dict(ser.validated_data)
        data = resemble_ask_transcript(uuid, payload)
        return Response(data, status=status.HTTP_200_OK)


class TranscriptQuestionsListView(APIView):
    """
    GET /api/v2/speech-to-text/:uuid/questions?page=1&per_page=25
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, uuid: str):
        UUIDPathSerializer(data={"uuid": uuid}).is_valid(raise_exception=True)

        ser = QuestionsListQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)

        data = resemble_list_questions(uuid, ser.validated_data)
        return Response(data, status=status.HTTP_200_OK)


class TranscriptQuestionDetailView(APIView):
    """
    GET /api/v2/speech-to-text/:uuid/questions/:question_uuid
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, uuid: str, question_uuid: str):
        UUIDPathSerializer(data={"uuid": uuid}).is_valid(raise_exception=True)
        QuestionUUIDPathSerializer(data={"question_uuid": question_uuid}).is_valid(raise_exception=True)

        data = resemble_get_question(uuid, question_uuid)
        return Response(data, status=status.HTTP_200_OK)
