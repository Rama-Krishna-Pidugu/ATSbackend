from app.services.llm_utils import call_groq
from typing import List

class ScreeningGenerator:
    def generate_questions(self, skill: str, level: str = "senior") -> List[str]:
        """Generate screening questions for a specific skill and level."""
        prompt = f"""Generate 5 technical interview questions for a {level} {skill} developer.\nThe questions should be:\n1. Technical and specific to {skill}\n2. Appropriate for {level} level\n3. Include both theoretical and practical aspects\n4. Focus on real-world scenarios\n5. Include one system design question if applicable\n\nFormat the response as a numbered list of questions."""

        try:
            response, _ = call_groq(prompt, temperature=0.7, max_tokens=500)
            questions = [q.strip() for q in response.split('\n') if q.strip()]
            cleaned_questions = []
            for q in questions:
                q = q.lstrip('0123456789.- ')
                if q:
                    cleaned_questions.append(q)
            return cleaned_questions[:5]
        except Exception as e:
            print(f"Error generating questions: {str(e)}")
            return [
                f"1. What is your experience with {skill}?",
                f"2. How would you approach a complex {skill} problem?",
                f"3. What are the best practices in {skill}?",
                f"4. How do you handle debugging in {skill}?",
                f"5. What's your favorite {skill} feature and why?"
            ] 