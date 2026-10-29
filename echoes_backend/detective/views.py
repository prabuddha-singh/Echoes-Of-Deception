
import json
import logging
import os

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_GET
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from uuid import UUID

from .models import Case

load_dotenv()

logger = logging.getLogger(__name__)


def health_check(request):
    return JsonResponse({
        "status": "ok",
        "message": "Echoes of Deception backend is running",
    })


def extract_response_text(response):
    """Extract text safely from a LangChain AIMessage."""
    content = response.content

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        text_parts = []

        for block in content:
            if isinstance(block, dict):
                if (
                    block.get("type") == "text"
                    and isinstance(block.get("text"), str)
                ):
                    text_parts.append(block["text"])

        return "\n".join(text_parts).strip()

    return ""


def validate_case(data):
    """Validate the generated case before saving it."""

    required_fields = {
        "title",
        "introduction",
        "crime_scene_description",
        "suspects",
        "clues",
        "solution",
    }

    if not isinstance(data, dict):
        raise ValueError("The generated case must be a JSON object.")

    if not required_fields.issubset(data):
        raise ValueError("The generated case is missing required fields.")

    for field in (
        "title",
        "introduction",
        "crime_scene_description",
    ):
        if not isinstance(data[field], str) or not data[field].strip():
            raise ValueError(f"Invalid or empty field: {field}")

    suspects = data["suspects"]
    clues = data["clues"]
    solution = data["solution"]

    if not isinstance(suspects, list) or len(suspects) != 3:
        raise ValueError("The case must contain exactly 3 suspects.")

    if not isinstance(clues, list) or len(clues) != 5:
        raise ValueError("The case must contain exactly 5 clues.")

    if not isinstance(solution, dict):
        raise ValueError("The solution must be a JSON object.")

    suspect_ids = set()

    for suspect in suspects:
        if not isinstance(suspect, dict):
            raise ValueError("Invalid suspect entry.")

        for field in ("id", "name", "profile", "alibi"):
            if not isinstance(suspect.get(field), str) or not suspect[field].strip():
                raise ValueError(f"Suspect is missing a valid {field}.")

        suspect_ids.add(suspect["id"])

    if len(suspect_ids) != len(suspects):
        raise ValueError("Suspect IDs must be unique.")

    clue_ids = set()

    for clue in clues:
        if not isinstance(clue, dict):
            raise ValueError("Invalid clue entry.")

        for field in ("id", "name", "description", "location"):
            if not isinstance(clue.get(field), str) or not clue[field].strip():
                raise ValueError(f"Clue is missing a valid {field}.")

        clue_ids.add(clue["id"])

    if len(clue_ids) != len(clues):
        raise ValueError("Clue IDs must be unique.")

    culprit_id = solution.get("culprit_id")

    if culprit_id not in suspect_ids:
        raise ValueError("The solution references an unknown culprit.")

    explanation = solution.get("explanation")

    if not isinstance(explanation, str) or not explanation.strip():
        raise ValueError("The solution needs an explanation.")

    evidence_ids = solution.get("evidence_ids")

    if not isinstance(evidence_ids, list) or not evidence_ids:
        raise ValueError("The solution needs supporting evidence IDs.")

    if not all(
        isinstance(evidence_id, str) and evidence_id in clue_ids
        for evidence_id in evidence_ids
    ):
        raise ValueError("The solution references an unknown clue.")

    return data


@csrf_exempt
@require_POST
def generate_case(request):
    """Generate a detective case, save it, and return public information."""

    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        return JsonResponse(
            {"error": "Gemini API key is not configured."},
            status=500,
        )

    prompt = """
Create one original, fictional detective investigation case.

Return ONLY valid JSON. Do not use Markdown code fences or add commentary.

Use exactly this structure:
{
  "title": "Case title",
  "introduction": "Short introduction for the player",
  "crime_scene_description": "Description of the crime scene",
  "suspects": [
    {
      "id": "suspect_1",
      "name": "Name",
      "profile": "Background and relationship to the victim",
      "alibi": "Claimed alibi"
    }
  ],
  "clues": [
    {
      "id": "clue_1",
      "name": "Clue name",
      "description": "What the player discovers",
      "location": "Where it is found"
    }
  ],
  "solution": {
    "culprit_id": "suspect_1",
    "explanation": "Actual sequence of events and reasoning",
    "evidence_ids": ["clue_1"]
  }
}

Requirements:
- Exactly 3 suspects with unique IDs.
- Exactly 5 clues with unique IDs.
- Exactly one culprit, selected from the 3 suspects.
- All evidence IDs in the solution must refer to existing clues.
- Make the clues, alibis, and solution logically consistent.
- Give the player enough evidence to deduce the culprit.
- Keep all information self-contained and fictional.
- Do not include any fields outside the specified structure.
"""

    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-3.6-flash",
            google_api_key=api_key,
            temperature=0.7,
            timeout=60,
            max_retries=2,
            max_output_tokens=4096,
        )

        response = llm.invoke(prompt)
        content = extract_response_text(response)

        if not content:
            logger.error("Gemini returned no usable text.")
            return JsonResponse(
                {"error": "Gemini returned no usable text."},
                status=502,
            )

        # Handle JSON wrapped in Markdown fences, if returned.
        if content.startswith("```"):
            lines = content.splitlines()

            if lines and lines[0].startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            content = "\n".join(lines).strip()

        case_data = json.loads(content)
        validate_case(case_data)

        saved_case = Case.objects.create(
            title=case_data["title"],
            introduction=case_data["introduction"],
            crime_scene_description=case_data["crime_scene_description"],
            public_data={
                "suspects": case_data["suspects"],
                "clues": case_data["clues"],
            },
            solution=case_data["solution"],
        )

        # Deliberately exclude the solution from the public response.
        return JsonResponse(
            {
                "id": str(saved_case.id),
                "title": saved_case.title,
                "introduction": saved_case.introduction,
                "crime_scene_description": saved_case.crime_scene_description,
                "suspects": saved_case.public_data["suspects"],
                "clues": saved_case.public_data["clues"],
            },
            status=201,
        )

    except json.JSONDecodeError:
        logger.exception("Gemini returned invalid JSON.")
        return JsonResponse(
            {"error": "Gemini returned invalid JSON. Try again."},
            status=502,
        )

    except ValueError as error:
        logger.warning("Generated case failed validation: %s", error)
        return JsonResponse(
            {"error": str(error)},
            status=502,
        )

    except Exception:
        logger.exception("Case generation failed.")
        return JsonResponse(
            {"error": "Case generation failed. Check the Django terminal."},
            status=502,
        )
@require_GET
def get_case(request,case_id):
    """Return public information for a saved detective case"""

    try:
        parsed_id = UUID(str(case_id))
    except (TypeError, ValueError, AttributeError):
        return JsonResponse(
            {"error" : "Invalid case id"},
            status = 400,
        )

    try:
        case = Case.objects.get(id=parsed_id)
    except Case.DoesNotExist:
        return JsonResponse(
            {"error" : "Case not found"},
            status = 404,
        )

    return JsonResponse(
        {
        "id": str(case.id),
        "title": case.title,
        "introduction": case.introduction,
        "crime_scene_description": case.crime_scene_description,
        "suspects": case.public_data.get("suspects", []),
        "clues": case.public_data.get("clues", []),
        }
    )
