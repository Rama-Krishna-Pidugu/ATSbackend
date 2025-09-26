# TODO: Fix Location-Based Search in ATS Backend

## Completed Steps
- [x] Update `ATSbackend/app/services/search_engine.py`:
  - Add location filtering: Skip resumes where the query location does not partially match the resume's contact['location'] (case-insensitive).
  - Add location boosting: Increase similarity score by 0.2 for matching locations.
  - Handle JSON parsing errors gracefully for contact field.
- [x] Update `ATSbackend/app/services/resume_parser.py`:
  - Include location in embedding_text for better semantic search matching.
  - Improve fallback _extract_contact to extract location using regex patterns and keywords.

## Pending Steps
- [ ] Test the updated search functionality:
  - Manually test the `/search/` API endpoint with a location parameter (e.g., query="Python developer", location="New York").
  - Verify that only location-matching resumes are returned and ranked higher.
  - Check logs for any errors in location parsing.
- [ ] Run database verification: Use `search_engine.verify_database()` to ensure all embeddings are intact.
- [ ] Deploy or restart the backend server to apply changes.

Last updated: After improving resume parser for location extraction and embedding.
