"""
ai_engine.py
Deep Market Research & Daily AI Keyword Recommendation Engine
Supports Google Gemini (Gemini 2.0 Flash / 1.5 Flash) and OpenAI (GPT-4o / GPT-4o-mini).
"""

import os
import json
import time
import requests
from datetime import datetime

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "ai_config.json")
DAILY_CACHE_FILE = os.path.join(os.path.dirname(__file__), "ai_daily_cache.json")
ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")

DEFAULT_CONFIG = {
    "provider": "groq",
    "api_key": "",
    "model": "openai/gpt-oss-120b"
}

def load_env_file():
    """Load key-value pairs from .env file into os.environ."""
    if os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and not os.environ.get(k):
                            os.environ[k] = v
        except Exception:
            pass

def load_config():
    """Load configuration prioritizing .env and environment variables."""
    load_env_file()
    config = {**DEFAULT_CONFIG}

    # Load non-sensitive preferences from config file if exists
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                config.update(saved)
        except Exception:
            pass

    # Environment variables take precedence for security
    env_groq = os.environ.get("GROQ_API_KEY")
    env_gemini = os.environ.get("GEMINI_API_KEY")
    env_openai = os.environ.get("OPENAI_API_KEY")
    env_provider = os.environ.get("AI_PROVIDER")
    env_model = os.environ.get("AI_MODEL")

    if env_groq:
        config["api_key"] = env_groq
        config["provider"] = "groq"
        config["model"] = env_model or "openai/gpt-oss-120b"
    elif env_gemini:
        config["api_key"] = env_gemini
        config["provider"] = "gemini"
        config["model"] = env_model or "gemini-2.0-flash"
    elif env_openai:
        config["api_key"] = env_openai
        config["provider"] = "openai"
        config["model"] = env_model or "gpt-4o-mini"

    if env_provider:
        config["provider"] = env_provider.lower()
    if env_model:
        config["model"] = env_model

    return config

