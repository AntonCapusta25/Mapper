import os
import json
from google import genai
from google.genai import types
from openai import OpenAI

class LLMEngine:
    def __init__(self):
        # google-genai automatically looks for GEMINI_API_KEY environment variable.
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            print("WARNING: GEMINI_API_KEY environment variable not set. Gemini API calls will fail.")
        self.client = genai.Client()
        self.model = 'gemini-2.5-flash'  # Latest frontier model
        
        # OpenAI Fallback
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        self.openai_client = OpenAI(api_key=self.openai_key) if self.openai_key else None

        self.brand_brain = (
            "Homemade is a community-driven food delivery platform that connects talented home chefs with customers "
            "looking for authentic, affordable, and freshly prepared meals. The platform enables individuals to start "
            "their own micro restaurants from home, turning their passion for cooking into a business while making "
            "food delivery more local and sustainable. Unlike traditional delivery platforms that rely on large "
            "restaurant chains, Homemade focuses on the human element.\n\n"
            "ACCOMPLISHED THUS FAR:\n"
            "- Operates in: Delft, Amsterdam, Rotterdam, Enschede, Haarlem, Den Haag.\n"
            "- 60+ independent home chefs offering diverse international cuisines.\n"
            "- Partnerships with student associations, local suppliers, and organizations.\n"
            "- Streamlined onboarding: From weeks to 2 days ready-to-serve.\n\n"
            "CATERING OFFERING:\n"
            "- Locally prepared food with a homemade feel.\n"
            "- Affordable catering without high overheads.\n"
            "- Support for independent chefs growing their businesses.\n"
            "- Sustainable model: Sourcing and delivering within the local community."
        )

    def _get_llm_suggestions(self, intent: str, count: int = 20) -> list[dict]:
        """Ask Gemini for highly specific Dutch Google search queries."""
        system_prompt = (
            f"You are a professional Dutch SEO expert specializing in Google Maps business discovery.\n"
            f"Generate exactly {count} highly concise, unique search queries for a scraper based on the user's intent: '{intent}'.\n\n"
            f"CRITICAL REQUIREMENTS:\n"
            f"- Length: 2-4 words per query. NO sentences.\n"
            f"- Format: Focus on Business Categories + physical locations (if city is known).\n"
            f"- Avoid: 'geïnteresseerd in', 'op zoek naar', 'open voor', 'met', 'voor'.\n\n"
            f"EXAMPLES:\n"
            f"- GOOD: 'IT bureau Enschede', 'Softwarebedrijf Enschede', 'Marketingbureau Enschede', 'Co-working Enschede'.\n"
            f"- BAD: 'Bedrijven in Enschede geïnteresseerd in samenwerking', 'Evenementenlocaties voor zakelijke lunches'.\n\n"
            f"Return ONLY a RAW JSON array: [{{\"label\": \"human readable name\", \"query\": \"short search string\"}}]. NO markdown."
        )
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=f"Intent: {intent}",
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.7,
                )
            )
            raw_text = response.text
            
            # Extract JSON block
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()
                
            data = json.loads(raw_text)
            return [{"label": str(d.get("label", d.get("query"))), "query": str(d.get("query"))} for d in data if isinstance(d, dict) and d.get("query")]
        except Exception as e:
            print(f"Gemini API Error: {e}. Attempting OpenAI fallback...")
            if self.openai_client:
                try:
                    response = self.openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": system_prompt + "\n\nCRITICAL: You MUST return a JSON object with a 'queries' key containing an array of objects with 'label' and 'query' fields."},
                            {"role": "user", "content": f"Intent: {intent}"}
                        ],
                        response_format={"type": "json_object"}
                    )
                    data = json.loads(response.choices[0].message.content)
                    print(f"DEBUG: OpenAI Raw Response: {data}")
                    
                    # Correctly identify the list first
                    queries_list = []
                    if isinstance(data, list):
                        queries_list = data
                    elif isinstance(data, dict):
                        # Look for common keys, otherwise find ANY list
                        queries_list = data.get("queries") or data.get("items") or data.get("suggestions")
                        if not queries_list:
                            for val in data.values():
                                if isinstance(val, list):
                                    queries_list = val
                                    break
                        if not queries_list:
                            queries_list = [data] # Fallback to single object
                    
                    # Ultra-permissive extraction: map common keys to 'query'
                    results = []
                    for item in queries_list:
                        if isinstance(item, dict):
                            # Look for ANY field that might be a query
                            q = item.get("query") or item.get("search_query") or item.get("q") or item.get("value")
                            l = item.get("label") or q or "Search Result"
                            if q:
                                results.append({"label": str(l), "query": str(q)})
                        elif isinstance(item, str):
                            results.append({"label": item, "query": item})
                    
                    if not results:
                        print("WARNING: OpenAI returned no valid queries. Using intent as fail-safe.")
                        results = [{"label": f"Search: {intent}", "query": intent}]
                        
                    return results
                except Exception as oe:
                    print(f"OpenAI Fallback Error: {oe}")
            
            # Absolute Fail-safe: Original Intent
            return [{"label": f"Fallback Search: {intent}", "query": intent}]

    def generate_branded_campaign(self, intent: str, city: str = "", meeting_link: str = "https://calendly.com/nederland-homemademeals/events", is_referral: bool = False) -> dict:
        """Synthesize a tailored outreach campaign based on intent, city, and the high-fidelity Dutch B2B template."""
        
        city_logic_context = (
            f"The target city is {city}. "
            "If city is Enschede: mention Kennispark/corporate vibrancy. "
            "If city is Amsterdam: mention Zuidas/creative hubs/grachtengordel. "
            "If city is generic: focus on daily office dynamic."
        ) if city else "Focus on the general office/student dynamic."

        system_prompt = (
            f"You are Oleksandr, Head of Growth at Homemade B.V. Draft a high-converting Dutch outreach email.\n\n"
            f"WHO WE ARE (Brand Brain):\n{self.brand_brain}\n\n"
            f"TARGET CITY: {city if city else 'Detect from intent or keep generic'}\n"
            f"AUDIENCE INTENT: {intent}\n"
            f"REFERRAL SCHEME ACTIVE: {'YES' if is_referral else 'NO'}\n"
            f"MEETING LINK: {meeting_link}\n\n"
            f"WRITING REQUIREMENTS:\n"
            f"- Language: Dutch (Nederlands).\n"
            f"- Tone: Professional, warm, startup-agility. Adapt to the intent (e.g., if intent is 'partnership', write a collaboration proposal, NOT a sales pitch).\n"
            f"- Intro: Mention the lead's world/city/industry specifically. If the city is known, use its unique vibe (e.g. Den Haag = political/international center, Amsterdam = creative/tech, Enschede = innovation hub).\n"
            f"- Proposal: Do NOT default to 'catering/lunch' unless it fits. Propose a specific value-add based on the INTENT (e.g. a collaboration, a presentation, or a pilot program).\n"
            f"- Sign off as: Oleksandr | Homemade Team\n\n"
            f"HTML STRUCTURE:\n"
            f"- Use a centered 600px container with border-radius: 12px and border: 1px solid #eee.\n"
            f"- Primary Brand Color: #f47a44 (Orange).\n"
            f"- Include a centered CTA button with background-color: #f47a44 and white text linking to the meeting link.\n"
            f"Return ONLY raw JSON: {{\"subject\": \"...\", \"html_body\": \"...\"}}."
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=f"Intent: {intent}\nCity: {city if city else 'Unknown'}",
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.7,
                )
            )
            raw_text = response.text
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()
            
            return json.loads(raw_text)
        except Exception as e:
            print(f"Gemini Synthesis Error: {e}. Attempting OpenAI fallback...")
            if self.openai_client:
                try:
                    response = self.openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"Intent: {intent}\nCity: {city if city else 'Unknown'}"}
                        ],
                        response_format={"type": "json_object"}
                    )
                    return json.loads(response.choices[0].message.content)
                except Exception as oe:
                    print(f"OpenAI Fallback Error: {oe}")
            
            # High-fidelity hardcoded fallback
            return {
                "subject": f"Samenwerken met Homemade in {city or 'uw stad'}?",
                "html_body": f"""
                <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: 20px auto; padding: 30px; border: 1px solid #e1e4e8; border-radius: 16px; line-height: 1.6; color: #24292e;">
                    <h2 style="color: #f47a44; font-size: 24px; margin-top: 0;">Hallo team van {{companyName}},</h2>
                    <p>Mijn naam is <strong>Oleksandr</strong>, Head of Growth bij <strong>Homemade B.V.</strong></p>
                    <p>Ik stuur jullie dit bericht omdat we met ons platform talentvolle thuischefs verbinden aan lokale gemeenschappen en bedrijven. We zijn momenteel onze aanwezigheid in <strong>{city or 'Amsterdam'}</strong> aan het uitbreiden en zien mooie mogelijkheden om samen te werken.</p>
                    <p>Homemade biedt een uniek concept: vers bereide maaltijden van lokale chefs, direct bij jullie op locatie. Dit is niet alleen een geweldige extra voor het team, maar ondersteunt ook direct ondernemerschap in de buurt.</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{meeting_link}" style="background-color: #f47a44; color: white; padding: 12px 25px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Plan een korte kennismaking</a>
                    </div>
                    <p>Zullen we binnenkort even kort bellen om te kijken of we iets voor elkaar kunnen betekenen?</p>
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="margin-bottom: 0;">Met vriendelijke groet,</p>
                    <p style="margin-top: 5px;"><strong>Oleksandr | Homemade Team</strong></p>
                </div>
                """
            }

    def process_intent(self, intent: str, count: int = 20) -> list[dict]:
        print(f"Generating {count} queries for intent: {intent}")
        return self._get_llm_suggestions(intent, count)

    def interpret_voice_command(self, audio_bytes: bytes, mime_type: str = "audio/ogg") -> dict:
        """Transcribe and extract intent/count from a voice message using multimodal Gemini."""
        system_prompt = (
            "You are the AI brain for NexusScrape, an autonomous outreach engine.\n"
            "Analyze the provided audio command from the user.\n"
            "1. Transcribe the audio clearly.\n"
            "2. Extract the 'intent' (a concise description of what/where to search).\n"
            "3. Extract the 'count' (number of queries, default to 20 if not explicitly mentioned).\n"
            "Return ONLY a RAW JSON object: {\"transcription\": \"...\", \"intent\": \"...\", \"count\": 20}. No markdown."
        )
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                    "What is the user's intent and query count in this audio?"
                ],
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.3,
                )
            )
            raw_text = response.text
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()
                
            return json.loads(raw_text)
        except Exception as e:
            print(f"Voice Interpretation Error: {e}")
            return {"error": str(e), "status": "failed"}
