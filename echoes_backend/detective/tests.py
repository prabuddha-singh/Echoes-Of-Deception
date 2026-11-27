
import json
import uuid
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.urls import reverse

from .models import Case


class CaseRetrievalTests(TestCase):

    def setUp(self):
        self.case_id = uuid.uuid4()

        self.case = Case.objects.create(
            id=self.case_id,
            title="The Last Tick of the Clock",
            introduction="A detective investigates a murder.",
            crime_scene_description="A body lies in a conservatory.",
            public_data={
                "suspects": [
                    {
                        "id": "suspect_1",
                        "name": "Clara Vance",
                        "profile": "The victim's niece.",
                        "alibi": "Claims she was at the theatre."
                    }
                ],
                "clues": [
                    {
                        "id": "clue_1",
                        "name": "Broken Watch",
                        "description": "A watch stopped at 9:45.",
                        "location": "Near the victim."
                    }
                ]
            },
            solution={
                "culprit_id": "suspect_1",
                "explanation": "Clara committed the murder.",
                "evidence_ids": ["clue_1"]
            }
        )

    def test_retrieve_existing_case(self):
        response = self.client.get(
            reverse("get_case", args=[self.case_id])
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data["title"], self.case.title)
        self.assertEqual(len(data["suspects"]), 1)
        self.assertEqual(len(data["clues"]), 1)

    def test_solution_not_exposed(self):
        response = self.client.get(
            reverse("get_case", args=[self.case_id])
        )

        data = response.json()

        self.assertNotIn("solution", data)
        self.assertNotIn("culprit_id", data)

    def test_invalid_case_id(self):
        response = self.client.get(
            "/api/cases/not-a-valid-id/"
        )

        self.assertEqual(response.status_code, 400)

    def test_nonexistent_case(self):
        nonexistent_id = uuid.uuid4()

        response = self.client.get(
            reverse("get_case", args=[nonexistent_id])
        )

        self.assertEqual(response.status_code, 404)


class CaseGenerationTests(TestCase):

    @patch("detective.views.ChatGoogleGenerativeAI")
    def test_generate_case_successfully(self, mock_llm_class):

        generated_data = {
            "title": "The Silent Witness",
            "introduction": "A detective investigates a mysterious death.",
            "crime_scene_description": "A body is found in a library.",
            "suspects": [
                {
                    "id": "suspect_1",
                    "name": "Alice",
                    "profile": "The victim's assistant.",
                    "alibi": "Claims she was working."
                },
                {
                    "id": "suspect_2",
                    "name": "Bob",
                    "profile": "The victim's friend.",
                    "alibi": "Claims he was sleeping."
                },
                {
                    "id": "suspect_3",
                    "name": "Charlie",
                    "profile": "The victim's business partner.",
                    "alibi": "Claims he was travelling."
                }
            ],
            "clues": [
                {
                    "id": f"clue_{i}",
                    "name": f"Clue {i}",
                    "description": f"Description of clue {i}.",
                    "location": "Library"
                }
                for i in range(1, 6)
            ],
            "solution": {
                "culprit_id": "suspect_1",
                "explanation": "Alice committed the crime.",
                "evidence_ids": ["clue_1"]
            }
        }

        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = json.dumps(
            generated_data
        )

        mock_llm_class.return_value = mock_llm

        with patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"}):

            response = self.client.post(
                reverse("generate_case")
            )

        self.assertEqual(response.status_code, 201)

        data = response.json()

        self.assertEqual(data["title"], "The Silent Witness")
        self.assertEqual(len(data["suspects"]), 3)
        self.assertEqual(len(data["clues"]), 5)

        self.assertNotIn("solution", data)
        self.assertNotIn("culprit_id", data)

        self.assertTrue(
            Case.objects.filter(title="The Silent Witness").exists()
        )