def save_config(provider, api_key, model=None):
    """
    Save configuration securely.
    Writes key to private .env file (excluded by .gitignore).
    """
    config = load_config()
    key_clean = api_key.strip() if api_key else ""
    prov_clean = provider.strip().lower() if provider else "groq"

    if key_clean.startswith("gsk_"):
        prov_clean = "groq"
        if not model or "gemini" in model or "gpt-4" in model:
            model = "openai/gpt-oss-120b"
    elif key_clean.startswith("AIzaSy"):
        prov_clean = "gemini"
        if not model:
            model = "gemini-2.0-flash"
    elif key_clean.startswith("sk-"):
        prov_clean = "openai"
        if not model:
            model = "gpt-4o-mini"

    config["provider"] = prov_clean
    if model:
        config["model"] = model.strip()

    # If new key provided, update .env file securely
    if key_clean:
        config["api_key"] = key_clean
        env_key_var = "GROQ_API_KEY" if prov_clean == "groq" else ("GEMINI_API_KEY" if prov_clean == "gemini" else "OPENAI_API_KEY")
        try:
            # Read existing lines from .env if any
            existing_lines = []
            if os.path.exists(ENV_FILE):
                with open(ENV_FILE, "r", encoding="utf-8") as f:
                    existing_lines = f.readlines()

            # Update or append the key
            updated = False
            new_lines = []
            for line in existing_lines:
                if line.strip().startswith(f"{env_key_var}="):
                    new_lines.append(f"{env_key_var}={key_clean}\n")
                    updated = True
                elif line.strip().startswith("AI_PROVIDER="):
                    new_lines.append(f"AI_PROVIDER={prov_clean}\n")
                elif line.strip().startswith("AI_MODEL="):
                    new_lines.append(f"AI_MODEL={config['model']}\n")
                else:
                    new_lines.append(line)

            if not updated:
                new_lines.append(f"{env_key_var}={key_clean}\n")
                new_lines.append(f"AI_PROVIDER={prov_clean}\n")
                new_lines.append(f"AI_MODEL={config['model']}\n")

            with open(ENV_FILE, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception:
            pass

    # Save non-sensitive metadata (no API key stored in JSON)
    safe_config_to_save = {
        "provider": config["provider"],
        "model": config["model"]
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(safe_config_to_save, f, indent=2)

    return config

def get_public_config():
    """
    Return safe public configuration for UI.
    SECURITY: NEVER leaks any characters, slices, or fragments of the actual API key.
    """
    cfg = load_config()
    key = cfg.get("api_key", "")
    return {
        "provider": cfg.get("provider", "groq"),
        "model": cfg.get("model", "openai/gpt-oss-120b"),
        "has_key": bool(key),
        "status": "Active & Protected" if bool(key) else "Not Configured"
    }

def test_api_connection(provider, api_key, model=None):
    """
    Test the provided API key with a small ping request.
    Returns (success: bool, message: str).
    """
    api_key = api_key.strip() if api_key else ""
    provider = provider.lower() if provider else "gemini"

    if api_key.startswith("gsk_"):
        provider = "groq"

    if not api_key:
        return False, "API key cannot be blank."

    if provider == "groq":
        target_model = model or "openai/gpt-oss-120b"
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        payload = {
            "model": target_model,
            "messages": [{"role": "user", "content": "Reply with 'CONNECTED_OK'."}],
            "max_tokens": 10
        }
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=12)
            if res.status_code == 200:
                return True, f"Successfully connected to Groq ({target_model})!"
            else:
                try:
                    err_json = res.json()
                    return False, f"Groq error: {err_json.get('error', {}).get('message', res.text)}"
                except Exception:
                    return False, f"Groq error: {res.text}"
        except Exception as e:
            return False, f"Groq request failed: {str(e)}"

    elif provider == "gemini":
        target_model = model or "gemini-2.0-flash"
        # If gemini-2.0-flash fails with 404, we test fallback to gemini-1.5-flash
        models_to_test = [target_model]
        if target_model != "gemini-1.5-flash":
            models_to_test.append("gemini-1.5-flash")

        last_error = ""
        for m in models_to_test:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": "Reply with 'CONNECTED_OK' if you can read this."}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 20}
            }
            try:
                res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=12)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        return True, f"Successfully connected to Google Gemini ({m})!"
                else:
                    try:
                        err_json = res.json()
                        last_error = err_json.get("error", {}).get("message", res.text)
                    except Exception:
                        last_error = res.text
            except Exception as e:
                last_error = str(e)

        return False, f"Gemini connection failed: {last_error}"

    elif provider == "openai":
        target_model = model or "gpt-4o-mini"
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        payload = {
            "model": target_model,
            "messages": [{"role": "user", "content": "Reply with 'CONNECTED_OK'."}],
            "max_tokens": 10
        }
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=12)
            if res.status_code == 200:
                return True, f"Successfully connected to OpenAI ({target_model})!"
            else:
                try:
                    err_json = res.json()
                    return False, f"OpenAI error: {err_json.get('error', {}).get('message', res.text)}"
                except Exception:
                    return False, f"OpenAI error: {res.text}"
        except Exception as e:
            return False, f"OpenAI request failed: {str(e)}"

    return False, f"Unknown provider: {provider}"

