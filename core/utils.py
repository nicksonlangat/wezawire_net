import openai
from django.conf import settings

openai.api_key = settings.OPENAI_KEY


additional_data = "Write a press release about the launch of a training program for young entrepreneurs in Zambia by MTN Zambia and impact hub. The 1st paragraph of this training this training is announcing the training. The 2nd paragraph is has facts and statistics about SMEs In Zambia and the importance of supporting young enterprise development. The 3rd paragraph is about be about quote of the minister for SMEs in Zambia and is highlight the importance of SMEs. The programs that the government has carried out and also a thank MTN this particular program. the 4th paragraph indicates that the programme targets 60 young people and the training is over 3 days and is going to feature faculty consisting of various experts Including from Zambia revenue authority and other institutions The next paragraph is has a quote of MTN Zambia CEO Abbad Reda who is going to highlight the commitment of mtn Zambia to Youth development and to help them outdo themselves every day. he's going to talk about the mtn 21 days of y'ello care. The next paragraph provides more details the 21 days Y'ello care 2023 edition in Zambia and in the rest of Africa "

standard_layout = {
    "press_release": {
        "headline": "Short and impactful headline summarizing the announcement",
        "subheadline": "Optional additional context expanding on the headline",
        "introduction": {
            "who": "Who is making the announcement?",
            "what": "What is being announced?",
            "when": "When is this happening?",
            "where": "Where is it relevant?",
            "why": "Why is this important?",
            "how": "How does it work or what does it achieve?",
        },
        "body": [
            {
                "section_title": "Detailed Explanation",
                "content": "Expand on the main announcement, providing specifics about the product, service, or milestone.",
            },
            {
                "section_title": "Supporting Data",
                "content": "Include relevant statistics, studies, or achievements that validate the announcement.",
            },
            {
                "section_title": "Quotes",
                "content": "Statements from the CEO, experts, or key stakeholders adding credibility and perspective.",
            },
            {
                "section_title": "Real-World Applications",
                "content": "How this innovation or announcement impacts users, industries, or communities.",
            },
        ],
        "call_to_action": "Encourage the reader to take the next step, such as visiting the website, attending an event, or contacting the company.",
        "boilerplate": "A short description of the company, including its mission and background.",
        "contact_information": {
            "name": "Contact person’s name",
            "email": "Contact email address",
            "phone": "Contact phone number",
            "website": "Company website or link to the announcement",
        },
    }
}


def get_press_release(prompt: str, client: str, partner: str, country: str):
    prompt = f"""
    Generate a press release for {client} in patnership with {partner} in {country}.
    The press release must have a title, a brief description, and the main content.
    The main press release content must be correctly formatted as HTML
    string using appropriate tags. The content must fill atleast one page PDF. This content will be exported to PDF make sure it looks appealing.
    Follow the standard press release format and make sure to include the following details:
    {prompt}
    """

    response = openai.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that creates DSA software engineering questions .",
            },
            {"role": "user", "content": prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "press_release",
                "schema": {
                    "type": "object",
                    "properties": {
                        "client": {
                            "type": "string",
                            "description": "The name of the client or organization issuing the press release.",
                        },
                        "partner": {
                            "type": "string",
                            "description": "The name of the partner organization collaborating on the press release.",
                        },
                        "country": {
                            "type": "string",
                            "description": "The country where the press release is focused or originated.",
                        },
                        "title": {
                            "type": "string",
                            "description": "The title of the press release.",
                        },
                        "description": {
                            "type": "string",
                            "description": "A brief summary of the press release.",
                        },
                        "content": {
                            "type": "string",
                            "description": "The main content of the press release formatted as an HTML string excluding <body><head> <style> <html> block tags. Format the HTML to be appealing and professional. Add a line break after each paragraph.",
                        },
                        "additional_data": {
                            "type": "object",
                            "description": "Additional relevant information to be included in the press release.",
                            "properties": {
                                "date": {
                                    "type": "string",
                                    "description": "The date of the press release.",
                                },
                                "contact_info": {
                                    "type": "string",
                                    "description": "Contact information for inquiries related to the press release.",
                                },
                            },
                            "required": ["date", "contact_info"],
                            "additionalProperties": False,
                        },
                    },
                    "required": [
                        "client",
                        "partner",
                        "country",
                        "title",
                        "description",
                        "content",
                        "additional_data",
                    ],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        },
    )

    return response.choices[0].message.content
