import io
import json
import os

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.http import Http404, StreamingHttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from openai import OpenAI
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from weasyprint import HTML

from . import utils
from .models import Client, Journalist, PressRelease
from .serializers import ClientSerializer, JournalistSerializer, PressReleaseSerializer

API_KEY = settings.OPENAI_KEY
client = OpenAI(api_key=API_KEY)


class GeneratePressReleaseAPI(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        data = request.data
        prompt = data.get("prompt")
        client = data.get("client")
        partner = data.get("partner")
        country = data.get("country")
        object_id = data.get("id")

        generated_press_release = utils.get_press_release(
            prompt=prompt, client=client, partner=partner, country=country
        )

        pr_data = json.loads(generated_press_release)

        try:
            db_pr = PressRelease.objects.get(id=object_id)

        except PressRelease.DoesNotExist:
            raise Http404("PressRelease not found")

        db_pr.client = client
        db_pr.title = pr_data["title"]
        db_pr.partner = pr_data["partner"]
        db_pr.description = pr_data["description"]
        db_pr.content = pr_data["content"]
        db_pr.country = pr_data["country"]
        db_pr.additional_data = pr_data["additional_data"]

        db_pr.save()

        serialized_data = PressReleaseSerializer(db_pr).data
        return Response(serialized_data, status=status.HTTP_201_CREATED)


class ClientListView(APIView):
    permission_classes = []
    authentication_classes = []

    pagination_class = PageNumberPagination

    def get(self, request):
        queryset = Client.objects.all()

        search_query = request.query_params.get("search", None)
        if search_query:
            queryset = queryset.filter(
                Q(email__icontains=search_query)
                | Q(name__icontains=search_query)
                | Q(country__icontains=search_query)
            )

        # Apply pagination
        paginator = self.pagination_class()
        paginated_queryset = paginator.paginate_queryset(queryset, request)

        # Serialize data
        serializer = ClientSerializer(paginated_queryset, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = ClientSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClientDetailView(APIView):
    permission_classes = []
    authentication_classes = []

    def get_object(self, pk):
        try:
            return Client.objects.get(pk=pk)
        except Client.DoesNotExist:
            raise Http404

    def patch(self, request, pk):
        client = self.get_object(pk)
        serializer = ClientSerializer(client, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        client = self.get_object(pk)
        client.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class JournalistDetailView(APIView):
    permission_classes = []
    authentication_classes = []

    def get_object(self, pk):
        try:
            return Journalist.objects.get(pk=pk)
        except Journalist.DoesNotExist:
            raise Http404

    def patch(self, request, pk):
        client = self.get_object(pk)
        serializer = JournalistSerializer(client, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        item = self.get_object(pk)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PressReleaseListCreateView(APIView):
    permission_classes = []
    authentication_classes = []

    pagination_class = PageNumberPagination

    def get(self, request):
        queryset = PressRelease.objects.all()

        search_query = request.query_params.get("search", None)
        if search_query:
            queryset = queryset.filter(
                Q(client__icontains=search_query)
                | Q(title__icontains=search_query)
                | Q(country__icontains=search_query)
            )

        # Apply pagination
        paginator = self.pagination_class()
        paginated_queryset = paginator.paginate_queryset(queryset, request)

        # Serialize data
        serializer = PressReleaseSerializer(paginated_queryset, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = PressReleaseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PressReleaseDetailView(APIView):
    permission_classes = []
    authentication_classes = []

    def get_object(self, pk):
        try:
            return PressRelease.objects.get(pk=pk)
        except PressRelease.DoesNotExist:
            raise Http404

    def get(self, request, pk):
        press_release = self.get_object(pk)
        serializer = PressReleaseSerializer(press_release)
        return Response(serializer.data)

    def patch(self, request, pk):
        press_release = self.get_object(pk)
        serializer = PressReleaseSerializer(
            press_release, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        press_release = self.get_object(pk)
        press_release.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PressPreview(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        id = request.data["id"]

        data = PressRelease.objects.get(id=id).description
        html_data = render_to_string("preview.html", {"data": data})
        html = HTML(string=html_data, base_url=request.build_absolute_uri("/"))
        buffer = io.BytesIO()
        html.write_pdf(target=buffer)
        pdf = buffer.getvalue()

        file_name = "preview.pdf"
        f = open(os.path.join(settings.MEDIA_ROOT, file_name), "wb")
        f.write(pdf)

        return Response({"url": f"media/{file_name}"})
        # response = HttpResponse(content_type='application/pdf')
        # response['Content-Disposition'] = 'attachment; filename="preview.pdf"'
        # response.write(pdf)
        # return response


class PressDistribute(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        recipients = request.data["journalists"]
        id = request.data["id"]
        data = PressRelease.objects.get(id=id).description
        pr = PressRelease.objects.get(id=id)
        if len(recipients) == 0:
            country = request.data["countries"]
            recipients = [
                journalist.email
                for journalist in Journalist.objects.filter(country=country)
            ]

        for recipient in recipients:
            try:
                journalist = Journalist.objects.get(email=recipient)
                pr.shared_with.add(journalist)
                pr.save()
                send_email(request, recipient, data)
            except Journalist.DoesNotExist:
                print(f"Journalist with email {recipient} not found")  #

        # save_client_pdf(request)

        return Response({"message": "success"})


def send_email(request, recipient, press):
    email_from = "pr@wezawire.net"
    data = press
    subject = request.data.get("subject", "New Press Release")
    file_name = request.data.get("file_name", "press_release")
    message = request.data.get("message", "")
    html_string = render_to_string(
        "pdf.html",
        {
            "sender_name": "Wezawire",  # request.user,
            "recipient": recipient,  # Journalist.objects.get(email=recipient).name_of_contact.split(" ")[0],
            "sender_role": "Admin",
        },
    )

    html_data = render_to_string("preview.html", {"data": data})
    html = HTML(string=html_data, base_url=request.build_absolute_uri("/"))
    buffer = io.BytesIO()
    html.write_pdf(target=buffer)
    pdf = buffer.getvalue()

    email_message = EmailMultiAlternatives(
        from_email=email_from,
        to=[recipient],
        subject=subject,
        body=message,
    )

    filename = f"{file_name}.pdf"

    f = open(os.path.join(settings.MEDIA_ROOT, filename), "wb")
    f.write(pdf)

    # doc = ClientDocument.objects.create(client=request.user, title=file_name)
    # doc.document.save(file_name, File(io.BytesIO(pdf)))

    mimetype_pdf = "application/pdf"
    # images = DraftImage.objects.filter(draft=press)

    email_message.attach_alternative(html_string, "text/html")
    email_message.attach(filename, pdf, mimetype_pdf)
    # for image in images:
    #              image_path = image.image.path
    #              with open(image_path, 'rb') as img:
    #                 email_message.attach(os.path.basename(image_path), img.read(), 'image/jpeg')
    email_message.template_id = "d-c00dfda29d33494ca0df0c0cab5f1aaa "
    email_message.dynamic_template_data = (
        {"sender_name": "Nick", "recipient": "Nelson", "sender_role": "Admin"},
    )

    email_message.send(fail_silently=False)

    return


def save_client_pdf(request):
    data = request.data["data"]
    request.data["subject"]
    file_name = request.data["file_name"]
    html_data = render_to_string("preview.html", {"data": data})
    html = HTML(string=html_data, base_url=request.build_absolute_uri("/"))
    buffer = io.BytesIO()
    html.write_pdf(target=buffer)
    pdf = buffer.getvalue()

    filename = f"{file_name}.pdf"

    f = open(os.path.join(settings.MEDIA_ROOT, filename), "wb")
    f.write(pdf)

    # doc = ClientDocument.objects.create(client=request.user, title=file_name)
    # doc.document.save(file_name, File(io.BytesIO(pdf)))
    # return doc


def stream_opena_response(request):
    question = json.loads(request.body)["question"]

    def generate_stream():
        response_stream = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": f"{question}"}],
            stream=True,
        )

        for chunk in response_stream:
            if chunk.choices[0].delta.content is not None:
                yield (chunk.choices[0].delta.content)

    return StreamingHttpResponse(generate_stream(), content_type="text/plain")


def index(request):
    return render(request, "index.html", {})


class StreamOpenAIResponseView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        question = request.data.get("question", "")

        def generate_stream():
            response_stream = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": f"{question}"}],
                stream=True,
            )

            for chunk in response_stream:
                if chunk.choices[0].delta.content is not None:
                    yield (chunk.choices[0].delta.content)

        return StreamingHttpResponse(generate_stream(), content_type="text/plain")