def _call_llm(prompt, system_instruction=None, json_mode=True):
    """
    Internal helper to call configured LLM with prompt and return text.
    Handles Groq, Gemini, and OpenAI.
    """
    cfg = load_config()
    api_key = cfg.get("api_key", "")
    provider = cfg.get("provider", "gemini")
    model = cfg.get("model", "gemini-2.0-flash")

    if api_key.startswith("gsk_"):
        provider = "groq"
        if not model or "gemini" in model or "gpt-4" in model:
            model = "openai/gpt-oss-120b"

    if not api_key:
        raise ValueError("API key is not configured. Please provide an API key in AI Settings.")

    if provider == "groq":
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        target_model = model or "openai/gpt-oss-120b"
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": 0.3
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        res = requests.post(url, json=payload, headers=headers, timeout=35)
        if res.status_code == 200:
            data = res.json()
            return data["choices"][0]["message"]["content"]
        else:
            try:
                err_msg = res.json().get("error", {}).get("message", res.text)
            except Exception:
                err_msg = res.text
            raise Exception(f"Groq API error: {err_msg}")

    if provider == "gemini":
        models_to_try = [model]
        if model != "gemini-1.5-flash":
            models_to_try.append("gemini-1.5-flash")

        last_exc = None
        for m in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
            contents = []
            if system_instruction:
                # In Gemini v1beta, system_instruction can be passed in top-level or as parts
                contents.append({"role": "user", "parts": [{"text": f"SYSTEM INSTRUCTIONS:\n{system_instruction}\n\nUSER REQUEST:\n{prompt}"}]})
            else:
                contents.append({"role": "user", "parts": [{"text": prompt}]})

            gen_config = {
                "temperature": 0.3,
                "maxOutputTokens": 3000
            }
            if json_mode:
                gen_config["responseMimeType"] = "application/json"

            payload = {
                "contents": contents,
                "generationConfig": gen_config
            }

            try:
                res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=35)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
                else:
                    err_msg = res.text
                    try:
                        err_msg = res.json().get("error", {}).get("message", res.text)
                    except Exception:
                        pass
                    last_exc = Exception(f"Gemini API error ({m}): {err_msg}")
            except Exception as e:
                last_exc = e

        if last_exc:
            raise last_exc
        raise Exception("Failed to get response from Gemini.")

    elif provider == "openai":
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model or "gpt-4o-mini",
            "messages": messages,
            "temperature": 0.3
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        res = requests.post(url, json=payload, headers=headers, timeout=35)
        if res.status_code == 200:
            data = res.json()
            return data["choices"][0]["message"]["content"]
        else:
            try:
                err_msg = res.json().get("error", {}).get("message", res.text)
            except Exception:
                err_msg = res.text
            raise Exception(f"OpenAI API error: {err_msg}")

    raise ValueError(f"Unsupported AI provider: {provider}")

