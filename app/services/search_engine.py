import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import os
import json
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession
from .llm_utils import call_groq
from pathlib import Path

class SearchEngine:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        # Get database connection details from environment
        self.db_user = os.getenv('DB_USER')
        self.db_password = os.getenv('DB_PASSWORD')
        self.db_host = os.getenv('DB_HOST')
        self.db_name = os.getenv('DB_NAME')
        self.database_url = f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}/{self.db_name}"
        self.engine = create_engine(self.database_url)

    def store_resume(self, resume_data: Dict[str, Any]) -> int:
        """Store a resume in the database with user_id."""
        try:
            # Create embedding for the resume
            embedding_text = resume_data.get('embedding_text', '')
            if not embedding_text:
                embedding_text = f"""
                Name: {resume_data['name']}
                Summary: {resume_data.get('summary', '')}
                Skills: {', '.join(resume_data.get('skills', []))}
                Experience: {resume_data.get('experience', '')}
                Education: {resume_data.get('education', '')}
                """
            
            embedding = self.model.encode(embedding_text)
            embedding_list = embedding.tolist()
            
            if not isinstance(embedding_list, list):
                raise ValueError("Invalid embedding format")

            with self.engine.connect() as conn:
                # First, check if resume already exists for this user
                result = conn.execute(text("""
                    SELECT id FROM resumes 
                    WHERE name = :name AND user_id = :user_id
                """), {
                    "name": resume_data["name"],
                    "user_id": resume_data["user_id"]
                })
                existing = result.fetchone()
                
                if existing:
                    # Update existing resume
                    conn.execute(text("""
                        UPDATE resumes 
                        SET skills = :skills, experience = :experience, education = :education, 
                            contact = :contact, summary = :summary, embedding = :embedding
                        WHERE name = :name AND user_id = :user_id
                    """), {
                        "skills": json.dumps(resume_data["skills"]),
                        "experience": resume_data["experience"],
                        "education": resume_data.get("education"),
                        "contact": json.dumps(resume_data.get("contact", {})),
                        "summary": resume_data.get("summary"),
                        "embedding": json.dumps(embedding_list),
                        "name": resume_data["name"],
                        "user_id": resume_data["user_id"]
                    })
                    resume_id = existing[0]
                else:
                    # Insert new resume
                    conn.execute(text("""
                        INSERT INTO resumes (
                            user_id, name, skills, experience, education, contact, summary, embedding
                        ) VALUES (
                            :user_id, :name, :skills, :experience, :education, :contact, :summary, :embedding
                        )
                    """), {
                        "user_id": resume_data["user_id"],
                        "name": resume_data["name"],
                        "skills": json.dumps(resume_data["skills"]),
                        "experience": resume_data["experience"],
                        "education": resume_data.get("education"),
                        "contact": json.dumps(resume_data.get("contact", {})),
                        "summary": resume_data.get("summary"),
                        "embedding": json.dumps(embedding_list)
                    })
                    resume_id = conn.execute(text("SELECT LAST_INSERT_ID()")).fetchone()[0]
                
                # Verify the embedding was stored correctly
                result = conn.execute(text("""
                    SELECT embedding FROM resumes WHERE id = :id
                """), {"id": resume_id})
                stored_embedding = result.fetchone()
                if not stored_embedding or not stored_embedding[0]:
                    raise ValueError("Failed to store embedding")
                
                return resume_id
        except Exception as e:
            print(f"Error storing resume: {str(e)}")
            raise

    def semantic_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Perform semantic search on resumes."""
        try:
            print(f"Starting semantic search for query: {query}")
            # Create a more comprehensive query embedding
            query_embedding = self.model.encode(query)
            with self.engine.connect() as conn:
                # Get all resumes with valid embeddings
                result = conn.execute(text("""
                    SELECT id, name, skills, experience, education, contact, summary, embedding 
                    FROM resumes 
                    WHERE embedding IS NOT NULL
                """))
                rows = result.fetchall()
                print(f"Found {len(rows)} resumes with valid embeddings")

                if not rows:
                    print("No resumes found with valid embeddings")
                    return []

                similarities = []
                for row in rows:
                    try:
                        resume_id, name, skills, experience, education, contact, summary, emb_json = row
                        if not emb_json:  # Skip if embedding is NULL
                            print(f"Skipping resume {resume_id} due to NULL embedding")
                            continue
                            
                        resume_embedding = np.array(json.loads(emb_json))
                        
                        # Calculate cosine similarity
                        similarity = np.dot(query_embedding, resume_embedding) / (
                            np.linalg.norm(query_embedding) * np.linalg.norm(resume_embedding)
                        )
                        
                        # Add a small boost for exact matches in skills or summary
                        if isinstance(skills, str):
                            skills_list = json.loads(skills)
                        else:
                            skills_list = skills
                            
                        # Check for keyword matches
                        query_keywords = query.lower().split()
                        skills_text = ' '.join(skills_list).lower()
                        summary_text = summary.lower() if summary else ""
                        
                        # Print matching information
                        print(f"\nResume {resume_id} ({name}):")
                        print(f"Skills: {skills_text}")
                        print(f"Summary: {summary_text}")
                        print(f"Query keywords: {query_keywords}")
                        
                        if any(keyword in skills_text for keyword in query_keywords):
                            print(f"Found keyword match in skills for resume {resume_id}")
                            similarity += 0.1
                            
                        if summary and any(keyword in summary_text for keyword in query_keywords):
                            print(f"Found keyword match in summary for resume {resume_id}")
                            similarity += 0.1
                        
                        print(f"Final similarity score: {similarity}")
                        # Clamp similarity to valid range (cosine can be -1..1, but we boost/scale it)
                        try:
                            similarity = float(similarity)
                        except Exception:
                            similarity = 0.0
                        # Ensure similarity is within 0.0 - 1.0 before storing
                        similarity = max(0.0, min(similarity, 1.0))
                        similarities.append((similarity, resume_id))
                    except (json.JSONDecodeError, TypeError) as e:
                        print(f"Error processing resume {resume_id}: {str(e)}")
                        continue

                if not similarities:
                    print("No similarities calculated")
                    return []

                # Get top matches
                top_matches = sorted(similarities, reverse=True)[:top_k]
                print(f"\nTop matches: {top_matches}")
                matched_ids = [match[1] for match in top_matches]

                # Fetch full resume data for matches
                placeholders = ",".join(["?"] * len(matched_ids))
                result = conn.execute(text(f"""
                    SELECT id, name, skills, experience, education, contact, summary 
                    FROM resumes 
                    WHERE id IN ({placeholders})
                """), matched_ids)
                
                results = []
                for row in result.fetchall():
                    try:
                        # Find the similarity score for this resume
                        similarity_score = next((score for score, rid in top_matches if rid == row[0]), 0)
                        # Safety clamp: ensure similarity_score is float and within 0..1
                        try:
                            similarity_score = float(similarity_score)
                        except Exception:
                            similarity_score = 0.0
                        similarity_score = max(0.0, min(similarity_score, 1.0))
                        
                        results.append({
                            "id": row[0],
                            "name": row[1],
                            "skills": json.loads(row[2]) if row[2] else [],
                            "experience": row[3] or "",
                            "education": row[4] or "",
                            "contact": json.loads(row[5]) if row[5] else {},
                            "summary": row[6] or "",
                            "similarity_score": similarity_score
                        })
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON for resume {row[0]}: {str(e)}")
                        continue
                
            return results
        except Exception as e:
            print(f"Error in semantic search: {str(e)}")
            return []

    def search(self, query: str, location: str = None, experience_years: int = None, user_id: str = None) -> Dict[str, Any]:
        """Main search function that combines semantic search with RAG."""
        try:
            print(f"\nStarting search for query: {query}")
            if not user_id:
                raise ValueError("user_id is required for search")
            
            # Create query embedding
            query_embedding = self.model.encode(query)
            
            with self.engine.connect() as conn:
                # Build base query with user_id filter
                base_query = text("""
                    SELECT id, name, skills, experience, education, contact, summary, embedding, 
                           certifications, work_history
                    FROM resumes
                    WHERE embedding IS NOT NULL
                    AND user_id = :user_id
                """)
                
                # Execute query
                result = conn.execute(base_query, {"user_id": user_id})
                rows = result.fetchall()
                print(f"Found {len(rows)} resumes for user {user_id}")
                
                if not rows:
                    print("No resumes found for user")
                    return {
                        "matches": [],
                        "analysis": "No resumes found in your database."
                    }
                
                # Calculate similarities
                similarities = []
                for row in rows:
                    try:
                        resume_id, name, skills, experience, education, contact, summary, emb_json, certs, work_hist = row
                        if not emb_json:  # Skip if embedding is NULL
                            print(f"Skipping resume {resume_id} due to NULL embedding")
                            continue

                        # Location-based similarity calculation (no skipping, include all)
                        location_similarity = 1.0  # Default if no location filter
                        if location:
                            try:
                                contact_dict = json.loads(contact) if isinstance(contact, str) else (contact or {})
                                resume_location = contact_dict.get('location', '')
                                if resume_location:
                                    # Create embeddings for location comparison
                                    query_location_embedding = self.model.encode(location)
                                    resume_location_embedding = self.model.encode(resume_location)
                                    location_similarity = np.dot(query_location_embedding, resume_location_embedding) / (
                                        np.linalg.norm(query_location_embedding) * np.linalg.norm(resume_location_embedding)
                                    )
                                    print(f"Resume {resume_id} location similarity: {location_similarity:.4f}")
                                else:
                                    # No location in resume, reduce similarity
                                    location_similarity = 0.3
                                    print(f"Resume {resume_id} has no location, using similarity: {location_similarity}")
                            except (json.JSONDecodeError, TypeError) as e:
                                # Error parsing location, use neutral similarity
                                location_similarity = 0.5
                                print(f"Error parsing location for resume {resume_id}, using similarity: {location_similarity}")

                        resume_embedding = np.array(json.loads(emb_json))

                        # Calculate cosine similarity
                        similarity = np.dot(query_embedding, resume_embedding) / (
                            np.linalg.norm(query_embedding) * np.linalg.norm(resume_embedding)
                        )

                        # Parse skills and education
                        skills_list = []
                        if isinstance(skills, str):
                            try:
                                skills_list = json.loads(skills)
                            except:
                                skills_list = []
                        elif isinstance(skills, list):
                            skills_list = skills

                        education = education or ""

                        # Keyword matching for better accuracy
                        query_lower = query.lower()
                        education_lower = education.lower()
                        skills_lower = [s.lower() for s in skills_list]
                        summary_lower = (summary or "").lower()

                        # Check for exact keyword matches
                        keyword_matches = 0
                        for keyword in query_lower.split():
                            if (keyword in education_lower or
                                any(keyword in skill for skill in skills_lower) or
                                keyword in summary_lower):
                                keyword_matches += 1

                        # Strict skill matching: if no keyword matches, set similarity to 0
                        if keyword_matches == 0:
                            similarity = 0.0

                        # Adjust similarity based on keyword matches
                        if keyword_matches > 0:
                            similarity += (keyword_matches * 0.1)  # Boost for each keyword match

                        # Location-based boosting using cosine similarity with bounds 0 to 100
                        if location:
                            # Clamp similarity to 0-1 range before scaling
                            clamped_location_similarity = max(0.0, min(location_similarity, 1.0))
                            if clamped_location_similarity > 0.7:
                                similarity += (clamped_location_similarity * 10)  # Boost scaled to max 10 (out of 100)
                            elif clamped_location_similarity < 0.3:
                                similarity *= 0.7  # Reduce similarity for poor location match

                        # Experience-based filtering (stronger penalty for shortfall)
                        if experience_years and experience:
                            try:
                                # Try to extract leading number of years from experience field
                                exp_years = float(experience.split()[0])
                                if exp_years < experience_years:
                                    shortfall = experience_years - exp_years
                                    # Apply an exponential penalty per missing year to reduce similarity more for larger gaps.
                                    # Use base 0.4 (more aggressive than simple halving). Minimum penalty floor is 0.05.
                                    penalty = max(0.05, (0.4 ** shortfall))
                                    similarity *= penalty
                            except Exception:
                                # If parsing fails, apply a conservative penalty
                                similarity *= 0.4

                        # Only include results with meaningful similarity
                        if similarity > 0.3:  # Minimum similarity threshold
                            similarities.append((similarity, row))

                    except (json.JSONDecodeError, TypeError) as e:
                        print(f"Error processing embedding for resume {row[0]}: {str(e)}")
                        continue
                
                # Sort by similarity
                similarities.sort(reverse=True)
                
                # Get top matches
                matches = []
                for similarity, row in similarities[:5]:  # Get top 5 matches
                    # Clamp similarity to 0..1 and convert to float
                    try:
                        sim_val = float(similarity)
                    except Exception:
                        sim_val = 0.0
                    sim_val = max(0.0, min(sim_val, 1.0))

                    matches.append({
                        "id": row[0],
                        "name": row[1],
                        "skills": row[2],
                        "experience": row[3],
                        "education": row[4],
                        "contact": row[5],
                        "summary": row[6],
                        "certifications": row[8],
                        "work_history": row[9],
                        "similarity_score": sim_val
                    })
                
                if not matches:
                    return {
                        "matches": [],
                        "analysis": "No matching resumes found for your search criteria."
                    }
                
                # Generate RAG response with detailed analysis
                rag_response = self.generate_answer_with_rag(query, matches)
                
                return {
                    "matches": matches,
                    "analysis": rag_response
                }
                    
        except Exception as e:
            print(f"Error in search: {str(e)}")
            return {
                "matches": [],
                "analysis": f"Error performing search: {str(e)}"
            }

    def generate_answer_with_rag(self, query: str, top_resumes: List[Dict[str, Any]]) -> str:
        """Generate a response using RAG with the top matching resumes."""
        if not top_resumes:
            return "No matching resumes found."
            
        context = "\n\n".join([
            f"Name: {r['name']}\n"
            f"Summary: {r['summary']}\n"
            f"Skills: {', '.join(json.loads(r['skills']) if isinstance(r['skills'], str) else r['skills'])}\n"
            f"Experience: {r['experience']}\n"
            f"Education: {r['education']}\n"
            f"Certifications: {', '.join(json.loads(r['certifications']) if isinstance(r['certifications'], str) else r['certifications'])}\n"
            f"Work History: {json.dumps(json.loads(r['work_history']) if isinstance(r['work_history'], str) else r['work_history'])}"
            for r in top_resumes
        ])
        
        prompt = f"""You are a helpful assistant helping recruiters find suitable candidates.
        
        User query: "{query}"

        Resume database (top matches):
        {context}

        Based on the above, provide a detailed analysis:
        1. Best matches (with reasoning)
        2. Why they match the requirements
        3. Key qualifications and experience
        4. Any potential concerns or missing qualifications
        5. Recommendations for next steps
        
        Format your response in a clear, structured way.
        """
        
        try:
            response, _ = call_groq(prompt)
            return response
        except Exception as e:
            print(f"Error generating RAG response: {str(e)}")
            return "Error generating analysis. Please try again."

    def clear_index(self, user_id: str = None):
        """Clear all resumes from the database for a specific user."""
        try:
            with self.engine.connect() as conn:
                if user_id:
                    conn.execute(text("DELETE FROM resumes WHERE user_id = :user_id"), {"user_id": user_id})
                else:
                    conn.execute(text("DELETE FROM resumes"))
        except Exception as e:
            print(f"Error clearing index: {str(e)}")
            raise

    def verify_database(self):
        """Verify database state and fix any issues."""
        try:
            with self.engine.connect() as conn:
                # Check for resumes without embeddings
                result = conn.execute(text("""
                    SELECT id, name FROM resumes 
                    WHERE embedding IS NULL OR embedding = ''
                """))
                missing_embeddings = result.fetchall()
                
                if missing_embeddings:
                    print(f"Found {len(missing_embeddings)} resumes without embeddings")
                    for resume_id, name in missing_embeddings:
                        try:
                            # Get resume data
                            result = conn.execute(text("""
                                SELECT name, skills, experience, education, contact, summary 
                                FROM resumes WHERE id = :id
                            """), {"id": resume_id})
                            resume_data = result.fetchone()
                            
                            if resume_data:
                                # Parse contact for location
                                location = ""
                                try:
                                    contact_dict = json.loads(resume_data[4]) if resume_data[4] else {}
                                    location = contact_dict.get('location', '')
                                except:
                                    pass

                                # Create embedding text
                                embedding_text = f"""
                                Name: {resume_data[0]}
                                Summary: {resume_data[5] or ''}
                                Skills: {resume_data[1] or '[]'}
                                Experience: {resume_data[2] or ''}
                                Education: {resume_data[3] or ''}
                                Location: {location}
                                """
                                
                                # Generate embedding
                                embedding = self.model.encode(embedding_text)
                                embedding_list = embedding.tolist()
                                
                                # Update embedding
                                conn.execute(text("""
                                    UPDATE resumes 
                                    SET embedding = :embedding 
                                    WHERE id = :id
                                """), {
                                    "embedding": json.dumps(embedding_list),
                                    "id": resume_id
                                })
                        except Exception as e:
                            print(f"Error fixing resume {resume_id}: {str(e)}")
                            continue
                
                return True
        except Exception as e:
            print(f"Error verifying database: {str(e)}")
            raise 