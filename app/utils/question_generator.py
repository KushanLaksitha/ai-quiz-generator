import os
import random
import json
import google.generativeai as genai

# Configure Gemini API with the provided key.
# WARNING: Storing API keys directly in code is INSECURE.
# Use environment variables for production.
genai.configure(api_key="AIzaSyBMqYqObWnmWDbTUn6JVDUUtfTfXaPd_zA")

MODEL_NAME = 'gemini-pro' # Or other suitable models you have access to

def generate_questions_from_text(text, num_questions=5):
    """
    Generates multiple-choice questions from the given text using the Google Gemini API.
    """
    if not text:
        print("No text provided for question generation.")
        return []

    # Ensure the text isn't too long for the model's context window.
    if len(text) > 10000:
        print(f"Text too long ({len(text)} characters). Truncating for Gemini API.")
        text = text[:10000]

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        
        prompt = f"""
        Generate exactly {num_questions} multiple-choice questions based on the following text.
        For each question, provide:
        - The 'question_text'.
        - A list of 'choices', where each choice has 'text' and 'is_correct' (boolean).
        - Ensure there is always exactly one 'is_correct: True' choice per question.
        - Ensure there are 4 choices for each question (1 correct, 3 incorrect).
        - The incorrect choices should be plausible but clearly wrong based on the text.
        - The output should be a JSON array of question objects.

        Example JSON format for one question:
        {{
            "question_text": "What is the capital of France?",
            "choices": [
                {{"text": "Berlin", "is_correct": false}},
                {{"text": "Madrid", "is_correct": false}},
                {{"text": "Paris", "is_correct": true}},
                {{"text": "Rome", "is_correct": false}}
            ]
        }}

        Here is the text:
        {text}
        """

        print("Sending prompt to Gemini API...")
        response = model.generate_content(prompt)
        
        generated_content = response.text
        
        if generated_content.startswith('```json') and generated_content.endswith('```'):
            generated_content = generated_content[7:-3].strip()

        questions_data = json.loads(generated_content)
        print("Successfully generated questions from Gemini API.")
        
        processed_questions = []
        for q_data in questions_data:
            if 'question_text' in q_data and 'choices' in q_data and isinstance(q_data['choices'], list):
                valid_choices = []
                correct_count = 0
                for choice in q_data['choices']:
                    if 'text' in choice and 'is_correct' in choice:
                        valid_choices.append(choice)
                        if choice['is_correct']:
                            correct_count += 1
                
                if correct_count == 1 and len(valid_choices) == 4:
                    processed_questions.append({
                        'text': q_data['question_text'],
                        'choices': valid_choices
                    })
                else:
                    print(f"Warning: Question skipped due to invalid choices format/count: {q_data.get('question_text', 'N/A')}")
            else:
                print(f"Warning: Malformed question data skipped: {q_data}")

        return processed_questions

    except Exception as e:
        print(f"Error calling Gemini API or parsing response: {e}")
        print(f"Gemini API Response (if available): {response.text if 'response' in locals() else 'N/A'}")
        return []