def _clean_json_output(raw_text):
    """Clean markdown backticks or malformed wrappers from LLM output."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

# Curated Fallback Recommendations if no API key is provided yet
CURATED_FALLBACK_RECOMMENDATIONS = [
    {
        "keyword": "Commercial Plots in Bihta Airport Corridor",
        "city": "Patna",
        "state": "Bihar",
        "category": "Real Estate & Plots",
        "roi_score": 98,
        "ticket_size": "₹50L - ₹3Cr",
        "target_buyer": "Industrial Warehouses, Logistics Firms & HNI Investors",
        "competition": "Medium",
        "why_profitable": "Rapid infrastructure expansion around upcoming Bihta International Airport and dry port.",
        "search_query": "real estate agents bihta patna",
        "mode": "general",
        "tag": "🔥 #1 Hotspot Bihar"
    },
    {
        "keyword": "Ranchi Ring Road Gated Township Land",
        "city": "Ranchi",
        "state": "Jharkhand",
        "category": "Real Estate & Plots",
        "roi_score": 96,
        "ticket_size": "₹35L - ₹1.8Cr",
        "target_buyer": "Duplex Developers, Doctors & Mining Executives",
        "competition": "Low-Medium",
        "why_profitable": "Prime 4-lane Ring Road connectivity connecting Kathal More, Tupudana & Ormanjhi.",
        "search_query": "property dealers ranchi ring road",
        "mode": "general",
        "tag": "💎 Prime Corridor"
    },
    {
        "keyword": "IIT JEE & NEET Medical Coaching Institutes",
        "city": "Patna",
        "state": "Bihar",
        "category": "Education & Coaching",
        "roi_score": 94,
        "ticket_size": "₹1.5L - ₹3.5L/student",
        "target_buyer": "Parents of 10th-12th Students across 38 Bihar Districts",
        "competition": "High",
        "why_profitable": "Boring Road & Kankarbagh form the regional education hub of Eastern India with massive student footfall.",
        "search_query": "iit jee neet coaching institutes boring road patna",
        "mode": "coaching",
        "tag": "🎓 High Student Volume"
    },
    {
        "keyword": "RERA Approved Residential Plots",
        "city": "Muzaffarpur",
        "state": "Bihar",
        "category": "Real Estate & Plots",
        "roi_score": 93,
        "ticket_size": "₹20L - ₹60L",
        "target_buyer": "Local Businessmen, Teachers & Government Servants",
        "competition": "Low",
        "why_profitable": "High demand for legally verified, mutated (Dakhil Kharij) plots in Mithila's commercial hub.",
        "search_query": "real estate property dealers muzaffarpur",
        "mode": "general",
        "tag": "✅ 100% Legal Clear Title"
    },
    {
        "keyword": "Industrial Shed & Warehouse Contractors",
        "city": "Jamshedpur",
        "state": "Jharkhand",
        "category": "Industrial & Construction",
        "roi_score": 95,
        "ticket_size": "₹25L - ₹2Cr",
        "target_buyer": "Ancillary Tata Motors suppliers, Steel Fabrication Units",
        "competition": "Medium",
        "why_profitable": "Adityapur Industrial Area houses 1,200+ operating plants with continuous fabrication demand.",
        "search_query": "industrial shed building contractors adityapur jamshedpur",
        "mode": "bihar_directory",
        "tag": "🏭 Industrial Powerhouse"
    },
    {
        "keyword": "Rooftop Solar EPC Installers & Dealers",
        "city": "Patna",
        "state": "Bihar",
        "category": "Energy & Sustainability",
        "roi_score": 91,
        "ticket_size": "₹2L - ₹20L",
        "target_buyer": "Commercial Hospitals, Banquet Halls, Cold Storages & High-Rise Apartments",
        "competition": "Low",
        "why_profitable": "High commercial power tariffs in Bihar drive massive ROI on 10kW-100kW solar installations.",
        "search_query": "solar energy equipment dealers patna",
        "mode": "general",
        "tag": "⚡ High Subsidy & Margin"
    },
    {
        "keyword": "Multi-Speciality Diagnostic & Pathology Labs",
        "city": "Dhanbad",
        "state": "Jharkhand",
        "category": "Healthcare",
        "roi_score": 92,
        "ticket_size": "₹10L - ₹80L",
        "target_buyer": "Coal Belt Corporate Employees, BCCL Hospitals & Private Practitioners",
        "competition": "Medium",
        "why_profitable": "Coal mining belt generates steady year-round diagnostic and occupational health testing volume.",
        "search_query": "diagnostic pathology centers bank more dhanbad",
        "mode": "general",
        "tag": "🩺 High Margin B2B"
    },
    {
        "keyword": "Luxury Banquet Halls & Marriage Gardens",
        "city": "Gaya",
        "state": "Bihar",
        "category": "Events & Hospitality",
        "roi_score": 90,
        "ticket_size": "₹3L - ₹15L/booking",
        "target_buyer": "Affluent NRI and Magadh Families hosting destination weddings",
        "competition": "Medium",
        "why_profitable": "Prime highway corridors like Dobhi Highway and Bodh Gaya road are expanding wedding hubs.",
        "search_query": "marriage banquet halls gaya bodh gaya",
        "mode": "bihar_directory",
        "tag": "🎉 High Booking Value"
    }
]

def get_daily_ai_recommendations(force_refresh=False):
    """
    Fetch daily high-ticket AI keyword recommendations.
    Uses cached result for today if available, or queries AI model if configured.
    Falls back gracefully if no key is supplied.
    """
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Check cache
    if not force_refresh and os.path.exists(DAILY_CACHE_FILE):
        try:
            with open(DAILY_CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
                if cached.get("date") == today_str and cached.get("items"):
                    return {
                        "date": today_str,
                        "last_updated": cached.get("last_updated"),
                        "ai_generated": cached.get("ai_generated", False),
                        "market_summary": cached.get("market_summary", ""),
                        "items": cached.get("items", []),
                        "has_api_key": load_config().get("api_key") != ""
                    }
        except Exception:
            pass

    cfg = load_config()
    if not cfg.get("api_key"):
        # Return rich curated recommendations with a notification to add API key
        return {
            "date": today_str,
            "last_updated": datetime.now().strftime("%I:%M %p, %d %b %Y"),
            "ai_generated": False,
            "key_required": True,
            "market_summary": "Active Curated Baseline: Showing high-yield commercial sectors in Bihar & Jharkhand. Add your AI API key in Settings to unlock real-time live AI research & continuous daily market discovery.",
            "items": CURATED_FALLBACK_RECOMMENDATIONS,
            "has_api_key": False
        }

    # Generate live with LLM
    system_instruction = (
        "You are an elite B2B Market Research Analyst & Lead Generation Strategist specializing in the Indian market, "
        "with deep micro-market expertise in Bihar (Patna, Muzaffarpur, Gaya, Bhagalpur, Begusarai, Purnia) and "
        "Jharkhand (Ranchi, Jamshedpur, Dhanbad, Bokaro, Deoghar). "
        "You analyze high-ticket commercial sectors: Real Estate Plots, Commercial Corridors, Private Healthcare, "
        "IIT/NEET Coaching, Industrial Sheds, Solar EPC, Building Materials, and B2B Suppliers. "
        "You output strictly valid JSON format only."
    )

    prompt = f"""
