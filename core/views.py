import io
import json
import os
import uuid
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
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
from . import utils
from .models import Client, Journalist, Partner, PressRelease
from .serializers import ClientSerializer, JournalistSerializer, PressReleaseSerializer

API_KEY = settings.OPENAI_KEY
client = OpenAI(api_key=API_KEY)


import pdfplumber
from weasyprint import HTML, CSS

def extract_text_from_pdf(pdf_file):
    """Extract raw text from an uploaded MPESA statement PDF file."""
    text_data = []
    
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_data.append(text)

    return "\n".join(text_data)


class GeneratePressReleaseAPI(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        data = request.data
        prompt = data.get("prompt")
        client = data.get("client")
       
        country = data.get("country")
        object_id = data.get("id")
        
        uploaded_file = request.FILES.get("file")
        extracted_text = ""
        if uploaded_file and uploaded_file.name.endswith(".pdf"):
            extracted_text = extract_text_from_pdf(uploaded_file)

        
        if object_id:
            try:
                press_release = PressRelease.objects.get(id=object_id)
            except PressRelease.DoesNotExist:
                press_release = PressRelease.objects.create(id=object_id)
        else:
            press_release = PressRelease.objects.create(id=str(uuid.uuid4()))
        
        
        # Process partners
        partners_data = self._extract_partners_data(request.data, request.FILES)
            

        # Create new partners
        for partner_data in partners_data:
            partner = Partner.objects.create(
                press_release=press_release,
                name=partner_data['name']
            )
            
            # Save partner image if provided
            if 'image' in partner_data and partner_data['image']:
                image_file = partner_data['image']
                image_path = f'partners/{partner.created_at}/{image_file.name}'
                saved_path = default_storage.save(image_path, ContentFile(image_file.read()))
                partner.image = saved_path
                partner.save()


        generated_press_release = utils.get_press_release(
            prompt=prompt, client=client, partners=[partner_data['name'] for partner_data in partners_data ],
              country=country, template=extracted_text
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
    

    def _extract_partners_data(self, data, files):
        """
        Extract partners data from request.data and request.FILES
        
        Handles both form data (partners[0][name], partners[0][image]) format
        and JSON format ({partners: [{name: "...", image: File}]})
        """
        partners = []
        
        # Check if data has a 'partners' key (JSON format)
        if 'partners' in data and isinstance(data['partners'], str):
            try:
                partners_json = json.loads(data['partners'])
                for partner_json in partners_json:
                    partner = {'name': partner_json.get('name', '')}
                    partners.append(partner)
                return partners
            except json.JSONDecodeError:
                pass
        
        # Process form data format: partners[0][name], partners[0][image], etc.
        partner_indices = set()
        for key in data.keys():
            if key.startswith('partners[') and '][name]' in key:
                # Extract index from format "partners[0][name]"
                index = key.split('[')[1].split(']')[0]
                partner_indices.add(index)
        
        for index in partner_indices:
            name_key = f'partners[{index}][name]'
            image_key = f'partners[{index}][image]'
            
            partner = {'name': data.get(name_key, '')}
            
            # Add image if available
            if image_key in files:
                partner['image'] = files[image_key]
                
            partners.append(partner)
            
        return partners


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
        
        pr = PressRelease.objects.get(id=id)

        data = pr.description
        client = Client.objects.filter(name=pr.client).first()
        client_logo = request.build_absolute_uri(client.logo.url)

        partner_logos = [partner.image.url for partner in pr.partners.all() if partner.image]  # Partner logos list

        html_data = render_to_string("preview.html", {"data": data, "client_logo": client_logo, "partner_logos": partner_logos})
        
        html = HTML(
            string=html_data,
            base_url=request.build_absolute_uri("/"),
        )
        
        buffer = io.BytesIO()
        html.write_pdf(target=buffer, stylesheets=[CSS(settings.STATIC_ROOT + "/css/invoice.css")])
        
        pdf = buffer.getvalue()
        
        file_name = "preview.pdf"
        f = open(os.path.join(settings.MEDIA_ROOT, file_name), "wb")
        f.write(pdf)

        return Response({"url": f"media/{file_name}"})

    # def post(self, request):
    #     id = request.data["id"]
    #     pr = PressRelease.objects.get(id=id)
    #     data = pr.description
    #     client = Client.objects.filter(name=pr.client).first()
    #     client_logo = request.build_absolute_uri(client.logo.url)  # Ensure absolute URL

    #     # Pass data and logo URL to template
    #     html_data = render_to_string("preview.html", {"data": data, "client_logo": client_logo})

    #     html = HTML(string=html_data, base_url=request.build_absolute_uri("/"))
    #     buffer = io.BytesIO()
    #     html.write_pdf(target=buffer, 
    #                 #    stylesheets=[CSS(settings.STATIC_ROOT + "/css/invoice.css")]
    #                    )
    #     pdf = buffer.getvalue()

    #     file_name = "preview.pdf"
    #     file_path = os.path.join(settings.MEDIA_ROOT, file_name)
        
    #     with open(file_path, "wb") as f:
    #         f.write(pdf)

    #     return Response({"url": f"media/{file_name}"})
       


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
