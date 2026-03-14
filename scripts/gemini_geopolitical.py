"""Ask Gemini how geopolitical entities fit in the v4 taxonomy."""
import os

with open('.env') as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()

from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

with open('taxonomy/TAXONOMY.md') as f:
    taxonomy = f.read()

PROMPT = f"""I am building a causal knowledge graph for an Indian news personalization engine. Here is our full taxonomy constitution:

=== TAXONOMY ===
{taxonomy}
=== END TAXONOMY ===

We have a problem with geopolitical entities. We want to include global/geopolitical factors that causally affect Indian citizens (US Fed rate decisions, OPEC output, China trade dynamics, Gulf economies, Russia-Ukraine, global shipping routes, etc.).

But some proposed node names feel wrong:
- "china_manufacturing" — is this an entity? It's more like a sector of a country.
- "us_china_trade" — is this an entity? It's a relationship between two countries, not a thing that exists.
- "russia_ukraine_conflict" — this is an EVENT, which Rule 1 explicitly forbids.

Questions:
1. How should geopolitical entities be modeled in our taxonomy? Apply our constitution rules strictly. What passes and what fails?

2. For each of these 10 proposed geopolitical entities, classify them: does it pass the constitution as-is, does it need renaming, or does it need to be split/restructured?
   - us_federal_reserve
   - opec_output
   - china_manufacturing
   - us_immigration_policy
   - gulf_economies
   - russia_ukraine_conflict
   - eu_digital_regulation
   - global_shipping_routes
   - us_china_trade
   - global_semiconductor_supply

3. What is the RIGHT way to model "China's role in global manufacturing" as graph nodes? Walk through the constitution rules step by step.

4. What is the RIGHT way to model "US-China trade tensions affecting Indian electronics prices"? Show the full causal chain with proper node classification per our L1 rules.

5. Do we need a new convention or rule for geopolitical entities, or does the existing constitution handle them if we name them correctly?

Be strict. Apply our rules literally. If something fails Rule 1 (Entity Principle), say so and propose the correct entity."""

models = ['gemini-3.1-pro-preview', 'gemini-3-pro-preview', 'gemini-2.5-flash']
for model in models:
    print(f"Trying {model}...", flush=True)
    try:
        response = client.models.generate_content(
            model=model,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=16000)
            ),
            contents=PROMPT
        )
        print(f"SUCCESS with {model}\n", flush=True)
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'thought') and part.thought:
                    print('=== GEMINI THINKING ===', flush=True)
                    print(part.text, flush=True)
                    print('=== END THINKING ===\n', flush=True)
                elif part.text:
                    print(part.text, flush=True)
        break
    except Exception as e:
        print(f"FAILED ({type(e).__name__}): {e}\n", flush=True)
        continue