Analyze the current commercial market for today ({today_str}) in Bihar and Jharkhand.
Identify 10 to 14 high-ticket, high-yield business niches and buyer search targets suitable for Google Maps and B2B lead scraping.

Ensure heavy focus on:
1. Real Estate Plots (Residential colonies, Bihta Airport corridor, Highway land, Ring Roads, RERA verified land)
2. Specialized Coaching & Medical Academies
3. B2B Building Contractors, Industrial Sheds, TMT/Cement dealers
4. Private Healthcare & Diagnostics
5. Solar Energy EPC and Commercial Equipment

Format your response as a JSON object with:
{{
  "market_summary": "A 2-sentence executive summary of today's highest-ROI lead opportunities in Bihar & Jharkhand.",
  "items": [
    {{
      "keyword": "Specific business or keyword string",
      "city": "Patna / Ranchi / Jamshedpur / Muzaffarpur / Dhanbad / Gaya / etc.",
      "state": "Bihar or Jharkhand",
      "category": "Real Estate & Plots / Education & Coaching / Healthcare / Industrial / etc.",
      "roi_score": 95,
      "ticket_size": "e.g. ₹20L - ₹1Cr (High Ticket) or B2B Enterprise",
      "target_buyer": "Specific profile of buyer/decision maker",
      "competition": "Low / Medium / High",
      "why_profitable": "1-2 sentences on why this niche generates high commission or sales",
      "search_query": "Exact Google Maps or directory search query for lead generation",
      "mode": "general or coaching or bihar_directory",
      "tag": "e.g. 🔥 #1 Hotspot or 💎 High Margin or ⭐ Enterprise"
    }}
  ]
}}
"""

    try:
        raw_output = _call_llm(prompt, system_instruction=system_instruction, json_mode=True)
        cleaned = _clean_json_output(raw_output)
        data = json.loads(cleaned)
        items = data.get("items", [])

        if not items:
            raise ValueError("No items in LLM response")

        cache_content = {
            "date": today_str,
            "last_updated": datetime.now().strftime("%I:%M %p, %d %b %Y"),
            "ai_generated": True,
            "market_summary": data.get("market_summary", "Live AI Market Analysis complete."),
            "items": items
        }

        try:
            with open(DAILY_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache_content, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        return {
            **cache_content,
            "has_api_key": True,
            "key_required": False
        }
    except Exception as e:
        # Fallback to curated if LLM call fails
        return {
            "date": today_str,
            "last_updated": datetime.now().strftime("%I:%M %p, %d %b %Y"),
            "ai_generated": False,
            "error": str(e),
            "market_summary": f"Could not reach AI model ({str(e)}). Displaying verified regional lead catalog.",
            "items": CURATED_FALLBACK_RECOMMENDATIONS,
            "has_api_key": True
        }

def conduct_deep_research(topic, sector="all", region="all", focus="all"):
    """
    Conduct on-demand deep market research on a user-defined prompt or topic.
    Returns structured market intelligence, opportunity assessment, and ready-to-scrape targets.
    """
    cfg = load_config()
    if not cfg.get("api_key"):
        return {
            "success": False,
            "key_required": True,
            "error": "API Key is required for Deep AI Research. Click 'AI Settings' in the top right to enter your Google Gemini or OpenAI key."
        }

    system_instruction = (
        "You are an expert AI Research Agent for lead generation and commercial intelligence. "
        "You provide exhaustive, data-driven market insights and identify the most lucrative niches, "
        "lucrative geographical clusters, high-intent buyer keywords, and actionable scraping queries. "
        "You return strictly valid JSON."
    )

    prompt = f"""
