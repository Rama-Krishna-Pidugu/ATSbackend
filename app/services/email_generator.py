import os

EMAIL_TEMPLATES = {
    "congratulations": {
        "subject": "🎉 Congratulations on Your Selection at {company_name}!",
        "body": """Hi {candidate_name},\n\nWe are thrilled to inform you that you have been selected for the role of {job_title} at {company_name}! Your skills, experience, and passion truly stood out during the selection process, and we are excited to welcome you to our team.\n\nIn the coming days, our HR team will reach out with the next steps, including details about your onboarding process, joining date, and required documentation.\n\nCongratulations once again on this well-deserved achievement! We look forward to seeing you thrive and make a positive impact with us.\n\nWarm regards,\n{your_name}\n{your_position}\n{company_name}\n{email_signature}"""
    },
    "initial_outreach": {
        "subject": "Exciting Opportunity for {job_title} at {company_name}",
        "body": """Hi {candidate_name},\n\nI came across your profile and was impressed by your experience with {key_skills}. Our client is hiring in {location} and I believe your skills would be a great fit.\n\nWe're looking for someone to join a dynamic team working on innovative projects. The role offers competitive compensation, flexibility, and opportunities for growth.\n\nWould you be open to a quick call this week to discuss this opportunity further? If so, please suggest a convenient time.\n\nLooking forward to connecting!\n\nBest regards,\n{your_name}\n{your_position}\n{company_name}\n{email_signature}"""
    },
    "interview_invitation": {
        "subject": "Interview Invitation for {job_title} at {company_name}",
        "body": """Hi {candidate_name},\n\nThank you for your interest in the {job_title} position at {company_name}. We were impressed with your background and would like to invite you for an interview to discuss your experience and the role in more detail.\n\nPlease let us know your availability for a call or meeting this week. We look forward to speaking with you!\n\nBest regards,\n{your_name}\n{your_position}\n{company_name}\n{email_signature}"""
    },
    "regret": {
        "subject": "Update on Your Application at {company_name}",
        "body": """Hi {candidate_name},\n\nThank you for your interest in the {job_title} position at {company_name}. We appreciate the time and effort you invested in your application.\n\nAfter careful consideration, we have decided to move forward with other candidates for this role. We encourage you to apply for future opportunities that match your skills and experience.\n\nThank you again for your interest in {company_name}, and we wish you all the best in your job search.\n\nBest regards,\n{your_name}\n{your_position}\n{company_name}\n{email_signature}"""
    }
}

class EmailGenerator:
    def generate_email(self, name: str, skill: str, company_name: str = None, position: str = None, template: str = "initial_outreach", location: str = "", key_skills: str = "") -> dict:
        """Generate a personalized outreach email using a template."""
        company_name = company_name or os.getenv("COMPANY_NAME", "Our Company")
        job_title = position or os.getenv("POSITION_TITLE", "Developer")
        your_name = os.getenv("YOUR_NAME", "AI Recruiter")
        your_position = os.getenv("YOUR_POSITION", "Recruiter")
        email_signature = os.getenv("EMAIL_SIGNATURE", "PeopleGPT")
        location = location or os.getenv("COMPANY_LOCATION", "")
        key_skills = key_skills or skill
        candidate_name = name
        t = EMAIL_TEMPLATES.get(template, EMAIL_TEMPLATES["initial_outreach"])
        subject = t["subject"].format(
            candidate_name=candidate_name,
            company_name=company_name,
            job_title=job_title,
            key_skills=key_skills,
            location=location,
            your_name=your_name,
            your_position=your_position,
            email_signature=email_signature
        )
        body = t["body"].format(
            candidate_name=candidate_name,
            company_name=company_name,
            job_title=job_title,
            key_skills=key_skills,
            location=location,
            your_name=your_name,
            your_position=your_position,
            email_signature=email_signature
        )
        return {"subject": subject, "body": body} 