Perform deep commercial market research for the following research request:
Topic / Query: "{topic}"
Target Sector: "{sector}"
Target Region / City: "{region}"
Strategy Focus: "{focus}"

Conduct a thorough analysis:
1. Executive Market Assessment (what is the commercial demand, growth trajectory, and monetization opportunity?)
2. High-Yield Lead Segments & Scraping Targets (8 to 12 precise search strings to scrape leads from Google Maps / Local Directories)
3. Estimated Deal Size & Ticket Value
4. Ideal Customer Profile (ICP) / Decision Maker titles to pitch
5. Strategic Advice: Key selling proposition to convert these leads

Format your response strictly as a JSON object:
{{
  "topic": "{topic}",
  "executive_summary": "Detailed 2-3 paragraph breakdown of the commercial opportunity, demand drivers, and geographical advantages.",
  "key_insights": [
    "Crucial insight 1",
    "Crucial insight 2",
    "Crucial insight 3",
    "Crucial insight 4"
  ],
  "market_potential": "High / Ultra-High / Moderate",
  "average_deal_size": "e.g. ₹5L - ₹50L",
  "primary_buyer_persona": "e.g. Managing Directors, Property Developers, School Founders",
  "leads": [
    {{
      "keyword": "High-intent lead niche or title",
      "city": "Recommended City or Specific Hub (e.g. Bihta, Patna, or Adityapur, Jamshedpur)",
      "state": "Bihar or Jharkhand or Pan-India",
      "roi_score": 98,
      "ticket_tier": "High Ticket / Enterprise / Mid Ticket",
      "competition": "Low / Medium / High",
      "search_query": "Exact keyword string optimized for Google Maps or Directory scraper",
      "mode": "general or coaching or bihar_directory",
      "pitch_angle": "One sentence on how to pitch this business or lead"
    }}
  ],
  "outreach_strategy": "Concrete advice on what offering or angle converts these leads fastest."
}}
"""

    try:
        raw_output = _call_llm(prompt, system_instruction=system_instruction, json_mode=True)
        cleaned = _clean_json_output(raw_output)
        data = json.loads(cleaned)
        return {
            "success": True,
            "research": data
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
